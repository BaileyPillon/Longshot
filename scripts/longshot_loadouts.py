"""Named mod configurations with preview, crash recovery and one-step undo.

Only order files and disable markers change. No mod asset or save is copied.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import longshot_mods as mods
import longshot_launcher_core as core

CATALOG = ".longshot-loadouts.json"
PENDING = ".longshot-loadout-pending.json"
UNDO = ".longshot-loadout-undo.json"


def read_json(path, default=None):
    if not path.exists():
        return default
    core.plain_path(path, directory=False)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Loadout metadata exceeds 1 MiB")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=mods.unique)


def write_json(path, value):
    mods.atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@contextmanager
def locked(root):
    root = core.plain_path(root)
    core.closed_games()
    path = root / ".longshot-loadouts.lock"
    core.plain_path(path, directory=False)
    with path.open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError("Another mod operation is active; try again when it finishes") from error
        try:
            yield root
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def catalog(root):
    data = read_json(Path(root) / CATALOG, {"schema": 1, "loadouts": {}})
    if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("loadouts"), dict):
        raise ValueError("Unsupported loadout catalog; keep the file and restore a backup")
    return data


def name_ok(name):
    if not isinstance(name, str) or name != name.strip() or not 1 <= len(name) <= 64 or any(ord(c) < 32 for c in name):
        raise ValueError("Give the loadout a name of 1 to 64 characters")
    return name


def capture(root, name, *, replace=False):
    name_ok(name)
    with locked(root) as root:
        if (root / PENDING).exists():
            raise ValueError("Recover the interrupted mod switch first")
        data = catalog(root)
        if name in data["loadouts"] and not replace:
            raise ValueError("That name already exists; choose a new name")
        layers = mods.scan(root)
        data["loadouts"][name] = [{"name": m["name"], "enabled": m["enabled"],
                                    "files": m["files"]} for m in layers]
        write_json(root / CATALOG, data)


def token(layers):
    return hashlib.sha256(json.dumps(layers, sort_keys=True).encode()).hexdigest()


def preview(root, name):
    root = core.plain_path(root)
    layers = mods.scan(root)
    saved = catalog(root)["loadouts"].get(name)
    if not isinstance(saved, list) or len(saved) > 10000:
        raise ValueError("Choose a saved loadout")
    found = {m["name"]: m for m in layers}
    if any(not isinstance(m, dict) or not isinstance(m.get("name"), str) or type(m.get("enabled")) is not bool for m in saved):
        raise ValueError("Invalid loadout entries")
    if len(saved) != len(found) or {m["name"] for m in saved} != set(found):
        raise ValueError("Installed mods changed. Save a new loadout after reviewing the mod list")
    planned = []
    for entry in saved:
        layer = dict(found[entry["name"]])
        if entry.get("files") != layer["files"]:
            raise ValueError(f"Files changed in {layer['name']}; review and save a new loadout")
        if entry["enabled"]:
            if layer["errors"] or layer["exefs_unsupported"]:
                raise ValueError(f"{layer['name']}: fix compatibility notes before using this loadout")
            if any(p.startswith(("-", "_")) for p in Path(layer["name"]).parts):
                raise ValueError("A loadout cannot enable a mod disabled by its folder name")
            for parent in (root / layer["name"]).parents:
                if parent == root.parent:
                    break
                if (parent / mods.MARKER).exists():
                    raise ValueError("A loadout cannot enable a mod disabled by an enclosing folder")
        layer["enabled"] = entry["enabled"]
        planned.append(layer)
    return {"layers": planned, "conflicts": mods.conflicts(planned), "token": token(layers)}


def file_state(root):
    paths = [mods.ORDER] + [m["name"] + "/" + mods.MARKER for m in mods.scan(root)]
    result = {}
    for relative in paths:
        path = core.plain_path(root / relative, directory=False)
        if path.exists() and path.stat().st_size > 256 * 1024:
            raise ValueError("A mod control file is oversized")
        result[relative] = path.read_bytes().hex() if path.exists() else None
    return result


def restore_files(root, state):
    # Treat journals as input: only currently known marker and order paths may change.
    allowed = set(file_state(root))
    if not isinstance(state, dict) or set(state) != allowed:
        raise ValueError("Mod folders changed since the transaction; preserve the recovery file")
    decoded = {}
    for relative, value in state.items():
        if value is not None and (not isinstance(value, str) or len(value) > 512 * 1024):
            raise ValueError("Invalid recovery metadata")
        decoded[relative] = bytes.fromhex(value) if value is not None else None
    for relative, content in decoded.items():
        path = core.plain_path(root / relative, directory=False)
        if content is None:
            path.unlink(missing_ok=True)
        else:
            # Preserve the original bytes, including non-UTF8 disable marker text.
            import tempfile
            fd, tmp = tempfile.mkstemp(prefix=".longshot-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)


def apply(root, name, expected_token):
    with locked(root) as root:
        if (root / PENDING).exists():
            raise ValueError("Recover the interrupted mod switch first")
        plan = preview(root, name)
        if plan["token"] != expected_token:
            raise ValueError("Mods changed after preview. Preview again before applying")
        before = file_state(root)
        write_json(root / PENDING, {"schema": 1, "before": before})
        try:
            core.closed_games()
            for layer in plan["layers"]:
                current = next(m for m in mods.scan(root) if m["name"] == layer["name"])
                if current["enabled"] != layer["enabled"]:
                    mods.set_enabled(root, layer["name"], layer["enabled"])
            # Disabled invalid packs may remain disabled; only enabled ones were checked above.
            mods.atomic_text(root / mods.ORDER, "# Longshot loadout: last enabled layer wins\n" +
                             "\n".join(m["name"] for m in plan["layers"]) + "\n")
            write_json(root / UNDO, {"schema": 1, "before": before, "after": file_state(root)})
        except BaseException:
            restore_files(root, before)
            (root / PENDING).unlink()
            raise
        (root / PENDING).unlink()
        return plan


def recover(root, *, undo=False):
    with locked(root) as root:
        path = root / (UNDO if undo else PENDING)
        if undo and (root / PENDING).exists():
            raise ValueError("Recover the interrupted switch before undoing another switch")
        data = read_json(path)
        if not isinstance(data, dict) or data.get("schema") != 1:
            raise ValueError("There is no saved switch to recover")
        if undo and file_state(root) != data.get("after"):
            raise ValueError("Mods changed since the switch. Undo would replace those changes")
        if undo:
            write_json(root / PENDING, {"schema": 1, "before": data.get("before")})
        restore_files(root, data.get("before"))
        path.unlink()
        if undo:
            (root / PENDING).unlink()

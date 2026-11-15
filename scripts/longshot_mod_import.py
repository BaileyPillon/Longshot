"""Stage a local RomFS mod as a disabled layer for review in the mod manager."""
from contextlib import contextmanager
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile
import zlib

import longshot_launcher_core as core
import longshot_loadouts as loadouts
import longshot_mods as mods


def install_folder(root, source):
    root = core.plain_path(root)
    source = core.plain_path(source)
    if source == root or source.is_relative_to(root) or root.is_relative_to(source):
        raise ValueError("Choose a mod folder outside the current mods directory")
    if (source / "exefs").exists():
        raise ValueError("This mod includes ExeFS patches. Choose a RomFS-only mod folder.")
    assets = core.plain_path(source / "romfs")
    if not assets.is_dir():
        raise ValueError("Choose the folder that contains the mod's romfs directory")
    with staging(root, source.name) as (stage, destination):
        pending = [assets]
        paths = set()
        count = 0
        while pending:
            folder = core.plain_path(pending.pop())
            (stage / folder.relative_to(source)).mkdir()
            for item in folder.iterdir():
                if mods.linked(item):
                    raise ValueError(f"Mod contains a linked path: {item.name}")
                relative = item.relative_to(source)
                check_path(destination, relative, item.is_dir(), paths)
                if item.is_dir():
                    pending.append(item)
                else:
                    core.plain_path(item, directory=False)
                    shutil.copyfile(item, stage / relative)
                    count += 1
        if not count:
            raise ValueError("The romfs folder is empty")
        manifest = source / "longshot-mod.json"
        if manifest.exists() or manifest.is_symlink():
            core.plain_path(manifest, directory=False)
            if manifest.stat().st_size > 65536:
                raise ValueError("Mod manifest exceeds 64 KiB")
            shutil.copyfile(manifest, stage / manifest.name)
    return source.name, count


def check_path(destination, relative, directory, seen):
    if len(relative.parts) > (33 if directory else 34) or len(str(destination / relative).encode("utf-8")) >= 260:
        raise ValueError(f"Mod path exceeds the game loader's limits: {relative}")
    key = mods.key(relative.as_posix())
    if key in seen:
        raise ValueError(f"Two paths collide in the game loader: {relative}")
    seen.add(key)


@contextmanager
def staging(root, name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}", name) or unsafe_part(name):
        raise ValueError("Choose a mod name of up to 64 letters, numbers, spaces, dots, hyphens or underscores")
    destination = root / name
    core.closed_games()
    root.mkdir(exist_ok=True)
    with loadouts.locked(root):
        if (root / loadouts.PENDING).exists():
            raise ValueError("Recover the interrupted loadout switch first")
        if any(mods.key(p.name) == mods.key(name) for p in root.iterdir()):
            raise FileExistsError(f"A mod named {name} is already installed")
        with tempfile.TemporaryDirectory(prefix=".longshot-import-", dir=root) as temporary:
            stage = Path(temporary) / name
            stage.mkdir()
            yield stage, destination
            errors = mods.manifest_errors(stage)
            if errors:
                raise ValueError("\n".join(errors))
            (stage / mods.MARKER).touch()
            core.closed_games()
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(f"A mod named {name} is already installed")
            stage.rename(destination)


def unsafe_part(part):
    reserved = r"CON|PRN|AUX|NUL|COM[0-9¹²³]|LPT[0-9¹²³]"
    return (not part or part in (".", "..") or part.endswith((".", " "))
            or any(ord(c) < 32 or c in '<>:"\\|?*' for c in part)
            or re.fullmatch(reserved, part.split(".")[0].rstrip(), re.IGNORECASE))


def install_zip(root, source):
    """Accept one RomFS layer, including a ZIP wrapped in a mod or title folder."""
    root = core.plain_path(root)
    source = core.plain_path(source, directory=False)
    try:
        with zipfile.ZipFile(source) as archive:
            return install_archive(root, source.stem, archive)
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, zlib.error) as error:
        raise ValueError(f"Could not read this mod ZIP: {error}") from error


def install_archive(root, name, archive):
    entries = archive.infolist()
    if len(entries) > 100_000:
        raise ValueError("Mod ZIP has too many entries")
    members, roots, seen, spellings = [], set(), set(), {}
    for entry in entries:
        parts = tuple(entry.filename.rstrip("/").split("/"))
        lower = tuple(part.lower() for part in parts)
        mode = stat.S_IFMT(entry.external_attr >> 16)
        if (len(parts) > 48 or entry.orig_filename != entry.filename or any(map(unsafe_part, parts))
                or mode not in (0, stat.S_IFREG, stat.S_IFDIR) or lower in seen
                or entry.flag_bits & 1):
            raise ValueError(f"Unsafe or duplicate mod ZIP entry: {entry.filename}")
        seen.add(lower)
        for depth in range(1, len(parts) + 1):
            prefix = parts[:depth]
            if spellings.setdefault(lower[:depth], prefix) != prefix:
                raise ValueError(f"Conflicting ZIP path spelling: {entry.filename}")
        if "exefs" in lower and ("romfs" not in lower or lower.index("exefs") < lower.index("romfs")):
            raise ValueError("This ZIP includes ExeFS patches. Choose a RomFS-only mod.")
        if not entry.is_dir():
            members.append((parts, entry))
            if "romfs" in parts and parts[-1] != "romfs":
                roots.add(parts[:parts.index("romfs")])
    if len(roots) != 1:
        raise ValueError("A mod ZIP must contain exactly one romfs folder with files")
    (prefix,) = roots
    if any(parent.lower() == "contents" and re.fullmatch(r"[0-9A-Fa-f]{16}", title)
           and title.lower() != mods.TITLE for parent, title in zip(prefix, prefix[1:])):
        raise ValueError("Mod ZIP targets a different game")
    assets = prefix + ("romfs",)
    selected = [(Path(*parts[len(prefix):]), entry) for parts, entry in members
                if parts[:len(assets)] == assets or parts == prefix + ("longshot-mod.json",)]
    if sum(entry.file_size for _, entry in selected) + 64 * 1024**2 > shutil.disk_usage(root.parent).free:
        raise ValueError("The mods drive does not have enough space to unpack this ZIP")
    with staging(root, name) as (stage, destination):
        paths = set()
        for relative, entry in selected:
            check_path(destination, relative, False, paths)
            if relative.name == "longshot-mod.json" and len(relative.parts) == 1 and entry.file_size > 65536:
                raise ValueError("Mod manifest exceeds 64 KiB")
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as stream, target.open("xb") as output:
                shutil.copyfileobj(stream, output, 1024 * 1024)
                if output.tell() != entry.file_size:
                    raise ValueError(f"Mod ZIP entry size changed: {relative}")
    return name, sum(len(relative.parts) > 1 for relative, _ in selected)

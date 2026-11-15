"""Native save ZIP exchange with NX2navi's version 1 format."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile
import zlib

import longshot_launcher_core as core


TITLE = core.oot_saves.TITLE.lower()
ACCOUNT = re.compile(r"[0-9a-f]{32}")
SLOT = re.compile(r"slot_(?:0[0-9]|1[01])")
MAX_MANIFEST = 16 * 1024
MAX_MEMBERS = 128
# Leave space for optional NX2navi bug-report attachments. They are never read.
MAX_ZIP = 256 * 1024 * 1024


def save_limit(name):
    if name in core.checkpoints.ACCOUNT_FILES:
        return core.checkpoints.ACCOUNT_FILES[name]
    folder, _, filename = name.partition("/")
    if SLOT.fullmatch(folder):
        return core.checkpoints.SLOT_FILES.get(filename, 0)
    return 0


def hashes(data):
    return {name: hashlib.sha256(content).hexdigest() for name, content in data.items()}


def read_package(path):
    path = core.plain_path(path, directory=False)
    with path.open("rb") as stream:
        if os.fstat(stream.fileno()).st_size > MAX_ZIP:
            raise ValueError("Save package is too large")
        try:
            with zipfile.ZipFile(stream) as archive:
                return read_members(archive)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError, UnicodeError, EOFError, zlib.error) as error:
            raise ValueError("Could not read this save ZIP") from error


def read_members(archive):
    entries = archive.infolist()
    if len(entries) > MAX_MEMBERS:
        raise ValueError("Too many entries in save ZIP")
    seen, data, manifest = set(), {}, None
    for entry in entries:
        name = entry.filename
        parts = name.rstrip("/").split("/")
        if (name != entry.orig_filename or name.casefold() in seen or "\\" in name or ":" in name
                or any(part in ("", ".", "..") for part in parts)
                or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
            raise ValueError("Invalid or duplicate entry in save ZIP")
        seen.add(name.casefold())
        if name == "manifest.json" and 0 < entry.file_size <= MAX_MANIFEST:
            manifest = json.loads(archive.read(entry))
        elif name.startswith("bug-report/"):
            continue
        elif entry.is_dir() and (name == "save/" or len(parts) == 2 and parts[0] == "save" and SLOT.fullmatch(parts[1])):
            continue
        elif name.startswith("save/") and 0 < entry.file_size <= save_limit(name[5:]):
            content = archive.read(entry)
            if len(content) != entry.file_size:
                raise ValueError(f"Incorrect save ZIP entry size: {name}")
            data[name[5:]] = content
        else:
            raise ValueError(f"Unexpected or oversized save ZIP entry: {name}")

    if (not isinstance(manifest, dict) or manifest.get("format") != "nx2navi-save"
            or type(manifest.get("format_version")) is not int or manifest["format_version"] != 1
            or str(manifest.get("title_id", "")).lower() != TITLE or manifest.get("game_version") != "1.1.1"
            or type(manifest.get("files")) is not int or manifest["files"] != len(data)):
        raise ValueError("Choose an Ocarina of Time remake 1.1.1 save ZIP")
    slots = sorted({name.split("/")[0] for name in data if "/" in name})
    if "account.sav" not in data or not slots or any(
        f"{slot}/{filename}" not in data for slot in slots for filename in core.checkpoints.SLOT_FILES
    ):
        raise ValueError("Save ZIP must contain an account and complete save slots")
    if "sha256" in manifest and manifest["sha256"] != hashes(data):
        raise ValueError("Save ZIP checksum mismatch")
    account = manifest.get("longshot_account", core.DEFAULT_ACCOUNT)
    if not isinstance(account, str) or not ACCOUNT.fullmatch(account):
        raise ValueError("Invalid save account identifier")
    return {Path(name): content for name, content in data.items()}, slots, account


def export_package(game, number, account, path):
    if not ACCOUNT.fullmatch(account):
        raise ValueError("Select a valid save account")
    core.closed_games()
    source = core.profile_folder(game, number) / "save" / account
    data, slots = core.save_files(source)
    portable = {name.as_posix(): content for name, content in data.items()}
    manifest = dict(format="nx2navi-save", format_version=1, title_id=TITLE, game_version="1.1.1",
                    game="The Legend of Zelda: Ocarina of Time", files=len(data), nx2navi="",
                    exported=datetime.now(timezone.utc).isoformat(timespec="seconds"), exported_by="Longshot",
                    bug_report=False, longshot_account=account, sha256=hashes(portable))
    path = core.plain_path(path, directory=False)
    if path.suffix.lower() != ".zip":
        raise ValueError("Choose a ZIP filename")
    if path.exists():
        raise FileExistsError(f"Choose a new ZIP filename: {path.name}")
    with tempfile.TemporaryDirectory(prefix=".longshot-export-", dir=path.parent) as temporary:
        staged = Path(temporary) / "save.zip"
        with staged.open("xb") as stream:
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, indent=2))
                for name, content in portable.items():
                    archive.writestr("save/" + name, content)
            stream.flush()
            os.fsync(stream.fileno())
        if read_package(staged) != (data, slots, account):
            raise ValueError("Save ZIP verification failed")
        core.closed_games()
        # Publish a verified file without replacing any concurrent export.
        if os.name == "nt":
            staged.rename(path)
        else:
            os.link(staged, path)
    return {"path": path, "slots": slots}


def import_package(path, game, number):
    core.closed_games()
    data, slots, account = read_package(path)
    return core.publish_saves(data, slots, account, game, number)

"""Stage a local RomFS mod as a disabled layer for review in the mod manager."""
from pathlib import Path
import re
import shutil
import tempfile

import longshot_launcher_core as core
import longshot_loadouts as loadouts
import longshot_mods as mods


def install_folder(root, source):
    root = core.plain_path(root)
    source = core.plain_path(source)
    if source == root or source.is_relative_to(root) or root.is_relative_to(source):
        raise ValueError("Choose a mod folder outside the current mods directory")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}", source.name) or source.name.endswith((".", " ")):
        raise ValueError("Use a mod folder name of 1 to 64 letters, numbers, spaces, dots, hyphens or underscores")
    if (source / "exefs").exists():
        raise ValueError("This mod includes ExeFS patches. Choose a RomFS-only mod folder.")
    assets = core.plain_path(source / "romfs")
    if not assets.is_dir():
        raise ValueError("Choose the folder that contains the mod's romfs directory")
    destination = root / source.name
    core.closed_games()
    root.mkdir(exist_ok=True)
    with loadouts.locked(root):
        if (root / loadouts.PENDING).exists():
            raise ValueError("Recover the interrupted loadout switch first")
        if any(mods.key(p.name) == mods.key(source.name) for p in root.iterdir()):
            raise FileExistsError(f"A mod named {source.name} is already installed")
        with tempfile.TemporaryDirectory(prefix=".longshot-import-", dir=root) as temporary:
            stage = Path(temporary) / source.name
            stage.mkdir()
            pending = [assets]
            files = set()
            while pending:
                folder = core.plain_path(pending.pop())
                target = stage / folder.relative_to(source)
                target.mkdir()
                for item in folder.iterdir():
                    if mods.linked(item):
                        raise ValueError(f"Mod contains a linked path: {item.name}")
                    relative = item.relative_to(source)
                    if len(relative.parts) > 34 or len(str(destination / relative).encode("utf-8")) >= 260:
                        raise ValueError(f"Mod path exceeds the game loader's limits: {relative}")
                    if item.is_dir():
                        if len(relative.parts) > 33:
                            raise ValueError(f"Mod folder exceeds the game loader's depth limit: {relative}")
                        pending.append(item)
                    else:
                        core.plain_path(item, directory=False)
                        key = mods.key(relative.as_posix())
                        if key in files:
                            raise ValueError(f"Two files collide in the game loader: {relative}")
                        shutil.copyfile(item, stage / relative)
                        files.add(key)
            if not files:
                raise ValueError("The romfs folder is empty")
            manifest = source / "longshot-mod.json"
            if manifest.exists() or manifest.is_symlink():
                core.plain_path(manifest, directory=False)
                if manifest.stat().st_size > 65536:
                    raise ValueError("Mod manifest exceeds 64 KiB")
                shutil.copyfile(manifest, stage / manifest.name)
            errors = mods.manifest_errors(stage)
            if errors:
                raise ValueError("\n".join(errors))
            (stage / mods.MARKER).touch()
            core.closed_games()
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(f"A mod named {source.name} is already installed")
            stage.rename(destination)
    return destination.name, len(files)

"""Own one experimental game and serve native checkpoint-menu requests.

Archives contain the last native save, never a live memory image. A renderer
confirmation precedes each request; the child exits before any save is read.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import longshot_launcher_core as core
import longshot_mods as mods
from hookshot_ctl import Bridge


def latest_slot(user):
    if not (Path(user) / "save").is_dir():
        raise ValueError("No native save exists. Save in-game before capturing a checkpoint")
    choices = []
    for account, slots in core.checkpoints.native_slots(user).items():
        for slot in slots:
            path = core.plain_path(Path(user) / "save" / account / slot / "progress.sav", directory=False)
            choices.append((path.stat().st_mtime_ns, account, slot))
    if not choices:
        raise ValueError("No complete native save exists. Save in-game before capturing a checkpoint")
    _, account, slot = max(choices)
    return account, slot


def unused_profile(game):
    for number in range(2, 10):
        if not core.profile_folder(game, number).exists():
            return number
    raise ValueError("All profiles are occupied. Use the launcher's checkpoint restore tools to choose a destination")


def read_request(path):
    core.plain_path(path, directory=False)
    if path.stat().st_size > 256:
        raise ValueError("Oversized player-tools request")
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 3 or lines[0] != "LSP1" or not lines[2].isdigit():
        raise ValueError("Invalid player-tools request")
    pid = int(lines[2])
    fields = lines[1].split()
    if fields == ["capture"]:
        return "capture", None, pid
    if len(fields) == 2 and fields[0] == "shortcut" and fields[1] in ("0", "1", "2"):
        return "shortcut", int(fields[1]), pid
    if len(fields) == 2 and fields[0] == "restore" and len(fields[1]) == 16 and all(c in "0123456789abcdef" for c in fields[1]):
        return "restore", fields[1], pid
    raise ValueError("Unknown player-tools request")


class Session:
    def __init__(self, game, number, romfs=None, exefs=None):
        core.closed_games()
        self.game = core.plain_path(game)
        self.number, self.romfs, self.exefs = number, romfs, exefs
        self.endpoint = "longshot-tools-" + uuid.uuid4().hex
        if os.name != "nt":
            self.endpoint = str(Path(tempfile.gettempdir()) / (self.endpoint + ".sock"))
        self.directory = core.plain_path(self.game / "longshot-player-tools" / "sessions" / uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        self.prefs = self.directory.parent.parent / "settings.json"
        self.shortcut = 0
        if self.prefs.exists():
            core.plain_path(self.prefs, directory=False)
            if self.prefs.stat().st_size > 4096:
                raise ValueError("Player tools settings are oversized")
            prefs = json.loads(self.prefs.read_text(encoding="utf-8"))
            self.shortcut = prefs.get("shortcut", 0)
            if type(self.shortcut) is not int or self.shortcut not in (0, 1, 2):
                raise ValueError("Invalid shortcut settings")
        self.stop_event = threading.Event()
        self.entries = {}
        self.message = f"Profile {number}. Save in-game first. Checkpoints load into an unused profile."
        self.current = None
        self.identity = None
        self.resume_checkpoint = False
        self.publish()
        self.launch()
        self.thread = threading.Thread(target=self.run, name="Longshot player tools", daemon=True)
        self.thread.start()

    def launch(self):
        command, env = core.launch_plan(self.game, self.number, self.romfs)
        env.update(HOS_CONTROL=self.endpoint, HOS_CONTROL_MEM="0", LONGSHOT_PLAYER_TOOLS_DIR=str(self.directory))
        if self.resume_checkpoint:
            env["HOS_SKIP_TITLE"] = "1"
        env.pop("HOS_INPUT_EXCLUSIVE", None)
        env.pop("HOS_INPUT_SCRIPT", None)
        user = core.profile_folder(self.game, self.number)
        user.mkdir(parents=True, exist_ok=True)
        core.plain_path(user)
        self.current = subprocess.Popen(command, cwd=self.game, env=env)

    def scan(self):
        if self.identity is None:
            self.identity = core.checkpoints.game_identity(self.game, self.exefs)
        folder = core.plain_path(self.game / "longshot-checkpoints")
        if not folder.exists():
            return
        rows = []
        for path in list(folder.glob("*.hsc")) + list(folder.glob("*.state")):
            try:
                core.plain_path(path, directory=False)
                info = core.checkpoints.read_state(path)
                core.checkpoints.validated_files(info)
                plan = core.checkpoints.choose_restore(info, self.identity, binding=info.binding,
                        portable_providers={core.checkpoints.PROVIDER: core.checkpoints.SCHEMA})
                if plan.mode != "portable":
                    continue
                rows.append((path.stat().st_mtime_ns, path))
            except (OSError, ValueError, core.checkpoints.CheckpointError):
                continue
        self.entries = {hashlib.sha256(str(path).encode()).hexdigest()[:16]: path
                        for _, path in sorted(rows, reverse=True)[:32]}

    def publish(self):
        clean = lambda value: " ".join(str(value).split())[:180]
        text = "LSP1\n" + clean(self.message) + "\n" + str(self.shortcut) + "\n"
        text += "".join(key + "\t" + clean(path.stem) + "\n" for key, path in self.entries.items())
        # Antivirus and an older renderer can briefly hold a Windows file open.
        # A transient sharing violation must not kill the service thread.
        for attempt in range(5):
            try:
                mods.atomic_text(self.directory / "state.txt", text)
                return
            except PermissionError:
                if attempt == 4:
                    return  # heartbeat expires visibly; the next loop retries
                time.sleep(.02)

    def quit_owned(self):
        if self.current.poll() is not None:
            raise ValueError("The game has already closed")
        bridge = Bridge(self.endpoint)
        try:
            reply = bridge.request("quit")
            if not reply.get("ok"):
                raise ValueError("The game declined to exit; no save files were changed")
        finally:
            bridge.close()
        try:
            self.current.wait(timeout=45)
        except subprocess.TimeoutExpired as error:
            raise ValueError("Game is still closing; no checkpoint was captured or restored") from error
        core.closed_games()

    def perform(self, action, argument):
        if action == "shortcut":
            mods.atomic_text(self.prefs, json.dumps({"schema": 1, "shortcut": argument}) + "\n")
            self.shortcut = argument
            return
        user = core.profile_folder(self.game, self.number)
        if action == "capture":
            latest_slot(user)  # Refuse before exiting if no complete save exists.
        else:
            if argument not in self.entries:
                raise ValueError("Checkpoint list changed; reopen the browser")
            target = self.entries[argument]
            next_profile = unused_profile(self.game)
            # Recheck compatibility and payload before the user loses the running session.
            info = core.checkpoints.read_state(target)
            core.checkpoints.validated_files(info)
            current_identity = core.checkpoints.game_identity(self.game, self.exefs)
            plan = core.checkpoints.choose_restore(info, current_identity, binding=info.binding,
                    portable_providers={core.checkpoints.PROVIDER: core.checkpoints.SCHEMA})
            if plan.mode != "portable":
                raise ValueError(plan.reason)
        self.message = "Closing the game safely before the checkpoint operation..."
        self.publish()
        self.quit_owned()
        try:
            if action == "capture":
                account, slot = latest_slot(user)
                folder = core.plain_path(self.game / "longshot-checkpoints")
                folder.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                target = folder / f"profile-{self.number}-{stamp}-{secrets.token_hex(3)}.hsc"
                core.checkpoints.capture(self.game, user, account, slot[5:], target, exefs=self.exefs)
                self.message = "Captured " + target.stem + f". Continuing profile {self.number}."
            else:
                destination = core.profile_folder(self.game, next_profile)
                destination.parent.mkdir(parents=True, exist_ok=True)
                core.checkpoints.prepare(self.game, target, destination, exefs=self.exefs)
                self.number = next_profile
                self.message = f"Restored {target.stem} into profile {next_profile}. Existing profiles are kept."
        except Exception:
            self.launch()  # A failed archive/restore resumes the original profile, never a partial destination.
            raise
        self.resume_checkpoint = True
        self.scan()
        self.publish()
        self.launch()

    def run(self):
        next_scan = 0
        while not self.stop_event.wait(.2):
            try:
                if time.monotonic() >= next_scan:
                    self.scan()
                    next_scan = time.monotonic() + 10
                request = self.directory / "request.txt"
                if request.exists():
                    try:
                        action, argument, pid = read_request(request)
                    finally:
                        request.unlink()
                    if pid != self.current.pid:
                        raise ValueError("Ignored a request from an earlier game session")
                    self.perform(action, argument)
                self.publish()
                if self.current.poll() is not None:
                    break
            except Exception as error:
                self.message = "Checkpoint operation stopped: " + str(error)
                self.publish()
                if self.current.poll() is not None:
                    break

    def close(self):
        self.stop_event.set()
        # No termination of the game; the native browser disables itself when its heartbeat expires.

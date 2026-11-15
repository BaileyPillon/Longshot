"""Opt-in local co-op hosting and per-session tunic overlays."""
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import longshot_launcher_core as core

COLORS = ("green", "blue", "red", "purple", "cyan", "orange", "yellow", "pink", "white", "black")


def invite_endpoint(address, port):
    if (not re.fullmatch(r"[A-Za-z0-9._-]{1,253}", address)
            or type(port) is not int or not 1 <= port <= 65535):
        raise ValueError("Enter a host name or IPv4 address and a port from 1 to 65535")
    return f"{address}:{port}"


def read_invite(text):
    address, separator, port = text.strip().partition(":")
    if not separator or not re.fullmatch(r"[0-9]{1,5}", port):
        raise ValueError("Paste a party address in host:port form")
    invite_endpoint(address, int(port))
    return address, int(port)


def server_plan(executable, bind, port, password, *, pvp=False):
    executable = core.plain_path(executable, directory=False)
    if not executable.is_file():
        raise ValueError("Choose the built coop_server executable")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Choose a port from 1 to 65535")
    address = ipaddress.IPv4Address(bind)
    if not password or len(password.encode()) > 128 or any(ord(c) < 32 or ord(c) == 127 for c in password):
        raise ValueError("Use a session password of 1 to 128 UTF-8 bytes without control characters")
    env = dict(os.environ)
    env["LONGSHOT_PARTY_SECRET"] = password
    command = [str(executable), "--bind", str(address), "--port", str(port),
               "--password-env", "LONGSHOT_PARTY_SECRET", "--pvp", "on" if pvp else "off"]
    if not address.is_loopback:
        command += ["--allow", "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]
    return command, env


class Server:
    """Own exactly the child created here; no process-name kills or router edits."""
    def __init__(self, executable, bind, port, password, directory, *, pvp=False):
        command, env = server_plan(executable, bind, port, password, pvp=pvp)
        directory = core.plain_path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.log = directory / f"server-{uuid.uuid4().hex}.log"
        with self.log.open("xb") as output:
            self.process = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT,
                                            stdin=subprocess.DEVNULL, cwd=directory,
                                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.port, self.bind = port, bind
        # A live process alone is not listening. The server emits this after ENet binds.
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise ValueError("The party server could not start. Check its log: " + str(self.log))
            if f"listening on port {port}" in self.log.read_text(errors="replace"):
                return
            time.sleep(.05)
        self.stop()
        raise ValueError("The server did not confirm that it was listening. Check: " + str(self.log))

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)


def tunic_overlay(game, color):
    if color not in COLORS:
        raise ValueError("Choose one of the available tunic colors")
    if color == "green":
        return None
    game = core.plain_path(game)
    pack = core.plain_path(game / "mods/contents/0400486024DEC000/coop-puppet")
    metadata = core.plain_path(pack / "coop_puppet.json", directory=False)
    if metadata.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Co-op pack metadata is oversized")
    meta = json.loads(metadata.read_text(encoding="utf-8"))
    if not meta.get("tunics", {}).get("green"):
        raise ValueError("Regenerate the puppet pack with tunic support before choosing a color")
    files = meta.get("self_files", {}).get(color)
    if not isinstance(files, dict) or not 1 <= len(files) <= 16 or "Tex/Angin_Tile_A_Alb.bntx.zs" not in files:
        raise ValueError("This pack has no complete self-tunic set for that color")
    sources = {}
    for target, relative in files.items():
        if not re.fullmatch(r"(?:Tex/[A-Za-z0-9_]+\.bntx\.zs|Model/Player_(?:Adult|Child)\.Player_(?:Adult|Child)\.bfres\.zs)", target):
            raise ValueError("Unexpected tunic target in puppet pack")
        if not isinstance(relative, str) or "\\" in relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("Invalid tunic source in puppet pack")
        source = core.plain_path(pack / relative, directory=False)
        if not source.is_file() or not 0 < source.stat().st_size <= 64 * 1024 * 1024:
            raise ValueError("Missing or oversized tunic file")
        sources[target] = source
    root = core.plain_path(game / "longshot-coop" / "tunics" / uuid.uuid4().hex)
    root.mkdir(parents=True)
    for target, source in sources.items():
        destination = root / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return root


def start_game(game, number, server, port, name, password, color="green", romfs=None):
    core.closed_games()
    command, env = core.coop_launch_plan(game, number, server, port, name, password, romfs)
    overlay = tunic_overlay(game, color)
    env["LICHII_COOP_COLOR"] = color
    env["LICHII_COOP_SELF_TUNIC"] = color
    if overlay:
        env["HOS_FS_OVERLAY"] = str(overlay)
    user = core.profile_folder(game, number)
    user.mkdir(parents=True, exist_ok=True)
    core.plain_path(user)
    return subprocess.Popen(command, cwd=game, env=env)

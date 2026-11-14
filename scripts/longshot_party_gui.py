"""Host or join a party with the pinned native co-op module."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import longshot_party as party


class PartyWindow:
    def __init__(self, launcher):
        self.launcher = launcher
        self.server = None
        self.window = tk.Toplevel(launcher.window)
        self.window.title("Co-op party — Longshot")
        self.window.geometry("670x685")
        self.window.minsize(620, 645)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        pane = ttk.Frame(self.window, padding=20)
        pane.pack(fill="both", expand=True)
        ttk.Label(pane, text="Co-op party", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(pane, text="Host on this PC or join a friend's server. Use a separate co-op profile.",
                  wraplength=610).pack(anchor="w", pady=(6, 16))
        grid = ttk.Frame(pane)
        grid.pack(fill="x")
        self.values = {key: tk.StringVar(value=value) for key, value in (
            ("profile", launcher.profile.get() if launcher.profile.get() != "1" else "2"),
            ("address", "127.0.0.1"), ("port", "27510"), ("name", "Player"),
            ("password", ""), ("color", "green"), ("network", "This PC only"))}
        for row, (key, title) in enumerate((("profile", "Co-op save profile"), ("name", "Player name"),
                ("color", "Kokiri tunic & name color"), ("address", "Server address"), ("port", "Port"),
                ("password", "Session password"), ("network", "Host access"))):
            ttk.Label(grid, text=title).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))
            choices = {"profile": list(map(str, range(2, 10))), "color": party.COLORS,
                       "network": ("This PC only", "Local network")}.get(key)
            field = (ttk.Combobox(grid, textvariable=self.values[key], values=choices, state="readonly", width=30)
                     if choices else ttk.Entry(grid, textvariable=self.values[key], width=33,
                                               show="*" if key == "password" else ""))
            field.grid(row=row, column=1, sticky="ew", pady=6)
        self.pvp = tk.BooleanVar(value=False)
        ttk.Checkbutton(pane, text="Allow players to damage each other (host setting)", variable=self.pvp).pack(anchor="w", pady=(12, 8))
        ttk.Label(pane, text="Tunic colors use your generated co-op pack. Goron and Zora tunics keep their own colors.\n"
                  "Local network hosting accepts private LAN addresses. Router forwarding is not changed.",
                  wraplength=610).pack(anchor="w", pady=8)
        default_server = Path(__file__).resolve().parents[1] / "work/fork-research/coop-build/server/Release/coop_server.exe"
        self.executable = tk.StringVar(value=str(default_server) if default_server.is_file() else "")
        row = ttk.Frame(pane)
        row.pack(fill="x", pady=8)
        ttk.Button(row, text="Choose server program…", command=self.choose_server).pack(side="left")
        ttk.Label(row, textvariable=self.executable, wraplength=405).pack(side="left", padx=10)
        self.status = tk.StringVar(value="No server hosted. A password is required for every session.")
        ttk.Label(pane, textvariable=self.status, wraplength=610).pack(anchor="w", pady=12)
        row = ttk.Frame(pane)
        row.pack(fill="x", pady=8)
        self.host_button = ttk.Button(row, text="Start hosting", command=lambda: launcher.guard(self.host))
        self.host_button.pack(side="left")
        ttk.Button(row, text="Stop hosting", command=self.stop).pack(side="left", padx=8)
        ttk.Button(row, text="Join & play", command=lambda: launcher.guard(self.join)).pack(side="right")
        row = ttk.Frame(pane)
        row.pack(fill="x", pady=(0, 4))
        ttk.Button(row, text="Copy party address", command=lambda: launcher.guard(self.copy_invite)).pack(side="left")
        ttk.Button(row, text="Paste party address", command=lambda: launcher.guard(self.paste_invite)).pack(side="left", padx=8)
        self.poll()

    def copy_invite(self):
        address = self.values["address"].get().strip()
        port = self.values["port"].get()
        if self.server and self.server.bind == "0.0.0.0":
            address = simpledialog.askstring("Party address", "Enter the LAN address friends use to reach this PC.", parent=self.window)
            if address is None:
                return
            port = str(self.server.port)
        invite = party.invite_endpoint(address, int(port))
        self.window.clipboard_clear()
        self.window.clipboard_append(invite)
        self.status.set("Party address copied. Share the session password separately.")

    def paste_invite(self):
        address, port = party.read_invite(self.window.clipboard_get())
        self.values["address"].set(address)
        self.values["port"].set(str(port))
        self.status.set("Party address loaded. Enter the session password before joining.")

    def choose_server(self):
        name = filedialog.askopenfilename(parent=self.window, title="Choose coop_server", filetypes=[("Server program", "*.exe"), ("All files", "*")])
        if name:
            self.executable.set(name)

    def host(self):
        if self.server and self.server.process.poll() is None:
            raise ValueError("This window is already hosting a party")
        address = "127.0.0.1" if self.values["network"].get() == "This PC only" else "0.0.0.0"
        port, password = int(self.values["port"].get()), self.values["password"].get()
        executable, pvp = Path(self.executable.get()), self.pvp.get()
        game = self.launcher.require_game()
        self.host_button.configure(state="disabled")
        def started(server):
            self.server = server
            self.values["address"].set("127.0.0.1")
            self.status.set(f"Hosting on {address}:{port}. Join below to start your game. Friends use this PC's LAN address.")
            self.host_button.configure(state="normal")
        self.launcher.task("Starting co-op server…", lambda: party.Server(executable, address, port, password,
                            game / "longshot-coop/logs", pvp=pvp), started)

    def join(self):
        v = {k: value.get() for k, value in self.values.items()}
        game = self.launcher.require_game()
        def started(child):
            self.launcher.child = child
            self.launcher.journal_session = None
            self.status.set(f"Game started with profile {v['profile']}, {v['color']} tunic. Press F6 in-game for the player list.")
            self.values["password"].set("")
        self.launcher.task("Joining co-op…", lambda: party.start_game(game, int(v["profile"]), v["address"].strip(),
                            int(v["port"]), v["name"], v["password"], v["color"], self.launcher.romfs), started)

    def stop(self):
        if self.server and self.server.process.poll() is None:
            if not messagebox.askyesno("Stop hosting", "Disconnect everyone from this hosted party? The game stays open.", parent=self.window):
                return False
            self.server.stop()
            self.status.set("Hosting stopped. Enter a password and start hosting to create another party.")
        return True

    def poll(self):
        if not self.launcher.busy:
            self.host_button.configure(state="normal")
        if self.server and self.server.process.poll() is not None:
            self.status.set("The server has stopped. Log: " + str(self.server.log))
            self.server = None
        self.window.after(750, self.poll)

    def close(self):
        if self.launcher.busy:
            self.status.set("Wait for the current operation to finish before closing.")
            return False
        if not self.stop():
            return False
        self.window.destroy()
        return True

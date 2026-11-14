"""Longshot's local game, save and companion launcher (Python with Tk)."""
import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import longshot_launcher_core as core
import longshot_companions as companions
import longshot_save_packages as save_packages
from longshot_mods_gui import Manager


class Launcher:
    def __init__(self, window, game=None, romfs=None, exefs=None):
        self.window, self.game = window, Path(game).resolve() if game else None
        self.romfs, self.exefs = romfs, exefs
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.busy, self.buttons = False, []
        self.child = None
        self.journal = None
        self.journal_session = None
        self.party = None
        self.player_tools = None
        window.title("Longshot")
        window.geometry("1020x760")
        window.minsize(840, 640)
        window.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(window)
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Treeview", rowheight=28)
        pane = ttk.Frame(window, padding=20)
        pane.pack(fill="both", expand=True)
        ttk.Label(pane, text="Longshot", style="Title.TLabel").pack(anchor="w")
        row = ttk.Frame(pane)
        row.pack(fill="x", pady=(10, 12))
        self.button(row, "Choose game folder…", self.choose).pack(side="left")
        self.location = tk.StringVar(value=str(self.game or "Choose your experimental Longshot game folder"))
        ttk.Label(row, textvariable=self.location, wraplength=720).pack(side="left", padx=12)
        tabs = ttk.Notebook(pane)
        tabs.pack(fill="both", expand=True)
        play, saves, hardware = (ttk.Frame(tabs, padding=16) for _ in range(3))
        for frame, title in ((play, "Play"), (saves, "Saves & checkpoints"), (hardware, "This PC")):
            tabs.add(frame, text=title)
        self.profile = tk.StringVar(value="1")
        row = ttk.Frame(play)
        row.pack(fill="x", pady=(4, 12))
        ttk.Label(row, text="Save profile").pack(side="left", padx=(0, 12))
        self.selector = ttk.Combobox(row, textvariable=self.profile, values=list(map(str, range(1, 10))), width=5, state="readonly")
        self.selector.pack(side="left")
        self.selector.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        self.button(row, "Play Longshot", self.play).pack(side="left", padx=16)
        self.button(row, "Play with journal", self.play_journal).pack(side="left")
        self.button(row, "Play with tools", self.play_tools).pack(side="left", padx=8)
        self.profile_text = tk.StringVar()
        ttk.Label(play, textvariable=self.profile_text, wraplength=860).pack(anchor="w", pady=(0, 20))
        ttk.Label(play, text="Tools", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(8, 8))
        for label, explanation, callback in (
            ("Manage mods", "Save named loadouts, preview conflicts, switch setups and undo.", self.mods),
            ("Completion tracker", "Read this profile's saves. Build the tracker once with the companion tool.", lambda: self.companion("tracker")),
            ("Co-op party…", "Host or join a party, choose a tunic color and use a separate profile.", self.coop),
            ("Randomized adventure…", "Pick a preset, share a seed recipe, or set up Archipelago multiworld.", self.adventure),
            ("Randomizer", "Generate a separate seed and playthrough. Some seeds may be unbeatable.", lambda: self.companion("randomizer"))):
            row = ttk.Frame(play)
            row.pack(fill="x", pady=7)
            self.button(row, label, callback, width=23).pack(side="left")
            ttk.Label(row, text=explanation, wraplength=600).pack(side="left", padx=16)
        ttk.Label(play, text="Graphics and controller settings stay in the game’s Insert menu.\n"
                  "This launcher uses the profile selected above. Co-op and inherited randomizer overlays are off for ordinary play.",
                  wraplength=850).pack(anchor="w", pady=24)
        ttk.Label(saves, text="Native saves", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(saves, text="Save in the game and close it before transferring or capturing saves. A ZIP contains every completed slot in the selected account.",
                  wraplength=860).pack(anchor="w", pady=(4, 8))
        self.slots = self.table(saves, (("account", "Account", 380), ("slot", "Save slot", 130)), height=4)
        row = ttk.Frame(saves)
        row.pack(fill="x", pady=8)
        self.button(row, "Capture selected save", self.capture).pack(side="left")
        self.button(row, "Export account ZIP…", self.export_save_package).pack(side="left", padx=8)
        self.button(row, "Import save ZIP…", self.import_save_package).pack(side="left")
        self.button(row, "Import save folder…", self.import_save).pack(side="left", padx=8)
        self.button(row, "Refresh", self.refresh).pack(side="right")
        ttk.Label(saves, text="Checkpoints", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(16, 8))
        self.archives = self.table(saves, (("name", "Checkpoint", 380), ("slot", "Save slot", 130), ("status", "Status", 200)), height=4)
        row = ttk.Frame(saves)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="New profile for import / restore").pack(side="left")
        self.restore_number = tk.StringVar(value="2")
        self.restore_selector = ttk.Combobox(row, textvariable=self.restore_number, values=list(map(str, range(2, 10))), width=5, state="readonly")
        self.restore_selector.pack(side="left", padx=8)
        self.button(row, "Restore selected checkpoint", self.restore).pack(side="left")
        self.hardware_text = tk.StringVar(value="Hardware has not been read yet.")
        ttk.Label(hardware, textvariable=self.hardware_text, wraplength=850).pack(anchor="w", pady=(0, 12))
        self.button(hardware, "Read this PC", self.read_hardware).pack(anchor="w", pady=(0, 14))
        self.advice = tk.Text(hardware, height=16, wrap="word", font=("Segoe UI", 10), padx=12, pady=10, state="disabled")
        self.advice.pack(fill="both", expand=True)
        ttk.Label(hardware, text="Starting points only. No settings are changed automatically; compare in-game results on this PC.",
                  wraplength=850).pack(anchor="w", pady=(10, 0))
        self.status = tk.StringVar(value="Ready")
        ttk.Label(pane, textvariable=self.status, wraplength=940).pack(anchor="w", pady=(12, 0))
        self.refresh()

    def button(self, parent, text, command, **kwargs):
        button = ttk.Button(parent, text=text, command=lambda: self.guard(command), **kwargs)
        self.buttons.append(button)
        return button

    def guard(self, callback):
        if self.busy:
            return
        try:
            callback()
        except Exception as error:
            self.status.set(str(error))
            messagebox.showerror("Longshot", str(error), parent=self.window)

    def table(self, parent, columns, **kwargs):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", selectmode="browse", **kwargs)
        for name, heading, width in columns:
            tree.heading(name, text=heading)
            tree.column(name, width=width, minwidth=80)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

    def task(self, label, work, completed):
        self.busy = True
        self.status.set(label)
        for button in self.buttons:
            button.configure(state="disabled")
        for selector in (self.selector, self.restore_selector):
            selector.configure(state="disabled")
        future = self.pool.submit(work)
        def poll():
            if not future.done():
                self.window.after(100, poll)
                return
            self.busy = False
            for button in self.buttons:
                button.configure(state="normal")
            for selector in (self.selector, self.restore_selector):
                selector.configure(state="readonly")
            self.guard(lambda: completed(future.result()))
        self.window.after(100, poll)

    def require_game(self):
        if not self.game:
            raise ValueError("Choose your Longshot game folder first")
        core.launch_plan(self.game, int(self.profile.get()), self.romfs)
        return self.game

    def choose(self):
        chosen = filedialog.askdirectory(title="Choose your experimental Longshot game folder", parent=self.window)
        if chosen:
            core.launch_plan(chosen, 1, self.romfs)
            self.game = Path(chosen).resolve()
            self.location.set(str(self.game))
            self.refresh()

    def refresh(self):
        self.slots.delete(*self.slots.get_children())
        self.archives.delete(*self.archives.get_children())
        if not self.game:
            self.profile_text.set("Choose a built game folder. Profile 1 keeps its original saves; profiles 2–9 are separate playthroughs.")
            return
        user = core.profile_folder(self.game, int(self.profile.get()))
        self.profile_text.set(f"Profile {self.profile.get()} · {user}\n" + ("Existing profile." if user.exists() else "New playthrough: no progress in this profile yet."))
        if (user / "save").is_dir():
            for account, slots in core.checkpoints.native_slots(user).items():
                for slot in slots:
                    self.slots.insert("", "end", iid=f"{account}/{slot}", values=(account, slot))
        folder = self.game / "longshot-checkpoints"
        # Use the existing CLI's extension; retain archives made by early launchers.
        archives = list(folder.glob("*.hsc")) + list(folder.glob("*.state"))
        for path in sorted(archives, reverse=True):
            try:
                info = core.checkpoints.read_state(path)
                core.checkpoints.validated_files(info)
                slot, status = info.binding.slot, "Ready for compatibility check"
            except Exception:
                slot, status = "—", "Invalid or unsupported"
            self.archives.insert("", "end", iid=path.name, values=(path.stem, slot, status))

    def play(self):
        self.require_game()
        self.child = core.start_game(self.game, int(self.profile.get()), self.romfs)
        self.journal_session = None
        self.status.set(f"Started Longshot with save profile {self.profile.get()}.")

    def play_tools(self):
        from longshot_player_tools import Session
        game, number = self.require_game(), int(self.profile.get())
        def started(session):
            if self.journal and self.journal.window.winfo_exists():
                self.journal.close()
            self.player_tools = session
            self.child = session.current
            self.journal_session = (session.endpoint, game / "longshot-journal" / f"profile-{number}.json", number)
            self.status.set(f"Started profile {number} with player tools. Press F5 or choose Insert → Gameplay → Checkpoints.")
            self.watch_player_tools(session)
        self.task("Starting player tools…", lambda: Session(game, number, self.romfs, self.exefs), started)

    def watch_player_tools(self, session):
        if self.player_tools is not session:
            return
        self.child = session.current
        if session.number != int(self.profile.get()):
            self.profile.set(str(session.number))
            reopen_journal = self.journal and self.journal.window.winfo_exists()
            if reopen_journal:
                self.journal.close()
            self.journal_session = (session.endpoint, session.game / "longshot-journal" / f"profile-{session.number}.json", session.number)
            if reopen_journal:
                from longshot_journal import JournalWindow
                endpoint, notes, number = self.journal_session
                self.journal = JournalWindow(tk.Toplevel(self.window), endpoint, notes, str(number))
            self.refresh()
            self.status.set(session.message)
        if session.current.poll() is None or session.thread.is_alive():
            self.window.after(500, lambda: self.watch_player_tools(session))

    def play_journal(self):
        from longshot_journal import JournalWindow
        game = self.require_game()
        number = int(self.profile.get())
        if self.child and self.child.poll() is None:
            if not self.journal_session:
                raise ValueError("This game started without the journal. Save and close it before choosing Play with journal.")
            if self.journal and self.journal.window.winfo_exists():
                self.journal.window.deiconify()
                self.journal.window.lift()
            else:
                endpoint, notes, original_profile = self.journal_session
                self.journal = JournalWindow(tk.Toplevel(self.window), endpoint, notes, str(original_profile))
                self.status.set(f"Reopened Adventure Journal for the running profile {original_profile}.")
            return
        if self.journal and self.journal.window.winfo_exists():
            self.journal.close()
        endpoint = "longshot-journal-" + uuid.uuid4().hex
        if os.name != "nt":
            endpoint = str(Path(tempfile.gettempdir()) / (endpoint + ".sock"))
        window = tk.Toplevel(self.window)
        try:
            notes = game / "longshot-journal" / f"profile-{number}.json"
            journal = JournalWindow(window, endpoint, notes,
                                    str(number), start_reader=False)
            self.child = core.start_game(game, number, self.romfs, journal_endpoint=endpoint)
        except Exception:
            window.destroy()
            raise
        self.journal = journal
        self.journal_session = (endpoint, notes, number)
        journal.reader.start()
        self.status.set(f"Started profile {number} with Adventure Journal. Load a save to begin live tracking.")

    def mods(self):
        self.require_game()
        Manager(tk.Toplevel(self.window), self.game / "mods")

    def coop(self):
        self.require_game()
        if self.party and self.party.window.winfo_exists():
            self.party.window.lift()
            return
        from longshot_party_gui import PartyWindow
        self.party = PartyWindow(self)

    def companion(self, name):
        self.require_game()
        game, user = self.game, core.profile_folder(self.game, int(self.profile.get()))
        def work():
            directory = companions.prepare(name)
            command, env = companions.launch_plan(name, directory, game=game, saves=user)
            return subprocess.Popen(command, cwd=directory, env=env)
        self.task(f"Opening {name}…", work, lambda _: self.status.set(f"Opened {name}."))

    def adventure(self):
        from longshot_adventure_gui import open_adventure
        open_adventure(self)

    def import_save(self):
        game = self.require_game()
        number = int(self.restore_number.get())
        if core.profile_folder(game, number).exists():
            raise ValueError(f"Profile {number} already exists. Select a new profile in Saves & checkpoints.")
        selected = filedialog.askdirectory(title=f"Import into profile {number}: choose the folder with account.sav and slot folders", parent=self.window)
        if selected:
            self.task("Copying and verifying native saves…", lambda: core.import_save(selected, game, number),
                      lambda result: self.saved(f"Imported {len(result['slots'])} save slots into new profile {number}. Originals preserved.", number))

    def export_save_package(self):
        game = self.require_game()
        chosen = self.slots.selection()
        if not chosen:
            raise ValueError("Select a save slot to export its account")
        core.closed_games()
        account, _ = chosen[0].split("/")
        profile = int(self.profile.get())
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = filedialog.asksaveasfilename(title=f"Export all slots for profile {profile}",
                                           initialfile=f"Longshot-profile-{profile}-{stamp}.zip",
                                           defaultextension=".zip", filetypes=[("Save ZIP", "*.zip")], parent=self.window)
        if path:
            self.task("Exporting and verifying the save ZIP…", lambda: save_packages.export_package(game, profile, account, path),
                      lambda result: self.status.set(f"Exported {len(result['slots'])} save slots to {result['path']}"))

    def import_save_package(self):
        game = self.require_game()
        number = int(self.restore_number.get())
        core.closed_games()
        if core.profile_folder(game, number).exists():
            raise ValueError(f"Profile {number} already exists. Select an unused profile for import / restore.")
        path = filedialog.askopenfilename(title=f"Import a Longshot or NX2navi save ZIP into profile {number}",
                                          filetypes=[("Save ZIP", "*.zip")], parent=self.window)
        if path:
            self.task("Checking the save ZIP and creating a new profile…", lambda: save_packages.import_package(path, game, number),
                      lambda result: self.saved(f"Imported {len(result['slots'])} save slots into new profile {number}.", number))

    def capture(self):
        game = self.require_game()
        chosen = self.slots.selection()
        if not chosen:
            raise ValueError("Select a native save slot to capture")
        account, slot = chosen[0].split("/")
        user = core.profile_folder(game, int(self.profile.get()))
        folder = core.plain_path(game / "longshot-checkpoints")
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = folder / f"{stamp}-profile{self.profile.get()}-{slot}-{uuid.uuid4().hex[:6]}.hsc"
        self.task("Capturing and verifying this native save…",
                  lambda: core.checkpoints.capture(game, user, account, slot[5:], path, exefs=self.exefs),
                  lambda _: self.saved(f"Captured {slot}. Its original save is unchanged."))

    def restore(self):
        game = self.require_game()
        core.closed_games()
        chosen = self.archives.selection()
        if not chosen:
            raise ValueError("Select a checkpoint to restore")
        number = int(self.restore_number.get())
        destination = core.profile_folder(game, number)
        destination.parent.mkdir(parents=True, exist_ok=True)
        path = game / "longshot-checkpoints" / chosen[0]
        self.task("Checking compatibility and restoring into a new profile…",
                  lambda: core.checkpoints.prepare(game, path, destination, exefs=self.exefs),
                  lambda _: self.saved(f"Restored checkpoint into profile {number}. Existing profiles are unchanged.", number))

    def saved(self, message, number=None):
        if number is not None:
            self.profile.set(str(number))
        self.refresh()
        self.status.set(message)

    def read_hardware(self):
        def show(info):
            gpus = [g['name'] + (f" · {g['vram_gib']} GiB VRAM" if 'vram_gib' in g else "") for g in info['gpus']]
            self.hardware_text.set(f"{info['cpu']}\nRAM: {info['ram_gib'] or 'Unknown'} GiB\n" + ("\n".join(gpus) or "GPU not detected"))
            self.advice.configure(state="normal")
            self.advice.delete("1.0", "end")
            self.advice.insert("1.0", "\n\n".join(f"{name} — {value}\n{reason}" for name, value, reason in core.recommendations(info)))
            self.advice.configure(state="disabled")
            self.status.set("Hardware read. Your game and Windows settings were not changed.")
        self.task("Reading this PC’s hardware…", core.hardware_info, show)

    def close(self):
        if self.busy:
            self.status.set("Wait for the current operation to finish before closing.")
            return
        if self.party and self.party.window.winfo_exists() and not self.party.close():
            return
        if self.player_tools and self.player_tools.thread.is_alive():
            if not messagebox.askyesno("Close Longshot launcher", "Closing this launcher disables in-game checkpoint tools. The game stays open. Close anyway?", parent=self.window):
                return
            self.player_tools.close()
        self.pool.shutdown(wait=False)
        if self.journal and self.journal.window.winfo_exists():
            self.journal.close()
        self.window.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path)
    parser.add_argument("--romfs", type=Path, help="optional external assets, useful for development builds")
    parser.add_argument("--exefs", type=Path, help="optional retained ExeFS for checkpoint compatibility checks")
    args = parser.parse_args()
    window = tk.Tk()
    Launcher(window, args.game, args.romfs, args.exefs)
    window.mainloop()


if __name__ == "__main__":
    main()

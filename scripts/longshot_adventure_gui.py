"""Choose and share a recipe, then review/generate in isolated OoTrR."""
import secrets
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

import longshot_adventure as adventure
import longshot_companions as companions


def open_adventure(launcher):
    game = launcher.require_game()
    window = tk.Toplevel(launcher.window)
    window.title("Randomized adventure — Longshot")
    window.geometry("650x545")
    window.minsize(620, 520)
    pane = ttk.Frame(window, padding=20)
    pane.pack(fill="both", expand=True)
    ttk.Label(pane, text="Randomized adventure", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(pane, text="Choose a recipe, then review its logic and generate it in the separate randomizer installation.",
              wraplength=590).pack(anchor="w", pady=(8, 16))
    preset = tk.StringVar(value=adventure.PRESETS["prudent"])
    seed = tk.StringVar(value=secrets.token_hex(8))
    featured = ttk.Combobox(pane, values=list(adventure.FEATURED), state="readonly", width=35)
    featured.set("Choose a featured challenge…")
    featured.pack(anchor="w", pady=(0, 12))

    def choose_featured(_event):
        style, value = adventure.FEATURED[featured.get()]
        preset.set(adventure.PRESETS[style])
        seed.set(value)
        code.set(adventure.share_code(style, value))
        status.set("Featured recipe loaded. Copy the code to share this setup with friends.")

    featured.bind("<<ComboboxSelected>>", choose_featured)
    ttk.Label(pane, text="Adventure style").pack(anchor="w")
    ttk.Combobox(pane, textvariable=preset, values=list(adventure.PRESETS.values()), state="readonly", width=38).pack(anchor="w", pady=(4, 10))
    ttk.Label(pane, text="Seed").pack(anchor="w")
    row = ttk.Frame(pane)
    row.pack(fill="x", pady=(4, 16))
    ttk.Entry(row, textvariable=seed).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text="New seed", command=lambda: seed.set(secrets.token_hex(8))).pack(side="left", padx=(8, 0))
    ttk.Label(pane, text="Adventure code · share a recipe or paste one from a friend").pack(anchor="w")
    code = tk.StringVar()
    ttk.Entry(pane, textvariable=code).pack(fill="x", pady=(4, 8))
    def selected():
        return next(k for k, v in adventure.PRESETS.items() if v == preset.get())
    def copy():
        value = adventure.share_code(selected(), seed.get())
        code.set(value)
        window.clipboard_clear()
        window.clipboard_append(value)
        status.set("Recipe copied. The same generator version and unchanged preset are required to reproduce it.")
    def use():
        value = adventure.from_code(code.get())
        preset.set(adventure.PRESETS[value["preset"]])
        seed.set(value["seed"])
        status.set("Recipe loaded. Review settings before generation.")
    row = ttk.Frame(pane)
    row.pack(fill="x")
    ttk.Button(row, text="Copy recipe", command=lambda: launcher.guard(copy)).pack(side="left")
    ttk.Button(row, text="Use pasted recipe", command=lambda: launcher.guard(use)).pack(side="left", padx=8)
    status = tk.StringVar(value="Recipes contain no saves or game assets. Multiworld placement comes from the Archipelago host.")
    ttk.Label(pane, textvariable=status, wraplength=590).pack(anchor="w", pady=16)
    def launch(multiworld):
        key, value = selected(), seed.get()
        adventure.recipe(key, value)
        def work():
            directory = companions.prepare("ootrr")
            command, env = companions.launch_plan("ootrr", directory, game=game)
            env = adventure.launch_environment(env, key, value, multiworld=multiworld)
            return subprocess.Popen(command, cwd=directory, env=env)
        launcher.task("Opening randomized adventure…", work,
                      lambda _: launcher.status.set("Opened isolated OoTrR. Review the selected recipe before generating."))
    row = ttk.Frame(pane)
    row.pack(fill="x")
    ttk.Button(row, text="Review solo adventure", command=lambda: launcher.guard(lambda: launch(False))).pack(side="left")
    ttk.Button(row, text="Set up multiworld", command=lambda: launcher.guard(lambda: launch(True))).pack(side="right")

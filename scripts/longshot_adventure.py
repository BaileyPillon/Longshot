"""Portable randomizer recipes: a reviewed preset, seed and generator identity."""
import base64
import hashlib
import json
import re

from longshot_companions import entry

PIN = entry("ootrr")["commit"]
PRESETS = {"prudent": "First shuffled adventure", "ap_defaults": "Glitchless adventure", "everything": "Everything shuffled"}
# Versioned, spoiler-free starting points shared by players using this generator.
FEATURED = {
    "Kokiri Trial": ("prudent", "Kokiri-Trial-01"),
    "Hyrule Relay": ("ap_defaults", "Hyrule-Relay-01"),
    "Lost Measure": ("everything", "Lost-Measure-01"),
}


def recipe(preset, seed):
    if preset not in PRESETS:
        raise ValueError("Choose a reviewed randomizer preset")
    if not isinstance(seed, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", seed):
        raise ValueError("Seed must use 1 to 64 letters, numbers, underscores or hyphens")
    return {"schema": 1, "generator": PIN, "preset": preset, "seed": seed}


def share_code(preset, seed):
    raw = json.dumps(recipe(preset, seed), sort_keys=True, separators=(",", ":")).encode()
    payload = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return "LS1." + payload + "." + hashlib.sha256(raw).hexdigest()[:12]


def from_code(code):
    if not isinstance(code, str) or len(code) > 1024:
        raise ValueError("Invalid adventure code")
    try:
        prefix, encoded, digest = code.strip().split(".")
        if prefix != "LS1" or not re.fullmatch(r"[A-Za-z0-9_-]+", encoded):
            raise ValueError()
        raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        data = json.loads(raw)
        if digest != hashlib.sha256(raw).hexdigest()[:12] or data.get("schema") != 1 or data.get("generator") != PIN:
            raise ValueError()
        validated = recipe(data.get("preset"), data.get("seed"))
        if data != validated:
            raise ValueError()
        return validated
    except (ValueError, TypeError, AttributeError, UnicodeError) as error:
        raise ValueError("Adventure code is damaged or uses a different generator version") from error


def launch_environment(env, preset, seed, *, multiworld=False):
    value = recipe(preset, seed)
    result = dict(env)
    if not result.get("LONGSHOT_OOTRR_GAME"):
        raise ValueError("Adventure recipes require the isolated full-randomizer installation")
    result["LONGSHOT_ADVENTURE_PRESET"] = value["preset"]
    result["LONGSHOT_ADVENTURE_SEED"] = value["seed"]
    result["LONGSHOT_ADVENTURE_PAGE"] = "multiworld" if multiworld else "settings"
    return result

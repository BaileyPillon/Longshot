"""Shareable recipes pin their generator and never launch into ordinary play."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import longshot_adventure as adventure


class Recipes(unittest.TestCase):
    def test_featured_challenges_round_trip(self):
        for label, (preset, seed) in adventure.FEATURED.items():
            with self.subTest(label=label):
                self.assertEqual(adventure.from_code(adventure.share_code(preset, seed)), adventure.recipe(preset, seed))

    def test_roundtrip_all_reviewed_presets(self):
        for preset in adventure.PRESETS:
            code = adventure.share_code(preset, "Longshot-2026")
            self.assertEqual(adventure.from_code(code), adventure.recipe(preset, "Longshot-2026"))
            with self.assertRaises(ValueError):
                adventure.from_code(code[:-1] + ("0" if code[-1] != "0" else "1"))

    def test_invalid_recipes_and_isolation(self):
        for seed in ("", "a\nb", "x" * 65, "../../save", None):
            with self.assertRaises(ValueError):
                adventure.recipe("prudent", seed)
        with self.assertRaises(ValueError):
            adventure.launch_environment({}, "prudent", "test")
        env = {"LONGSHOT_OOTRR_GAME": "private-mode", "HOS_COOP": "0"}
        result = adventure.launch_environment(env, "prudent", "test", multiworld=True)
        self.assertEqual(result["LONGSHOT_ADVENTURE_PAGE"], "multiworld")
        self.assertNotIn("LONGSHOT_ADVENTURE_PAGE", env)


if __name__ == "__main__":
    unittest.main()

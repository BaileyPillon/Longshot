"""Confirm imported layers remain inactive until enabled through the existing manager."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import longshot_mod_import as importer
import longshot_mods as mods


class ModImport(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "mods"
        self.root.mkdir()
        self.source = self.root.parent / "Example textures"
        asset = self.source / "romfs/texture/example.bin"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b"local asset")
        running = patch.object(importer.core.oot_saves, "running_games", return_value=[])
        running.start()
        self.addCleanup(running.stop)

    def test_install_review_enable_and_duplicate_refusal(self):
        name, count = importer.install_folder(self.root, self.source)
        self.assertEqual(count, 1)
        self.assertFalse(mods.scan(self.root)[0]["enabled"])
        self.assertEqual((self.root / name / "romfs/texture/example.bin").read_bytes(), b"local asset")
        mods.set_enabled(self.root, name, True)
        with self.assertRaises(FileExistsError):
            importer.install_folder(self.root, self.source)
        self.assertTrue(mods.scan(self.root)[0]["enabled"])

    def test_incompatible_and_exefs_folders_leave_no_layer(self):
        (self.source / "longshot-mod.json").write_text(json.dumps({"title_id": "another game"}))
        with self.assertRaisesRegex(ValueError, "different game"):
            importer.install_folder(self.root, self.source)
        self.assertEqual(mods.scan(self.root), [])
        (self.source / "exefs").mkdir()
        with self.assertRaisesRegex(ValueError, "ExeFS"):
            importer.install_folder(self.root, self.source)
        self.assertEqual(mods.scan(self.root), [])


if __name__ == "__main__":
    unittest.main()

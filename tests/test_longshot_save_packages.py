"""Exercise the actual save publication path with disposable native saves."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import longshot_launcher_core as core
import longshot_save_packages as packages


class SavePackages(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.game = Path(folder.name)
        self.archive = self.game / "test.zip"
        self.account = "b" * 32
        self.data = {"account.sav": b"account", "option.sav": b"option",
                     "slot_00/caption.sav": b"caption", "slot_00/progress.sav": b"progress"}
        self.source = core.profile_folder(self.game, 1) / "save" / self.account
        for path, payload in self.data.items():
            target = self.source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        running = patch.object(core.oot_saves, "running_games", return_value=[])
        self.running = running.start()
        self.addCleanup(running.stop)

    def write_nx2navi(self, *, extra=None, **overrides):
        manifest = dict(format="nx2navi-save", format_version=1, title_id=packages.TITLE,
                        game_version="1.1.1", files=len(self.data))
        manifest.update(overrides)
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            for path, content in self.data.items():
                archive.writestr("save/" + path, content)
            if extra:
                archive.writestr(extra, b"metadata")

    def test_export_round_trip_and_refuse_replacement(self):
        packages.export_package(self.game, 1, self.account, self.archive)
        with self.assertRaises(FileExistsError):
            packages.export_package(self.game, 1, self.account, self.archive)
        moved = packages.import_package(self.archive, self.game, 2)
        self.assertEqual(moved["slots"], ["slot_00"])
        target = core.profile_folder(self.game, 2) / "save" / self.account
        for path, content in self.data.items():
            self.assertEqual((target / path).read_bytes(), content)
        with self.assertRaises(ValueError):
            packages.import_package(self.archive, self.game, 2)

    def test_nx2navi_import_ignores_attachments(self):
        self.write_nx2navi(extra="bug-report/nx2navi.ini")
        result = packages.import_package(self.archive, self.game, 3)
        self.assertEqual(result["account"], core.DEFAULT_ACCOUNT)
        self.assertEqual(result["files"], len(self.data))
        self.assertFalse(list(core.profile_folder(self.game, 3).rglob("*.ini")))

    def test_bad_archives_do_not_create_profiles(self):
        for kwargs in ({"extra": "save/../account.sav"}, {"extra": "save/ACCOUNT.SAV"},
                       {"sha256": {}}, {"game_version": "1.0.0"}):
            with self.subTest(kwargs=kwargs):
                self.write_nx2navi(**kwargs)
                with self.assertRaises(ValueError):
                    packages.import_package(self.archive, self.game, 2)
                self.assertFalse(core.profile_folder(self.game, 2).exists())
        self.data.pop("slot_00/caption.sav")
        self.write_nx2navi()
        with self.assertRaises(ValueError):
            packages.import_package(self.archive, self.game, 2)
        self.assertFalse(core.profile_folder(self.game, 2).exists())

    def test_export_refuses_if_game_starts_before_publication(self):
        self.running.side_effect = [[], ["Longshot"]]
        with self.assertRaisesRegex(ValueError, "close the game"):
            packages.export_package(self.game, 1, self.account, self.archive)
        self.assertFalse(self.archive.exists())
        self.assertFalse(list(self.game.glob(".longshot-export-*")))


if __name__ == "__main__":
    unittest.main()

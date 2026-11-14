"""Asset-free loadout transaction, stale preview, rollback and crash recovery checks."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import longshot_loadouts as loadouts
import longshot_mods as mods


class Loadouts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ("A", "B", "_disabled"):
            path = self.root / name / "romfs" / "overlap.txt"
            path.parent.mkdir(parents=True)
            path.write_text(name)
        self.closed = patch.object(loadouts.core, "closed_games")
        self.closed.start()
        self.addCleanup(self.closed.stop)
        self.addCleanup(self.tmp.cleanup)

    def save_and_change(self):
        loadouts.capture(self.root, "Adventure")
        mods.set_enabled(self.root, "A", False)
        mods.set_order(self.root, ["B", "A"])
        return loadouts.preview(self.root, "Adventure")

    def test_preview_apply_undo_preserves_exact_control_bytes(self):
        plan = self.save_and_change()
        (self.root / "A" / mods.MARKER).write_bytes(b"\xff original\r\n")
        before = loadouts.file_state(self.root)
        self.assertEqual(plan["conflicts"][0]["winner"], "B")
        loadouts.apply(self.root, "Adventure", plan["token"])
        self.assertTrue(mods.scan(self.root)[1]["enabled"])
        loadouts.recover(self.root, undo=True)
        self.assertEqual(loadouts.file_state(self.root), before)
        self.assertEqual((self.root / "A/romfs/overlap.txt").read_text(), "A")

    def test_stale_preview_and_changed_install_rejected(self):
        plan = self.save_and_change()
        mods.set_enabled(self.root, "B", False)
        before = loadouts.file_state(self.root)
        with self.assertRaisesRegex(ValueError, "changed after preview"):
            loadouts.apply(self.root, "Adventure", plan["token"])
        self.assertEqual(loadouts.file_state(self.root), before)
        (self.root / "A/romfs/new.txt").write_text("new")
        with self.assertRaisesRegex(ValueError, "Files changed"):
            loadouts.preview(self.root, "Adventure")

    def test_mods_added_after_capture_are_disabled_and_undoable(self):
        self.save_and_change()
        new_layer = self.root / "Later" / "romfs"
        new_layer.mkdir(parents=True)
        (new_layer / "overlap.txt").write_text("new mod")
        plan = loadouts.preview(self.root, "Adventure")
        self.assertEqual(plan["new_mods"], ["Later"])
        self.assertEqual(plan["conflicts"][0]["winner"], "B")
        loadouts.apply(self.root, "Adventure", plan["token"])
        self.assertTrue((new_layer.parent / mods.MARKER).exists())
        loadouts.recover(self.root, undo=True)
        self.assertFalse((new_layer.parent / mods.MARKER).exists())

    def test_failure_rolls_back_and_crash_journal_recovers(self):
        plan = self.save_and_change()
        before = loadouts.file_state(self.root)
        original = loadouts.write_json
        def fail_undo(path, value):
            if path.name == loadouts.UNDO:
                raise OSError("disk full")
            original(path, value)
        with patch.object(loadouts, "write_json", fail_undo), self.assertRaises(OSError):
            loadouts.apply(self.root, "Adventure", plan["token"])
        self.assertEqual(loadouts.file_state(self.root), before)
        loadouts.write_json(self.root / loadouts.PENDING, {"schema": 1, "before": before})
        mods.set_enabled(self.root, "B", False)
        with self.assertRaisesRegex(ValueError, "Recover"):
            loadouts.apply(self.root, "Adventure", plan["token"])
        loadouts.recover(self.root)
        self.assertEqual(loadouts.file_state(self.root), before)

    def test_running_game_and_incompatible_pack_refused(self):
        with patch.object(loadouts.core, "closed_games", side_effect=ValueError("game running")), self.assertRaises(ValueError):
            loadouts.capture(self.root, "Unsafe")
        loadouts.capture(self.root, "Adventure")
        (self.root / "B/longshot-mod.json").write_text('{"build_id":"wrong"}')
        with self.assertRaisesRegex(ValueError, "compatibility"):
            loadouts.preview(self.root, "Adventure")

    def test_undo_refuses_later_edits_and_duplicate_name(self):
        plan = self.save_and_change()
        loadouts.apply(self.root, "Adventure", plan["token"])
        mods.set_enabled(self.root, "B", False)
        with self.assertRaisesRegex(ValueError, "changed since"):
            loadouts.recover(self.root, undo=True)
        with self.assertRaisesRegex(ValueError, "already exists"):
            loadouts.capture(self.root, "Adventure")

    def test_malicious_recovery_path_and_lock_are_rejected(self):
        loadouts.write_json(self.root / loadouts.PENDING, {"schema": 1, "before": {"../outside": "61"}})
        with self.assertRaises(ValueError):
            loadouts.recover(self.root)
        self.assertFalse((self.root.parent / "outside").exists())
        with loadouts.locked(self.root), self.assertRaises(ValueError):
            with loadouts.locked(self.root):
                self.fail("second writer acquired the lock")


if __name__ == "__main__":
    unittest.main()

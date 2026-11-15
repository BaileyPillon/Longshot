"""Checkpoint requests cannot overwrite profiles or survive a game restart."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import longshot_player_tools as tools


class PlayerTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_bounded_protocol(self):
        path = self.root / "request.txt"
        path.write_text("LSP1\ncapture\n123\n")
        self.assertEqual(tools.read_request(path), ("capture", None, 123))
        path.write_text("LSP1\nrestore 0123456789abcdef\n123\n")
        self.assertEqual(tools.read_request(path), ("restore", "0123456789abcdef", 123))
        for text in ("LSP1\nrestore ../../user\n123\n", "LSP1\ncapture\n", "x" * 257,
                     "LSP1\nshortcut 3\n123\n", "LSP1\ncapture\nNaN\n"):
            path.write_text(text)
            with self.assertRaises(ValueError):
                tools.read_request(path)

    def test_profile_selection_never_replaces_existing_even_empty(self):
        for n in (2, 3, 4):
            tools.core.profile_folder(self.root, n).mkdir(parents=True)
        self.assertEqual(tools.unused_profile(self.root), 5)
        for n in range(5, 10):
            tools.core.profile_folder(self.root, n).mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "occupied"):
            tools.unused_profile(self.root)

    def test_no_save_does_not_quit_game(self):
        session = tools.Session.__new__(tools.Session)
        session.game, session.number = self.root, 1
        session.quit_owned = Mock()
        with self.assertRaises(ValueError):
            session.perform("capture", None)
        session.quit_owned.assert_not_called()

    def test_failed_capture_relaunches_original_profile(self):
        session = tools.Session.__new__(tools.Session)
        session.game, session.number, session.exefs = self.root, 4, None
        session.quit_owned, session.publish, session.launch = Mock(), Mock(), Mock()
        with patch.object(tools, "latest_slot", return_value=("a" * 32, "slot_03")), \
             patch.object(tools.core.checkpoints, "capture", side_effect=OSError("disk full")), \
             self.assertRaises(OSError):
            session.perform("capture", None)
        session.quit_owned.assert_called_once()
        session.launch.assert_called_once()
        self.assertEqual(session.number, 4)

    def test_saves_newest_complete_slot_and_closes_only_owned_child(self):
        folder = self.root / "save" / ("a" * 32)
        folder.mkdir(parents=True)
        (folder / "account.sav").write_bytes(b"account")
        for n in (0, 3):
            slot = folder / f"slot_{n:02}"
            slot.mkdir()
            (slot / "caption.sav").write_bytes(b"caption")
            (slot / "progress.sav").write_bytes(b"progress")
        import os
        os.utime(folder / "slot_00/progress.sav", ns=(1, 1))
        self.assertEqual(tools.latest_slot(self.root), ("a" * 32, "slot_03"))
        session = tools.Session.__new__(tools.Session)
        session.current, session.endpoint = Mock(), "unique-child-endpoint"
        session.current.poll.return_value = None
        connection = Mock()
        connection.request.return_value = {"ok": True}
        with patch.object(tools, "Bridge", return_value=connection) as bridge, patch.object(tools.core, "closed_games"):
            session.quit_owned()
        bridge.assert_called_once_with("unique-child-endpoint")
        session.current.terminate.assert_not_called()
        session.current.wait.assert_called_once_with(timeout=45)


if __name__ == "__main__":
    unittest.main()

"""Co-op host secrecy, child ownership and isolated tunic assets."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import longshot_party as party


class Party(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.exe = self.root / "coop_server.exe"
        self.exe.touch()
        self.addCleanup(self.tmp.cleanup)

    def test_server_scope_secret_and_arguments(self):
        command, env = party.server_plan(self.exe, "127.0.0.1", 27510, "secret value")
        self.assertNotIn("secret value", command)
        self.assertEqual(env["LONGSHOT_PARTY_SECRET"], "secret value")
        self.assertNotIn("--upnp", command)
        self.assertNotIn("--invite", command)
        self.assertNotIn("--allow", command)
        command, _ = party.server_plan(self.exe, "0.0.0.0", 27510, "secret", pvp=True)
        self.assertIn("--allow", command)
        self.assertEqual(command[command.index("--pvp") + 1], "on")
        for port in (0, 65536, True):
            with self.assertRaises(ValueError):
                party.server_plan(self.exe, "127.0.0.1", port, "secret")

    def test_party_address_round_trip(self):
        address = party.invite_endpoint("192.168.1.10", 27510)
        self.assertEqual(party.read_invite(address), ("192.168.1.10", 27510))
        for invalid in ("https://host:27510", "host:65536", "host:27510 secret", "host:0", "host"):
            with self.assertRaises(ValueError):
                party.read_invite(invalid)

    def test_tunic_is_private_overlay_not_pack_rewrite(self):
        pack = self.root / "mods/contents/0400486024DEC000/coop-puppet"
        (pack / "coop_self").mkdir(parents=True)
        source = pack / "coop_self/blue.bntx.zs"
        source.write_bytes(b"synthetic texture")
        meta = {"tunics": {"green": ["synthetic"]}, "self_files": {
            "blue": {"Tex/Angin_Tile_A_Alb.bntx.zs": "coop_self/blue.bntx.zs"}}}
        (pack / "coop_puppet.json").write_text(json.dumps(meta))
        overlay = party.tunic_overlay(self.root, "blue")
        self.assertEqual((overlay / "Tex/Angin_Tile_A_Alb.bntx.zs").read_bytes(), b"synthetic texture")
        self.assertFalse((pack / "romfs").exists())
        self.assertIsNone(party.tunic_overlay(self.root, "green"))
        self.assertNotEqual(overlay, party.tunic_overlay(self.root, "blue"))
        meta["self_files"]["blue"]["Tex/Angin_Tile_A_Alb.bntx.zs"] = "../../outside"
        (pack / "coop_puppet.json").write_text(json.dumps(meta))
        with self.assertRaises(ValueError):
            party.tunic_overlay(self.root, "blue")

    def test_child_has_only_selected_color_overlay(self):
        with patch.object(party.core, "closed_games"), \
             patch.object(party.core, "coop_launch_plan", return_value=(["game"], {"HOS_COOP": "1"})), \
             patch.object(party, "tunic_overlay", return_value=self.root / "private-overlay"), \
             patch.object(party.subprocess, "Popen") as start:
            party.start_game(self.root, 2, "localhost", 27510, "Link", "secret", "blue")
        env = start.call_args.kwargs["env"]
        self.assertEqual(env["LICHII_COOP_COLOR"], "blue")
        self.assertEqual(env["LICHII_COOP_SELF_TUNIC"], "blue")
        self.assertEqual(Path(env["HOS_FS_OVERLAY"]), self.root / "private-overlay")


if __name__ == "__main__":
    unittest.main()

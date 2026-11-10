from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest import mock

import fixture_ship_short


class ShortShipFixtureTests(unittest.TestCase):
    def test_short_bridge_fixture_uses_real_canal_bridge_and_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            (build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")).touch()
            output = root / "review"
            argv = ["fixture_ship_short.py", "--build-dir", str(build), "--output", str(output),
                    "--engine", "204", "--canal-width", "2", "--bridge-type", "1", "--bridge-hold"]
            with mock.patch.object(sys, "argv", argv), mock.patch("fixture_ship_short.subprocess.Popen", side_effect=RuntimeError("stop before launch")):
                with self.assertRaisesRegex(RuntimeError, "stop before launch"):
                    fixture_ship_short.main()
            commands = (output / "scripts/game_start.scr").read_text()
            self.assertIn("canal_width=2", commands)
            self.assertIn("bridge_type=1", commands)
            self.assertIn("bridge_hold=1", commands)
            source = (output / "ai/ship-short/main.nut").read_text()
            self.assertIn("AIBridge.BuildBridge(AIVehicle.VT_ROAD,bridge_type", source)
            self.assertIn("AIMarine.BuildCanal", source)
            self.assertIn("SHIP_SHORT_HELD", source)
            self.assertNotIn("renderer3d", commands)


if __name__ == "__main__":
    unittest.main()

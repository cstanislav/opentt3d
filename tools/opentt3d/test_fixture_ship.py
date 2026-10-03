from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest import mock

import fixture_ship


class ShipFixtureScriptTests(unittest.TestCase):
    def test_concave_dike_fixture_is_opt_in_and_uses_original_marine_commands(self):
        for island in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                build = root/"build"
                build.mkdir()
                (build/("opentt3d.exe" if os.name == "nt" else "opentt3d")).touch()
                output = root/"review"
                argv = ["fixture_ship.py","--build-dir",str(build),"--output",str(output)]
                if island:
                    argv.append("--dike-island")
                with mock.patch.object(sys,"argv",argv),mock.patch("fixture_ship.subprocess.Popen",side_effect=RuntimeError("stop before launch")):
                    with self.assertRaisesRegex(RuntimeError,"stop before launch"):
                        fixture_ship.main()
                commands = (output/"scripts/game_start.scr").read_text()
                self.assertIn(f"dike_island={int(island)}",commands)
                source = (output/"ai/ship-catalogue/main.nut").read_text()
                self.assertIn("if (tile==dike_island) continue;",source)
                self.assertIn("AIMarine.BuildCanal(tile)",source)
                self.assertIn("original dry canal island remains land",source)
                self.assertNotIn("renderer3d",commands)


if __name__ == "__main__":
    unittest.main()

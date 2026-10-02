"""Original-setting and read-only breakdown-observation fixture controls."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import fixture_train


class TrainBreakdownFixtureTests(unittest.TestCase):
    def generated(self, *flags):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            (build / ("opentt3d.exe" if sys.platform == "win32" else "opentt3d")).touch()
            output = root / "fixture"
            argv = ["fixture_train.py", "--build-dir", str(build), "--output", str(output), *flags]
            with mock.patch.object(sys, "argv", argv), mock.patch("fixture_train.subprocess.Popen", side_effect=RuntimeError("stop before launch")) as launch:
                with self.assertRaisesRegex(RuntimeError, "stop before launch"):
                    fixture_train.main()
                launch.assert_called_once()
            return (output / "openttd.cfg").read_text(), (output / "scripts/game_start.scr").read_text()

    def test_existing_fixtures_keep_breakdowns_disabled(self):
        config, script = self.generated()
        self.assertIn("vehicle_breakdowns = 0\n", config)
        self.assertIn("review_wait_breakdown=0", script)

    def test_waiting_uses_original_normal_setting_and_observation_only(self):
        config, script = self.generated("--vehicle-breakdowns", "2", "--wait-breakdown", "--low-effect-id")
        self.assertIn("vehicle_breakdowns = 2\n", config)
        self.assertIn("review_wait_breakdown=1", script)
        self.assertIn("review_low_effect_id=1", script)
        source = (Path(fixture_train.__file__).with_name("fixtures") / "train/main.nut").read_text()
        self.assertIn("AIVehicle.GetState(train) == AIVehicle.VS_BROKEN && breakdown_observed_speed > 0", source)
        self.assertIn('AIGameSettings.GetValue("difficulty.vehicle_breakdowns")', source)
        self.assertNotIn("SetReliability", source)
        self.assertNotIn("CreateEffect", source)

    def test_incompatible_wait_controls_fail_before_launch(self):
        for flags in (("--wait-breakdown",),
                      ("--wait-breakdown", "--vehicle-breakdowns", "2", "--hold"),
                      ("--wait-breakdown", "--vehicle-breakdowns", "2", "--departing"),
                      ("--wait-breakdown", "--vehicle-breakdowns", "2", "--cargo-source", "0", "--cargo-destination", "1", "--first-engine", "27", "--last-engine", "27")):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                build = root / "build"
                build.mkdir()
                (build / ("opentt3d.exe" if sys.platform == "win32" else "opentt3d")).touch()
                output, stderr = root / "unused", io.StringIO()
                with mock.patch.object(sys, "argv", ["fixture_train.py", "--build-dir", str(build), "--output", str(output), *flags]), mock.patch("fixture_train.subprocess.Popen") as launch, contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as error:
                        fixture_train.main()
                    self.assertEqual(error.exception.code, 2)
                    self.assertIn("--wait-breakdown requires", stderr.getvalue())
                    launch.assert_not_called()
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

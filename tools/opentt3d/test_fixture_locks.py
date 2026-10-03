"""Lock fixtures must preserve public commands, source slopes and actual saved states."""
import copy
from pathlib import Path
import tempfile
import unittest

from fixture_locks import validate_manifest, verify_save

ROOT = Path(__file__).resolve().parents[2]


class OriginalLockFixtureTests(unittest.TestCase):
    def manifest(self):
        width = 128
        locks = []
        for elevation in range(2):
            for direction in range(4):
                x, y = 10+direction*8, 10+elevation*8
                tile = x+y*width
                delta = (-1,width,1,-width)[direction]
                locks.append(dict(tile=tile, x=x, y=y, direction=direction, elevation=elevation, height=elevation,
                                  lower=tile-delta, upper=tile+delta, connected_both_ways=True))
        return {"company": 0, "map_width": width, "map_height": 128, "locks": locks}

    def test_all_eight_natural_connected_locks_remain_exact_without_mutation(self):
        row = self.manifest()
        original = copy.deepcopy(row)
        self.assertIs(validate_manifest(row), row)
        self.assertEqual(row, original)

    def test_missing_directions_duplicate_or_wrong_registration_are_rejected(self):
        row = self.manifest()
        missing, duplicate, wrong = copy.deepcopy(row), copy.deepcopy(row), copy.deepcopy(row)
        missing["locks"].pop()
        duplicate["locks"][-1] = duplicate["locks"][0]
        wrong["locks"][0]["upper"] += 1
        for changed in (missing, duplicate, wrong):
            with self.assertRaises(ValueError):
                validate_manifest(changed)

    def test_bool_fractional_unconnected_and_false_elevations_are_not_coerced(self):
        for key,value in (("direction",True), ("height",1.0), ("height",-1), ("connected_both_ways",1), ("elevation",1)):
            row = self.manifest()
            row["locks"][0][key] = value
            with self.assertRaises(ValueError):
                validate_manifest(row)

    def test_only_complete_original_save_headers_are_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lock.sav"
            for data in (b"", b"OTTZ", b"fake"+b"x"*200):
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    verify_save(path)
            path.write_bytes(b"OTTZ"+b"x"*200)
            self.assertEqual(len(verify_save(path)),64)

    def test_public_lock_commands_do_not_terraform_force_state_or_invent_api(self):
        script = (ROOT / "tools/opentt3d/fixtures/locks/main.nut").read_text()
        for required in ("AITestMode()", "AIMarine.BuildLock(tile)", "AITile.GetSlope", "AITile.GetMinHeight",
                         "AIMarine.AreWaterTilesConnected", "AICompany.SetLoanAmount", "LOCK_FIXTURE_READY", "LOCK_FIXTURE_FAILED"):
            self.assertIn(required, script)
        for forbidden in ("RaiseTile", "LowerTile", "LevelTiles", "SetTile", "SetAnimationFrame", "SetCompanyRating", "Random(", "BuildRiver"):
            self.assertNotIn(forbidden, script)
        runtime = (ROOT / "tools/opentt3d/fixture_locks.py").read_text()
        for required in ("threaded_saves = false", "Map successfully saved", 'send("pause"', 'send("save lock-fixture"',
                         "save failed-fixture", "new output directory", 'OPENTT3D_BACKGROUND="1"', '"127.0.0.1"'):
            self.assertIn(required, runtime)


if __name__ == "__main__":
    unittest.main()

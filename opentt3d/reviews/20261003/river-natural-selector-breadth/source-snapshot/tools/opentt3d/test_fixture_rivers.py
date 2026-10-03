"""Read-only river surveys never prove undrawn bank absence or full family acceptance."""
import copy
from pathlib import Path
import unittest

from fixture_rivers import validate_survey


class RiverSurveyTests(unittest.TestCase):
    def survey(self):
        row = dict(map_width=128, map_height=128, river_tiles=2, read_only_tile_queries=True)
        tiles = [dict(tile=4002, x=34, y=31, slope=3, min_height_levels=0),
                 dict(tile=4003, x=35, y=31, slope=0, min_height_levels=1)]
        return row, tiles

    def test_observed_tiles_keep_original_level_units_without_promoting_missing_states(self):
        row, tiles = self.survey()
        result = validate_survey(row, tiles)
        self.assertEqual(result["observed_slopes"], [0, 3])
        self.assertEqual(result["observed_min_height_levels"], [0, 1])
        self.assertEqual(result["tiles"], tiles)
        self.assertFalse(result["complete_river_family_verified"])
        self.assertFalse(result["geometry_or_quality_approved"])

    def test_empty_survey_does_not_infer_absence(self):
        row, _ = self.survey()
        row["river_tiles"] = 0
        result = validate_survey(row, [])
        self.assertEqual(result["observed_slopes"], [])
        self.assertFalse(result["complete_river_family_verified"])
        self.assertFalse(result["geometry_or_quality_approved"])

    def test_bad_metadata_coercions_and_duplicate_registration_fail(self):
        row, tiles = self.survey()
        for key, value in (("map_width", True), ("map_height", 128.0), ("river_tiles", 3), ("read_only_tile_queries", 1)):
            changed = dict(row, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_survey(changed, tiles)
        for key, value in (("tile", 4002.0), ("x", 33), ("y", -1), ("slope", True), ("slope", 1),
                           ("min_height_levels", 1.0), ("min_height_levels", -1)):
            changed = copy.deepcopy(tiles)
            changed[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_survey(row, changed)
        with self.assertRaises(ValueError):
            validate_survey(row, [tiles[0], tiles[0]])

    def test_squirrel_observes_public_queries_only(self):
        source = (Path(__file__).with_name("fixtures") / "rivers/main.nut").read_text()
        self.assertIn("AITile.IsRiverTile(tile)", source)
        self.assertIn("AITile.GetSlope(tile)", source)
        self.assertIn("AITile.GetMinHeight(tile)", source)
        self.assertNotRegex(source, r"\b(?:Build\w*|DemolishTile|RaiseTile|LowerTile|LevelTiles|SetLoanAmount|SetName|Random|Rand)\s*\(")

    def test_failed_script_can_still_acknowledge_an_original_saved_world(self):
        source = Path(__file__).with_name("fixture_rivers.py").read_text()
        self.assertIn('not allow_failed and "script died unexpectedly" in text', source)
        self.assertIn('threaded_saves = false', source)
        self.assertIn('Map successfully saved', source)
        self.assertIn('timeout=10, allow_failed=True', source)
        self.assertIn('timeout=20, allow_failed=True', source)
        self.assertIn('verify_save(output / "save/failed-river-survey.sav")', source)


if __name__ == "__main__":
    unittest.main()

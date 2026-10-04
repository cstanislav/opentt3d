"""Read-only river surveys never prove undrawn bank absence or full family acceptance."""
import copy
from pathlib import Path
import unittest

from fixture_rivers import survey_tiles, validate_survey


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
        self.assertFalse(result["public_terrain_type_queries"])
        self.assertEqual(result["observed_public_terrain_types"], [])

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
        self.assertIn("AITile.GetTerrainType(tile)", source)
        self.assertNotRegex(source, r"\b(?:Build\w*|DemolishTile|RaiseTile|LowerTile|LevelTiles|SetLoanAmount|SetName|Random|Rand)\s*\(")

    def test_public_terrain_types_remain_distinct_from_raw_newgrf_snow_codes(self):
        row, tiles = self.survey()
        row["public_terrain_type_queries"] = True
        tiles[0]["public_terrain_type"], tiles[1]["public_terrain_type"] = 1, 3
        result = validate_survey(row, tiles)
        self.assertEqual(result["observed_public_terrain_types"], [1, 3])
        self.assertIn("snow=4", result["terrain_type_code_domain"])
        self.assertFalse(result["complete_terrain_type_or_snowline_coverage_verified"])
        self.assertFalse(result["geometry_or_quality_approved"])

    def test_missing_invalid_or_unacknowledged_terrain_queries_fail(self):
        row, tiles = self.survey()
        row["public_terrain_type_queries"] = True
        for value in (None, True, 1.0, -1, 4):
            changed = copy.deepcopy(tiles)
            changed[0]["public_terrain_type"], changed[1]["public_terrain_type"] = value, 0
            with self.subTest(value=value), self.assertRaises(ValueError): validate_survey(row, changed)
        with self.assertRaises(ValueError): validate_survey(row, tiles)
        row["public_terrain_type_queries"] = 1
        with self.assertRaises(ValueError): validate_survey(row, tiles)
        row["public_terrain_type_queries"] = False
        tiles[0]["public_terrain_type"] = 0
        with self.assertRaises(ValueError): validate_survey(row, tiles)

    def test_reloaded_survey_uses_the_original_save_and_verifies_its_header(self):
        source = Path(__file__).with_name("fixture_rivers.py").read_text()
        self.assertIn("input_save_sha256 = verify_save(input_save)", source)
        self.assertIn('["-g", str(input_save)] if input_save is not None', source)
        self.assertIn("loaded_original_world_not_regenerated=True", source)

    def test_interleaved_loaded_ai_output_cannot_acknowledge_the_new_public_command(self):
        text = '\n'.join((
            'RIVER_SURVEY_TILE {"tile":99,"survey_token":0}',
            'RIVER_SURVEY_TILE {"tile":4002,"survey_token":17}',
            'RIVER_SURVEY_TILE {"tile":88,"survey_token":18}',
            'RIVER_SURVEY_TILE {"tile":4003,"survey_token":17}',
            'RIVER_SURVEY_TILE {"tile":77,"survey_token":true}'))
        self.assertEqual(survey_tiles(text,17),[{"tile":4002,"survey_token":17},{"tile":4003,"survey_token":17}])
        for token in (None,True,0,-1,17.0,0x80000000):
            with self.subTest(token=token),self.assertRaises(ValueError): survey_tiles(text,token)
        row,tiles = self.survey();row["survey_token"] = 17
        tiles[0]["survey_token"],tiles[1]["survey_token"] = 17,18
        with self.assertRaises(ValueError): validate_survey(row,tiles)
        tiles[1]["survey_token"] = 17
        self.assertEqual(validate_survey(row,tiles)["survey_token"],17)

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

"""Original water ownership/selection gates; source inventories never approve geometry."""
import copy
import unittest

from original_water import ROOT, catalogue, constant_reader, default_lock_selection, layers, runtime_selection, validate_default_export


class OriginalWaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = catalogue()
        cls.table = (ROOT / "src/table/water_land.h").read_text()
        cls.constants = (ROOT / "src/table/sprites.h").read_text() + "\n" + (ROOT / "src/tile_type.h").read_text()
        cls.drawing = (ROOT / "src/water_cmd.cpp").read_text()
        cls.enums = (ROOT / "src/water_map.h").read_text()
        cls.directions = (ROOT / "src/direction_type.h").read_text()
        cls.flags = (ROOT / "src/newgrf_canal.h").read_text()

    def selection(self, part, direction, z):
        return default_lock_selection(part, direction, z, self.inventory)

    def exported(self):
        rows = []
        for row in self.inventory["locks"]:
            for owner in row["body"]:
                for elevation, sprite in enumerate(owner["default_sprite_variants"]):
                    offset = owner["sprite_offset"]
                    rows.append({"category": "canal-lock", "style": elevation, "variant": offset, "sprite": sprite,
                                 "image": f"canal-lock-{elevation}-{offset}.pam", "offset": [-128, -40], "size": [256, 80]})
        rows.extend({"category": "water-slope", "style": 0, "variant": row["slot"], "sprite": row["sprite"],
                     "image": f"water-slope-0-{row['slot']}.pam", "offset": [-128, 0], "size": [256, 128]}
                    for row in self.inventory["default_water_slopes"])
        return rows

    def test_complete_three_part_four_direction_two_face_two_elevation_sources(self):
        self.assertEqual(len(self.inventory["locks"]), 12)
        sprites = {sprite for row in self.inventory["locks"] for owner in row["body"] for sprite in owner["default_sprite_variants"]}
        self.assertEqual(sprites, set(range(5332, 5380)))
        for row in self.inventory["locks"]:
            self.assertEqual([owner["face"] for owner in row["body"]], ["rear", "front"])
            self.assertEqual(row["footprint_tiles"], [1, 1])
            self.assertEqual([owner["origin"][2] for owner in row["body"]], [0, 0])

    def test_sorting_extents_and_source_origins_are_metadata_not_artwork_dimensions(self):
        for row in self.inventory["locks"]:
            rear, front = row["body"]
            axis_x = row["direction_name"] in ("NE", "SW")
            self.assertEqual(rear["origin"], [0, 0, 0])
            self.assertEqual(front["origin"], [0, 15, 0] if axis_x else [15, 0, 0])
            self.assertEqual(rear["sort_extent"][:2], [16, 1] if axis_x else [1, 16])
            self.assertEqual(rear["sort_extent"][2], 6)
            self.assertEqual(front["sort_extent"][2], 6 if row["part_name"] == "upper" else 10)
            self.assertNotIn("model_size", rear)

    def test_middle_water_slopes_and_independent_flat_endpoint_water(self):
        self.assertEqual([self.selection(0, d, 0)["ground"]["default_sprite"] for d in range(4)], [5329, 5328, 5330, 5331])
        for part in (1, 2):
            for direction in range(4):
                ground = self.selection(part, direction, 0)["ground"]
                self.assertEqual(ground["default_sprite"], 4061)
                self.assertTrue(ground["is_flat_water"])

    def test_sea_level_and_elevated_lock_predicates_use_original_source_height(self):
        for direction in range(4):
            for part in (0, 1):
                self.assertEqual(self.selection(part, direction, 0)["elevation_variant"], 0)
                self.assertEqual(self.selection(part, direction, 1)["elevation_variant"], 1)
            self.assertEqual(self.selection(2, direction, 8)["elevation_variant"], 0)
            self.assertEqual(self.selection(2, direction, 9)["elevation_variant"], 1)
            for owner in self.selection(2, direction, 8)["body"]:
                self.assertEqual(owner["selected_default_sprite"], owner["default_sprite_variants"][0])

    def test_read_only_selection_never_changes_its_inventory(self):
        original = copy.deepcopy(self.inventory)
        row = self.selection(0, 0, 1)
        row["body"][0]["origin"][0] = 900
        self.assertEqual(original, self.inventory)
        self.assertFalse(self.inventory["reviewed"])
        self.assertEqual(self.inventory["final_visual_approvals"], 0)
        self.assertTrue(self.inventory["runtime_selection"]["callback_offsets_required"])

    def test_invalid_boolean_fractional_or_out_of_range_selection_is_not_coerced(self):
        for values in ((True, 0, 0), (0, False, 0), (0, 0, 8.0), (0, 0, 8.5), (3, 0, 0), (0, 4, 0), (0, 0, -1)):
            with self.assertRaises(ValueError):
                default_lock_selection(*values, inventory=self.inventory)

    def test_custom_river_edge_offsets_cover_flat_and_all_four_slopes_without_claiming_ids(self):
        offsets = self.inventory["river_edge_source_offsets"]
        self.assertEqual(len(offsets), 60)
        self.assertEqual({row["offset"] for row in offsets}, set(range(60)))
        self.assertTrue(all("sprite" not in row for row in offsets))
        self.assertIn("intentionally absent", self.inventory["runtime_selection"]["river_bank_absence"])

    def test_custom_river_ground_selectors_include_flat_and_all_slopes_without_surface_only_claim(self):
        grounds = self.inventory["river_ground_source_selectors"]
        self.assertEqual({(row["slope"],row["ground_offset"],row["flat_sprite_adds_one"]) for row in grounds},
                         {("SLOPE_FLAT",0,False),("SLOPE_SE",0,True),("SLOPE_NE",1,True),("SLOPE_SW",2,True),("SLOPE_NW",3,True)})
        self.assertTrue(all("sprite" not in row for row in grounds))
        self.assertIn("raised rocks/islands",self.inventory["scope"])
        self.assertFalse(self.inventory["reviewed"])

    def test_river_ground_offset_changes_need_source_review_even_when_edge_groups_match(self):
        changed = self.drawing.replace("case SLOPE_NE: offset += 1; edges_offset += 24; break;",
                                       "case SLOPE_NE: offset += 2; edges_offset += 24; break;")
        self.assertNotEqual(changed,self.drawing)
        with self.assertRaisesRegex(ValueError,"ground/edge offset coupling"):
            runtime_selection(changed,self.enums,self.directions,self.flags)

    def test_river_ground_flat_flag_and_selected_draw_are_not_guessed_from_slope_names(self):
        for changed in (self.drawing.replace("offset = HasBit(_water_feature[CF_RIVER_SLOPE].flags, CFF_HAS_FLAT_SPRITE) ? 1 : 0;",
                                             "offset = HasBit(_water_feature[CF_RIVER_SLOPE].flags, CFF_HAS_FLAT_SPRITE) ? 2 : 0;"),
                        self.drawing.replace("default:       offset  = 0; break;","default:       offset  = 1; break;"),
                        self.drawing.replace("DrawGroundSprite(image + offset, PAL_NONE);","DrawGroundSprite(image, PAL_NONE);")):
            self.assertNotEqual(changed,self.drawing)
            with self.assertRaises(ValueError):
                runtime_selection(changed,self.enums,self.directions,self.flags)

    def test_unknown_constant_operations_and_cycles_are_rejected(self):
        for source, expression in (("static const SpriteID X = X + 1;", "X"),
                                   ("static const SpriteID X = 4 * 2;", "X"), ("", "True"), ("", "__import__('os')")):
            with self.assertRaises(ValueError):
                constant_reader(source)(expression)

    def test_source_tables_reject_missing_or_extra_body_owner(self):
        line = "TILE_SEQ_LINE(0,  0, 0, TILE_SIZE, 1, LOCK_HEIGHT_MIDDLE_REAR,  0 + 1)"
        for changed in (self.table.replace(line, "", 1), self.table.replace(line, line + "\n" + line, 1)):
            with self.assertRaises(ValueError):
                layers(changed, self.constants)

    def test_source_tables_reject_reordered_parts(self):
        with self.assertRaises(ValueError):
            layers(self.table.replace("TILE_SPRITE_LINE(1, _lock_display_middle_ne_seq)", "TILE_SPRITE_LINE(1, _lock_display_upper_ne_seq)"), self.constants)

    def test_source_selection_rejects_changed_elevation_or_missing_callback(self):
        for changed in (self.drawing.replace("part == LockPart::Upper ? 8 : 0", "part == LockPart::Upper ? 0 : 0"),
                        self.drawing.replace("GetCanalSpriteOffset(feature, ti->tile, tile_offs)", "tile_offs")):
            with self.assertRaises(ValueError):
                runtime_selection(changed, self.enums, self.directions, self.flags)

    def test_source_selection_rejects_lost_custom_flat_flag_or_river_callback(self):
        for changed in (self.drawing.replace("HasBit(_water_feature[CF_WATERSLOPE].flags, CFF_HAS_FLAT_SPRITE)", "false"),
                        self.drawing.replace("GetCanalSpriteOffset(CF_RIVER_SLOPE, ti->tile, offset)", "offset")):
            with self.assertRaises(ValueError):
                runtime_selection(changed, self.enums, self.directions, self.flags)

    def test_complete_default_export_is_not_live_geometry_approval(self):
        result = validate_default_export(self.exported(), self.inventory)
        self.assertEqual(result["source_entries_verified"], 52)
        self.assertFalse(result["live_custom_selection_verified"])
        self.assertFalse(result["geometry_or_quality_approved"])

    def test_default_export_rejects_missing_duplicate_or_wrong_sprite_owner(self):
        rows = self.exported()
        wrong = copy.deepcopy(rows)
        wrong[0]["sprite"] += 1
        for changed in (rows[:-1], rows + rows[:1], wrong):
            with self.assertRaises(ValueError):
                validate_default_export(changed, self.inventory)

    def test_default_export_rejects_coercion_or_registration_loss(self):
        for field, value in (("sprite", True), ("style", False), ("variant", 0.0), ("offset", [-128.0, -40]),
                             ("size", [256, 0]), ("image", "foreign.pam")):
            rows = self.exported()
            rows[0][field] = value
            with self.assertRaises(ValueError):
                validate_default_export(rows, self.inventory)


if __name__ == "__main__":
    unittest.main()

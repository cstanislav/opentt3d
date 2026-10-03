"""Actual callback values distinguish river features; source role is never quality approval."""
import copy
import re
import unittest

from live_river_selectors import selected_river_selectors, source_slopes
from original_water import ROOT


class RiverSelectorTests(unittest.TestCase):
    def sources(self):
        fixture = {"map_width":128,"map_height":128}
        ground = dict(tile=4002,tile_xy=[34,31],climate=0,water_class=2,slope=3,source_height=0,draw_origin=[544,496,0],
            feature="CF_RIVER_SLOPE",base_sprite=11264,selected_sprite=11267,requested_offset=3,resolved_offset=3,
            feature_flags=1,offset_callback=True,absent=False,palette=0,base_set="OpenGFX2 Classic",base_graphics=True,
            source_offset=[-124,0],source_size=[256,92],source_file="ogfx2e_extra_8",source_image="ground.pam",source_image_sha256="a"*64,texture_generation=3)
        edge = dict(ground,feature="CF_RIVER_EDGE",base_sprite=10000,selected_sprite=10037,requested_offset=36,resolved_offset=37,
            feature_flags=0,source_size=[148,40],source_image="edge.pam",source_image_sha256="b"*64)
        return fixture,[ground,edge]

    def test_source_corner_bits_are_independent_of_screen_order(self):
        self.assertEqual(source_slopes(),{"SLOPE_FLAT":0,"SLOPE_NE":12,"SLOPE_SE":6,"SLOPE_SW":3,"SLOPE_NW":9})
        source = (ROOT / "src/slope_type.h").read_text()
        with self.assertRaisesRegex(ValueError,"composition"):
            source_slopes(source.replace("SLOPE_N | SLOPE_E,","SLOPE_S | SLOPE_W,"))

    def test_observer_is_default_off_excludes_synthetic_and_never_resolves_callbacks_again(self):
        export = (ROOT / "src/renderer3d/reference_export.cpp").read_text()
        observer = export.split("void RetainRiverSelector(",1)[1].split("void ExportHouseReferences()",1)[0]
        observer = re.sub(r"/\*.*?\*/|//[^\n]*","",observer,flags=re.S)
        self.assertNotRegex(observer,r"\b(?:GetCanalSprite|GetCanalSpriteOffset|Random|InteractiveRandom)\s*\(")
        self.assertIn("!WaterSourceTracingEnabled()",observer)
        enabled = export.split("bool WaterSourceTracingEnabled()",1)[1].split("void ObserveWaterSource(",1)[0]
        self.assertIn('std::getenv("OPENTT3D_EXPORT_WATER_SOURCES")',enabled)
        self.assertIn('std::string_view(value) == "1"',enabled)
        capture = (ROOT / "src/renderer3d/world_capture.cpp").read_text()
        wrapper = capture.split("void ObserveRiverSelector(",1)[1].split("void BeginCapture(",1)[0]
        for guard in ("!WaterSourceTracingEnabled()","!capture","capture->diagnostic","capture->tile == nullptr","capture->tile->tile != tile"):
            self.assertIn(guard,wrapper)
        drawing = (ROOT / "src/water_cmd.cpp").read_text()
        river = drawing.split("static void DrawRiverWater(",1)[1].split("void DrawShoreTile",1)[0]
        sprite = drawing.split("static void DrawWaterSprite(",1)[1].split("static void DrawWaterEdges(",1)[0]
        for body in (river,sprite):
            self.assertEqual(len(re.findall(r"\bGetCanalSpriteOffset\s*\(",body)),1)
        self.assertEqual(len(re.findall(r"\bGetCanalSprite\s*\(",river)),1)

    def test_custom_callback_outputs_are_retained_not_forced_to_input_or_classic_ids(self):
        fixture,rows = self.sources()
        rows[1].update(base_graphics=False,source_file="custom-bank")
        result = selected_river_selectors(rows,fixture,0)
        self.assertEqual(result["observed_tiles"],1)
        self.assertEqual(result["edge_sources"][0]["resolved_offset"],37)
        self.assertEqual(result["edge_sources"][0]["requested_offset"],36)
        self.assertFalse(result["edge_sources"][0]["base_graphics"])
        for key in ("complete_river_family_verified","raised_water_ownership_verified","layer_order_or_animation_verified","geometry_or_quality_approved"):
            self.assertIs(result[key],False)

    def test_empty_or_undrawn_edges_never_establish_absence(self):
        fixture,rows = self.sources()
        self.assertEqual(selected_river_selectors([],fixture,0)["absent_edge_features"],[])
        self.assertEqual(selected_river_selectors(rows[:1],fixture,0)["absent_edge_features"],[])
        absent = {key:value for key,value in rows[1].items() if key not in ("source_offset","source_size","source_file","base_graphics","source_image","source_image_sha256")}
        absent.update(base_sprite=0,selected_sprite=0,resolved_offset=0,offset_callback=False,absent=True)
        result = selected_river_selectors([rows[0],absent],fixture,0)
        self.assertEqual(len(result["absent_edge_features"]),1)
        self.assertEqual(result["edge_sources"],[])
        with self.assertRaisesRegex(ValueError,"present and absent"):
            selected_river_selectors(rows+[absent],fixture,0)
        absent["source_image_sha256"] = "c"*64
        with self.assertRaisesRegex(ValueError,"zero feature base"):
            selected_river_selectors([rows[0],absent],fixture,0)

    def test_flat_flag_and_every_slope_group_keep_original_offset_inputs(self):
        fixture,rows = self.sources()
        for slope,slot,group in ((0,0,0),(12,1,24),(6,0,12),(3,2,36),(9,3,48)):
            for flag in (0,1):
                if slope == 0 and flag == 0:
                    continue
                changed = copy.deepcopy(rows)
                request = 0 if slope == 0 else slot+flag
                changed[0].update(slope=slope,feature_flags=flag,requested_offset=request,resolved_offset=request,selected_sprite=11264+request)
                changed[1].update(slope=slope,requested_offset=group,resolved_offset=group+1,selected_sprite=10000+group+1)
                self.assertEqual(selected_river_selectors(changed,fixture,0)["observed_slopes"],[slope])
                changed[0]["requested_offset"] += 1
                with self.assertRaisesRegex(ValueError,"custom river ground"):
                    selected_river_selectors(changed,fixture,0)

    def test_default_sloped_ground_keeps_zero_edge_group_and_no_offset_callback(self):
        fixture,rows = self.sources()
        rows[0].update(base_sprite=0,selected_sprite=5330,requested_offset=0,resolved_offset=0,offset_callback=False)
        rows[1].update(requested_offset=0,resolved_offset=1,selected_sprite=10001)
        self.assertEqual(selected_river_selectors(rows,fixture,0)["ground_sources"][0]["selected_sprite"],5330)
        rows[1]["requested_offset"] = 36
        with self.assertRaisesRegex(ValueError,"ground/edge source groups"):
            selected_river_selectors(rows,fixture,0)

    def test_missing_ground_and_mismatched_tile_state_cannot_be_merged(self):
        fixture,rows = self.sources()
        with self.assertRaisesRegex(ValueError,"ground owner"):
            selected_river_selectors(rows[1:],fixture,0)
        rows[1].update(source_height=8,draw_origin=[544,496,8])
        with self.assertRaisesRegex(ValueError,"tile state"):
            selected_river_selectors(rows,fixture,0)

    def test_reloads_deduplicate_only_exact_metadata_and_image_bytes(self):
        fixture,rows = self.sources()
        duplicate = copy.deepcopy(rows)
        for row in duplicate:
            row.update(texture_generation=7,source_image="renamed.pam")
        self.assertEqual(selected_river_selectors(rows+duplicate,fixture,0),selected_river_selectors(rows,fixture,0))
        duplicate[0]["source_image_sha256"] = "c"*64
        with self.assertRaisesRegex(ValueError,"conflicting"):
            selected_river_selectors(rows+duplicate,fixture,0)

    def test_registration_boolean_coercions_unknown_features_and_missing_provenance_fail(self):
        fixture,rows = self.sources()
        for key,value in (("climate",True),("slope",True),("tile",4002.0),("source_height",8.0),("tile_xy",[35,31]),
                          ("draw_origin",[544,496,1]),("feature","CF_DIKES"),("base_sprite",True),("resolved_offset",3.0),
                          ("requested_offset",-1),("offset_callback",1),("feature_flags",True),("feature_flags",256),("absent",1),
                          ("palette",False),("source_size",[256,0]),("source_offset",[-124.0,0]),("source_image_sha256","g"*64),
                          ("base_set",""),("source_file",""),("base_graphics",1)):
            changed = copy.deepcopy(rows)
            changed[0][key] = value
            with self.subTest(field=key,value=value), self.assertRaises(ValueError):
                selected_river_selectors(changed,fixture,0)


if __name__ == "__main__":
    unittest.main()

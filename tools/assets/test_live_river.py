"""Incidental river callbacks cannot invent banks, classify IDs or approve a family."""
import copy
import unittest

from live_water import selected_river_sources


class LiveRiverTests(unittest.TestCase):
    def sources(self):
        fixture = {"map_width":128,"map_height":128}
        base = dict(kind="sloped-river",climate=0,water_class=2,slope=3,tile=4002,tile_xy=[34,31],
            source_height=0,draw_origin=[544,496,0],role="ground",transparent=False,cropped=False,
            sprite=11267,image=11267,palette=0,source_offset=[-124,0],source_size=[256,92],
            base_graphics=True,base_set="OpenGFX2 Classic",source_file="ogfx2e_extra_8",source_image_sha256="a"*64,
            texture_generation=3,source_image="water-original.pam")
        bank = dict(base,sprite=10343,image=10343,source_size=[148,40],source_image_sha256="b"*64,source_image="bank-original.pam")
        return fixture, [base,bank]

    def test_water_and_bank_ground_are_retained_but_not_classified_from_numeric_ids(self):
        fixture, rows = self.sources()
        result = selected_river_sources(rows,fixture,0)
        self.assertEqual(len(result["selected_ground_sources"]),2)
        self.assertEqual(result["observed_tiles"],1)
        self.assertEqual(result["observed_slopes"],[3])
        for key in ("feature_offsets_resolved","conditional_absences_verified","layer_order_or_animation_verified",
                    "complete_river_family_verified","geometry_or_quality_approved"):
            self.assertIs(result[key],False)
        self.assertTrue(all("feature" not in row and "bank" not in row for row in result["selected_ground_sources"]))

    def test_reloads_duplicate_sources_without_losing_bytes_or_inventing_draw_order(self):
        fixture, rows = self.sources()
        changed = copy.deepcopy(rows)
        for row in changed:
            row.update(texture_generation=19,source_image="renamed.pam")
        self.assertEqual(selected_river_sources(rows+changed,fixture,0),selected_river_sources(rows,fixture,0))
        self.assertEqual(selected_river_sources(list(reversed(rows)),fixture,0),selected_river_sources(rows,fixture,0))
        changed[0]["source_image_sha256"] = "c"*64
        with self.assertRaisesRegex(ValueError,"conflicting"):
            selected_river_sources(rows+changed,fixture,0)
        changed = copy.deepcopy(rows)
        changed[1].update(source_height=8,draw_origin=[544,496,8])
        with self.assertRaisesRegex(ValueError,"tile state"):
            selected_river_sources(changed,fixture,0)

    def test_unobserved_rivers_do_not_prove_absence_or_complete_source_selection(self):
        fixture, _ = self.sources()
        result = selected_river_sources([dict(kind="lock")],fixture,0)
        self.assertEqual(result["selected_ground_sources"],[])
        self.assertIs(result["conditional_absences_verified"],False)
        self.assertIs(result["complete_river_family_verified"],False)

    def test_coerced_registration_flags_sizes_and_provenance_are_rejected(self):
        fixture, rows = self.sources()
        for key,value in (("tile",True),("source_height",0.0),("draw_origin",[545,496,0]),("tile_xy",[34,32]),
                          ("slope",0),("slope",True),("water_class",1),("palette",True),("image",11267.0),
                          ("role","body"),("sequence_origin",[0,0,0]),("source_offset",[-124.0,0]),("source_size",[256,0]),
                          ("source_file",""),("base_set",""),("base_graphics",1),("cropped",True),("transparent",True),
                          ("source_image_sha256","g"*64)):
            changed = copy.deepcopy(rows)
            changed[0][key] = value
            with self.subTest(field=key,value=value), self.assertRaises(ValueError):
                selected_river_sources(changed,fixture,0)

    def test_custom_provenance_is_retained_not_silently_replaced_with_classic_or_another_climate(self):
        fixture, rows = self.sources()
        rows[0].update(base_graphics=False,source_file="custom-river",base_set="Alternative")
        result = selected_river_sources(rows,fixture,0)
        custom = next(row for row in result["selected_ground_sources"] if row["sprite"] == 11267)
        self.assertIs(custom["base_graphics"],False)
        self.assertEqual(custom["source_file"],"custom-river")
        with self.assertRaisesRegex(ValueError,"climate"):
            selected_river_sources(rows,fixture,1)


if __name__ == "__main__":
    unittest.main()

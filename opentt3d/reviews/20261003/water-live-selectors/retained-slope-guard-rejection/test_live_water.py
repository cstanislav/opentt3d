"""Source selection must be actual, complete and exact; no static-ID or score inheritance."""
import copy
import unittest

from live_water import selected_lock_sources
from original_water import catalogue


class LiveWaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals = catalogue()

    def sources(self):
        fixture = {"map_width": 128, "map_height": 128, "locks": []}
        observations = []
        for elevation in range(2):
            for direction in range(4):
                x, y = 12+direction*10, 12+elevation*12
                tile = x+128*y
                delta = (-1,128,1,-128)[direction]
                fixture["locks"].append(dict(tile=tile,x=x,y=y,lower=tile-delta,upper=tile+delta,
                    height=elevation,direction=direction,elevation=elevation,connected_both_ways=True))
                for part, location in enumerate((tile,tile-delta,tile+delta)):
                    xy = [location % 128,location // 128]
                    height = (elevation+int(part == 2))*8
                    base = dict(kind="lock",tile=location,tile_xy=xy,climate=0,direction=direction,part=part,
                        slope=(9,12,6,3)[direction] if part == 0 else 0,water_class=1,
                        source_height=height,palette=0,draw_origin=[xy[0]*16,xy[1]*16,height],cropped=False,transparent=False,
                        source_file="test-source",base_set="test-base-set",base_graphics=True,source_offset=[-128,-40],
                        source_size=[256,80],source_image_sha256="a"*64,texture_generation=3,source_image="original.pam")
                    observations.append(dict(base,role="ground",sprite=9000,image=9000))
                    for face, owner in enumerate(self.originals["locks"][part*4+direction]["body"]):
                        sprite = 10000+elevation*24+owner["sprite_offset"]
                        observations.append(dict(base,role="body",sprite=sprite,image=sprite,sequence_origin=owner["origin"],
                            sequence_offset=[0,0,0],sort_extent=owner["sort_extent"]))
        return fixture, observations

    def test_all48_dynamic_walls_and24_independent_water_owners_are_not_geometry_approval(self):
        fixture, rows = self.sources()
        result = selected_lock_sources(rows,fixture,0,self.originals)
        self.assertEqual(result["wall_owner_states_verified"],48)
        self.assertEqual(result["independent_water_owners_verified"],24)
        self.assertFalse(result["dynamic_ids_inferred"])
        self.assertFalse(result["geometry_or_quality_approved"])

    def test_slope_water_class_and_source_provenance_cannot_be_coerced_or_lost(self):
        fixture, rows = self.sources()
        for key,value in (("slope",0),("slope",True),("water_class",True),("water_class",3),("source_file",""),
                          ("base_set",""),("image",float(rows[1]["image"])),("source_size",[0,80])):
            changed = copy.deepcopy(rows)
            changed[1][key] = value
            with self.assertRaises(ValueError):
                selected_lock_sources(changed,fixture,0,self.originals)

    def test_reload_or_repeat_never_changes_pixels_owners_or_registration(self):
        fixture, rows = self.sources()
        original = copy.deepcopy(rows)
        repeated = copy.deepcopy(rows)
        for row in repeated:
            row["texture_generation"] = 9
            row["source_image"] = "reloaded.pam"
        self.assertEqual(selected_lock_sources(rows,fixture,0,self.originals),selected_lock_sources(rows+repeated,fixture,0,self.originals))
        self.assertEqual(rows,original)

    def test_missing_foreign_or_coerced_owner_is_rejected(self):
        fixture, rows = self.sources()
        for key,value in (("climate",True),("source_height",0.0),("draw_origin",[0,0,0]),("tile",1),
                          ("sequence_origin",[0,1,0]),("sort_extent",[16,1,99]),("sequence_offset",[1,0,0]),("source_image_sha256","b")):
            changed = copy.deepcopy(rows)
            changed[1][key] = value
            with self.assertRaises(ValueError):
                selected_lock_sources(changed,fixture,0,self.originals)
        with self.assertRaises(ValueError):
            selected_lock_sources(rows[:-1],fixture,0,self.originals)

    def test_same_saved_owner_cannot_change_one_source_byte(self):
        fixture, rows = self.sources()
        changed = copy.deepcopy(rows[1])
        changed["source_image_sha256"] = "b"*64
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            selected_lock_sources(rows+[changed],fixture,0,self.originals)

    def test_source_provenance_is_retained_without_assuming_classic_compatibility(self):
        fixture, rows = self.sources()
        for row in rows:
            row["base_graphics"] = False
            row["base_set"] = "alternative"
        result = selected_lock_sources(rows,fixture,0,self.originals)
        self.assertTrue(all(not owner["source"]["base_graphics"] for owner in result["bodies"]))
        self.assertFalse(result["geometry_or_quality_approved"])

    def test_saved_site_direction_elevation_or_overlap_is_not_forced(self):
        fixture, rows = self.sources()
        for key,value in (("direction",True),("elevation",1),("upper",100),("height",1),("connected_both_ways",False)):
            changed = copy.deepcopy(fixture)
            changed["locks"][0][key] = value
            with self.assertRaises(ValueError):
                selected_lock_sources(rows,changed,0,self.originals)


if __name__ == "__main__":
    unittest.main()

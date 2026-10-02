import unittest

from original_objects import catalogue, layers, SOURCE, SPRITES


class OriginalObjectCatalogueTests(unittest.TestCase):
    def test_all_original_types_and_twenty_hq_tiles_preserve_source_order(self):
        result = catalogue()
        self.assertEqual([row["id"] for row in result["types"]],list(range(5)))
        self.assertEqual(len(result["tiles"]),24)
        headquarters = result["tiles"][4:]
        self.assertEqual([row["size_stage"] for row in headquarters],[stage for stage in range(5) for part in range(4)])
        self.assertEqual([row["tile_offset"] for row in headquarters],[[0,0],[1,0],[0,1],[1,1]]*5)
        self.assertEqual(result["headquarters_ground_only_slots"],11)
        self.assertTrue(all(row["ground"]["company_colour"] for row in headquarters))
        self.assertFalse(any(row["reviewed"] for row in result["types"]+result["tiles"]))
        self.assertEqual(result["final_visual_approvals"],0)

    def test_ground_only_hq_sizes_and_southern_tiles_do_not_gain_fake_bodies(self):
        headquarters = catalogue()["tiles"][4:]
        self.assertTrue(all(not row["body"] for row in headquarters[:8]))
        self.assertTrue(all(not headquarters[stage*4+3]["body"] for stage in range(5)))
        self.assertTrue(all(len(headquarters[stage*4+part]["body"])==1 for stage in range(2,5) for part in range(3)))
        self.assertEqual(headquarters[9]["ground"]["sprite"],2615,"HQ west/east source order follows the original tile layout")
        self.assertEqual(headquarters[10]["ground"]["sprite"],2613)
        self.assertEqual([headquarters[stage*4]["body"][0]["sort_extent"] for stage in (2,3,4)],[[16,16,20],[16,16,50],[16,16,60]])

    def test_original_non_hq_origins_sort_extents_and_company_colour_remain_distinct(self):
        result = catalogue()
        self.assertEqual([row["body"][0]["origin"] for row in result["tiles"][:4]],[[7,7,0],[4,4,0],[0,0,0],[8,8,0]])
        self.assertEqual([row["body"][0]["sort_extent"] for row in result["tiles"][:4]],[[2,2,70],[7,7,61],[16,16,25],[1,1,6]])
        self.assertEqual([row["body"][0]["company_colour"] for row in result["tiles"][:4]],[False,False,True,True])
        self.assertEqual(result["tiles"][0]["ground"],result["tiles"][1]["ground"])

    def test_climate_flags_and_ground_ownership_are_not_generalized(self):
        types = catalogue()["types"]
        self.assertEqual(types[0]["climates"],["temperate","arctic","tropic"])
        self.assertEqual(types[1]["climates"],["temperate","arctic"])
        self.assertIn("HasNoFoundation",types[3]["flags"])
        self.assertNotIn("HasNoFoundation",types[4]["flags"])
        self.assertEqual(types[3]["footprint_tiles"],[1,1])
        self.assertEqual(types[4]["footprint_tiles"],[2,2])
        self.assertEqual(len(types[4]["climates"]),4)

    def test_missing_or_unknown_source_layers_are_rejected(self):
        source, sprites = SOURCE.read_text(), SPRITES.read_text()
        for changed in (source.replace("TILE_SPRITE_LINE_NOTHING(SPR_TINYHQ_NORTH)",""),
                        source.replace("SPR_HUGEHQ_EAST_GROUND","SPR_UNKNOWN_OBJECT_SOURCE"),
                        source.replace("_object_hq_huge_north)","_object_hq_unknown_north)"),
                        source.replace("PAL_NONE }, _object_lighthouse_seq","PAL_UNKNOWN }, _object_lighthouse_seq")):
            with self.subTest(changed=changed[-50:]), self.assertRaises(ValueError):
                layers(changed,sprites)

    def test_source_metadata_does_not_apply_a_geometry_or_simulation_scale(self):
        source = SOURCE.read_text().replace("2,  2, 70","2,  2, 72")
        result = layers(source,SPRITES.read_text())
        self.assertEqual(result["tiles"][0]["body"][0]["sort_extent"],[2,2,72])
        self.assertNotIn("voxel_states",result["tiles"][0])
        self.assertNotIn("voxel_geometry",result["tiles"][0])


if __name__ == "__main__":
    unittest.main()

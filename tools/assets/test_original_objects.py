import copy
import unittest

from original_objects import catalogue, layers, runtime_selection, validate_export, SOURCE, SPRITES, DRAWING


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

    def export_fixture(self):
        exported = []
        for original in catalogue()["tiles"]:
            row = {key:copy.deepcopy(original[key]) for key in ("object_id","size_stage","part","tile_offset")}
            for role, layers in (("ground",[original["ground"]]),("body",original["body"])):
                images = []
                for index,layer in enumerate(layers):
                    image = {key:copy.deepcopy(layer[key]) for key in ("sprite","sprite_flags","company_colour")}
                    if role == "body":
                        image.update({key:copy.deepcopy(layer[key]) for key in ("origin","sort_extent")})
                    stage = row["size_stage"] if row["size_stage"] is not None else 0
                    image.update(palette=layer["palette_id"],sprite_offset=[-124,-240],sprite_size=[32,65],palette_indices=[1,7,198],
                                 image=f"object-{row['object_id']}-{stage}-{row['part']}-{role}"+(f"-{index}" if role == "body" else "")+".pam")
                    images.append(image)
                row[role] = images[0] if role == "ground" else images
            exported.append(row)
        return exported

    def test_native_export_matches_every_source_layer_and_preserves_genuine_body_absences(self):
        result = validate_export(self.export_fixture())
        self.assertEqual(result,{"source_equivalent_layouts":24,"ground_layers":24,"separate_body_layers":13,"ground_only_headquarters_slots":11})

    def test_wrong_source_flags_offsets_extents_and_layer_ownership_are_rejected(self):
        for key,value in (("sprite",123),("sprite_flags",0),("company_colour",False),("origin",[0,0,1]),("sort_extent",[16,16,40]),
                          ("image","../../other.pam"),("sprite_offset",[0]),("sprite_size",[0,65]),("palette_indices",[7,7])):
            exported = self.export_fixture()
            exported[12]["body"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_export(exported)
        exported = self.export_fixture()
        exported[4]["body"] = copy.deepcopy(exported[12]["body"])
        with self.assertRaisesRegex(ValueError,"body ownership"):
            validate_export(exported)

    def test_reordered_or_missing_native_tiles_do_not_validate_a_complete_hq(self):
        exported = self.export_fixture()
        exported[13], exported[14] = exported[14], exported[13]
        with self.assertRaisesRegex(ValueError,"source order"):
            validate_export(exported)
        with self.assertRaisesRegex(ValueError,"layout count"):
            validate_export(exported[:-1])

    def test_null_size_metadata_must_be_explicit_and_source_integer_types_cannot_be_coerced(self):
        exported = self.export_fixture()
        del exported[0]["size_stage"]
        with self.assertRaisesRegex(ValueError,"source order"):
            validate_export(exported)
        for key,value in (("object_id",False),("part",0.0),("tile_offset",[0,False])):
            exported = self.export_fixture()
            exported[0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,"source order"):
                validate_export(exported)
        for key,value in (("company_colour",0),("sprite_flags",0.0),("palette",False)):
            exported = self.export_fixture()
            exported[0]["ground"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,"layer metadata"):
                validate_export(exported)
        exported = self.export_fixture()
        exported[0]["body"][0]["origin"] = [7.0,7,0]
        with self.assertRaisesRegex(ValueError,"layer metadata"):
            validate_export(exported)

    def test_original_runtime_selector_preserves_upgrades_tile_order_and_ground_visibility(self):
        result = runtime_selection(DRAWING.read_text())
        self.assertEqual(result["headquarters_score_thresholds"],[170,350,520,720])
        self.assertTrue(result["headquarters_upgrades_only"])
        self.assertEqual(result["headquarters_tile_order"],["north","west","east","south"])
        source = DRAWING.read_text()
        for old,new in (("score >= 350","score >= 349"),("GetCompanyHQSize(tile) < val","GetCompanyHQSize(tile) != val"),
                        ("TileY(diff) << 1 | TileX(diff)","TileX(diff) << 1 | TileY(diff)"),
                        ("if (!IsInvisibilitySet(TO_STRUCTURES))","if (!IsTransparencySet(TO_STRUCTURES))")):
            with self.subTest(old=old), self.assertRaises(ValueError):
                runtime_selection(source.replace(old,new))


if __name__ == "__main__":
    unittest.main()

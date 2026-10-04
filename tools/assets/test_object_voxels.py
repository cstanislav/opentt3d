"""Original object volumes/ownership; geometry tests are not visual approval."""
import copy
import json
from pathlib import Path
import unittest

from compile_voxels import compile_catalogue
from original_objects import catalogue

ROOT = Path(__file__).resolve().parents[2]


class ObjectVoxelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT/"assets/3d/voxels.json").read_text())
        names = {"object_transmitter","object_lighthouse","object_owned_land_sign",
                 "object_company_statue","object_company_gnome","airport_radio_tower"}
        cls.source["models"] = {name:cls.source["models"][name] for name in names}
        cls.source["bindings"] = {"objects":{layout:states for layout,states in cls.source["bindings"]["objects"].items()
                                             if int(layout) < 4}}
        cls.compiled = compile_catalogue(cls.source)

    def paint(self,name):
        return {(x+i,y,z):tuple(self.compiled["materials"][material-1])
                for x,y,z,length,material in self.compiled["models"][name]["runs"] for i in range(length)}

    def test_only_present_original_object_climates_are_bound(self):
        original = catalogue()
        climates = ("temperate","arctic","tropic","toyland")
        for typ in original["types"][:4]:
            states = self.compiled["bindings"]["objects"][str(typ["id"])]
            self.assertEqual(set(states),{str(climates.index(climate)) for climate in typ["climates"]})
        self.assertEqual(sum(len(states) for states in self.compiled["bindings"]["objects"].values()),13)
        self.assertNotEqual(self.compiled["bindings"]["objects"]["2"]["0"],self.compiled["bindings"]["objects"]["2"]["3"])
        self.assertNotIn("object_ground",self.compiled["bindings"],"Ordinary climate/slope terrain remains independently source-owned")

    def test_transmitter_preserves_detailed_mast_and_only_removes_airport_fence(self):
        parent, object_cells = self.paint("airport_radio_tower"), self.paint("object_transmitter")
        remove = {tuple(self.source["materials"][name] if isinstance(self.source["materials"][name],list)
                        else [self.source["materials"][name]]*6) for name in ("radio_fence_post","air_company")}
        self.assertEqual(object_cells,{cell:paint for cell,paint in parent.items() if paint not in remove})
        self.assertEqual(self.compiled["models"]["object_transmitter"]["origin"],[-7,-7,0])
        self.assertEqual(self.compiled["models"]["object_transmitter"]["size"],self.compiled["models"]["airport_radio_tower"]["size"])
        self.assertTrue(any(239 in paint or 240 in paint for paint in object_cells.values()))
        self.assertNotIn((31,31,40),object_cells,"The detailed radio lattice still has actual empty air")

    def test_sign_and_each_sculpture_have_real_depth_and_source_palette_families(self):
        allowed = {
            "object_owned_land_sign":{1,2,9,10,11,199,201,203},
            "object_lighthouse":set(range(2,16))|set(range(73,79))|set(range(129,134))|{242,243,244},
            "object_company_statue":{9,11,12,14}|set(range(112,122))|set(range(198,205)),
            "object_company_gnome":set(range(1,16))|set(range(70,80))|set(range(88,95))|set(range(165,170))|set(range(198,206)),
        }
        for name,colours in allowed.items():
            cells = self.paint(name)
            self.assertGreater(len(cells),20)
            self.assertTrue({value for paint in cells.values() for value in paint} <= colours,name)
            spans = [max(cell[axis] for cell in cells)-min(cell[axis] for cell in cells)+1 for axis in range(3)]
            if name == "object_owned_land_sign":
                self.assertEqual(spans,[12,2,32],"The source sign keeps its half-unit real thickness, three-unit width, sixteen-unit height and original +X board orientation; do not inflate it to a generic solid")
            else:
                self.assertTrue(all(span >= 6 for span in spans),name)
            self.assertEqual(self.source["models"][name]["review_status"],"work-in-progress")
        self.assertNotIn("extends",self.source["models"]["object_company_gnome"])
        self.assertGreater(max(z for x,y,z in self.paint("object_company_gnome")),3*max(z for x,y,z in self.paint("object_company_statue")))

    def test_gnome_keeps_original_green_coat_and_pink_skin_on_their_own_body_parts(self):
        cells = self.paint("object_company_gnome")
        self.assertTrue(set(cells[48,40,40]) <= set(range(88,95)),"Original green coat may not be exchanged with skin despite both palettes existing in the source")
        self.assertTrue(set(cells[28,43,31]) <= set(range(165,170)),"Original pink hand remains skin, not coat green")
        self.assertTrue(set(cells[48,68,108]) <= set(range(165,170)),"The independently sculpted nose retains skin paint")

    def test_statue_preserves_eight_original_edge_bollards_without_filling_the_walkway(self):
        cells = self.paint("object_company_statue")
        for x,y in ((5,13),(13,5),(5,50),(13,58),(58,13),(50,5),(58,50),(50,58)):
            self.assertTrue(set(cells[x,y,5]) <= set(range(198,205)))
        self.assertNotIn((31,4,5),cells)
        self.assertNotIn((4,31,5),cells)

    def test_lighthouse_retains_open_lantern_cage_and_original_animated_lamp(self):
        cells = self.paint("object_lighthouse")
        self.assertNotIn((18,16,104),cells,"Real lamp-to-cage gap cannot become a solid billboard/extrusion")
        self.assertIn((14,14,103),cells)
        self.assertIn((14,14,107),cells)
        self.assertTrue({242,243,244} <= {colour for paint in cells.values() for colour in paint})
        self.assertIn((14,23,103),cells,"Lantern cage has independently supported posts")

    def test_compiler_rejects_unavailable_object_climates_and_absent_hq_bodies(self):
        cases = (("objects","0","3"),("objects","1","2"),("objects","1","3"),
                 ("objects","4","0"),("objects","11","0"),("objects","15","0"),
                 ("objects","19","0"),("objects","23","0"),("objects","24","0"),
                 ("objects","2","4"),("object_ground","0","0"))
        for category,identifier,state in cases:
            with self.subTest(binding=(category,identifier,state)):
                data = copy.deepcopy(self.source)
                data["bindings"] = {category:{identifier:{state:"object_owned_land_sign"}}}
                with self.assertRaisesRegex(ValueError,"Object bindings"):
                    compile_catalogue(data)

    def test_runtime_object_selection_is_read_only_and_preserves_source_fallback(self):
        source = (ROOT/"src/renderer3d/voxel_models.cpp").read_text()
        implementation = source.split("bool HasVoxelObjectLayout(",1)[1].split("bool DrawVoxelEffect(",1)[0]
        for required in ('set->name != "OpenGFX2 Classic"','TextureGeneration()',
                         'source->GetSequence().size() > 1','HasVoxelAsset("object_ground",layout,climate)',
                         'HasVoxelAsset("objects",layout,climate)','IsBaseGraphicsSprite(image)'):
            self.assertIn(required,implementation)
        for mutation in ("UpdateCompanyHQ","SetAnimationFrame","BuildObject(","Random(","Command<"):
            self.assertNotIn(mutation,implementation)


if __name__ == "__main__":
    unittest.main()

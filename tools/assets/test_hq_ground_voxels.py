"""Two ground-only HQ stages; structural tests never approve source/visual fidelity."""
import copy
import json
from pathlib import Path
import unittest

from compile_voxels import compile_catalogue
from original_objects import catalogue
from quality_audit import original_object_layer_model

ROOT = Path(__file__).resolve().parents[2]
CLIMATES = ("temperate","arctic","tropic","toyland")
PARTS = ("north","west","east","south")


class HeadquartersGroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT/"assets/3d/voxels.json").read_text())
        cls.source["models"] = {name:model for name,model in cls.source["models"].items() if name.startswith("hq_ground_")}
        cls.source["bindings"] = {"object_ground":cls.source["bindings"]["object_ground"]}
        cls.compiled = compile_catalogue(cls.source)
        cls.original = catalogue()

    def cells(self,name):
        return {(x+i,y,z):tuple(self.compiled["materials"][material-1])
                for x,y,z,length,material in self.compiled["models"][name]["runs"] for i in range(length)}

    def name(self,stage,climate,part):
        return f"hq_ground_{('tiny','small')[stage]}_{CLIMATES[climate]}_{PARTS[part]}"

    def joined(self,stage,climate):
        joined = {}
        for part in range(4):
            name = self.name(stage,climate,part)
            for cell,paint in self.cells(name).items():
                self.assertNotIn(cell,joined,"Two independent source owners must never duplicate a world cell")
                joined[cell] = paint
        return joined

    def test_two_complete_ground_only_families_are_bound_in_all_four_original_climates(self):
        self.assertEqual(len(self.compiled["models"]),32)
        self.assertEqual(set(self.compiled["bindings"]["object_ground"]),{str(layout) for layout in range(4,12)})
        self.assertNotIn("objects",self.compiled["bindings"],"Ground-owned cottage/turret relief cannot fill the absent sortable body")
        for row in self.original["tiles"]:
            if row["object_id"] != 4 or row["size_stage"] >= 2: continue
            self.assertEqual(row["body"],[])
            for climate in range(4):
                expected = self.name(row["size_stage"],climate,row["part"])
                self.assertEqual(original_object_layer_model(self.compiled,self.original,row,"ground",0,climate),expected)
                self.assertIsNone(original_object_layer_model(self.compiled,self.original,row,"body",0,climate))

    def test_each_owner_has_exact_tile_registration_and_complete_ground_contact(self):
        for stage in range(2):
            for climate in range(4):
                for part in range(4):
                    name = self.name(stage,climate,part); model = self.compiled["models"][name]
                    self.assertEqual(model["cell_size"],[0.5,0.5,0.5])
                    self.assertEqual(model["origin"],[-16*(part%2),-16*(part//2),-0.5])
                    cells = self.cells(name)
                    x0,y0 = 32*(part%2),32*(part//2)
                    # Flat soil belongs to its physical tile. Raised artwork
                    # retains the explicit original native owner rather than
                    # incorrectly sending an entire vertical column next door.
                    for x,y,z in cells:
                        self.assertEqual(2*x-z >= 64,bool(part%2),name)
                        self.assertEqual(2*y-z >= 64,bool(part//2),name)
                    self.assertEqual({(x,y) for x,y,z in cells if z == 0},{(x,y) for x in range(x0,x0+32) for y in range(y0,y0+32)})
                    self.assertEqual(self.source["models"][name]["review_status"],"work-in-progress")

    def test_partition_is_exactly_the_explicit_compound_not_a_resized_or_truncated_copy(self):
        for stage in range(2):
            for climate in range(4):
                source = copy.deepcopy(self.source)
                name = self.name(stage,climate,0)
                source["models"] = {"joined":{**source["models"][name],"ops":source["models"][name]["ops"][:-1]}}
                source["bindings"] = {}
                compiled = compile_catalogue(source)
                expected = {(x+i,y,z):tuple(compiled["materials"][material-1])
                            for x,y,z,length,material in compiled["models"]["joined"]["runs"] for i in range(length)}
                self.assertEqual(self.joined(stage,climate),expected)

    def test_original_cottage_shed_turret_and_gate_keep_real_depth_and_openings(self):
        ordinary = self.joined(0,0); small = self.joined(1,0)
        self.assertNotIn((23,29,9),ordinary,"The cottage interior is real air, not a stretched solid block")
        self.assertIn((14,31,8),ordinary,"Inset glazing remains on the recessed back plane")
        self.assertNotIn((14,32,8),ordinary,"Window aperture keeps an actual recess")
        self.assertIn((23,29,19),ordinary,"Company-coloured roof retains true sloped height")
        self.assertNotIn((48,19,4),small,"The separately modelled shed retains its real interior")
        self.assertIn((48,19,10),small,"Corrugated shed roof is volumetric and supported by its own walls")
        castle = self.joined(1,3)
        self.assertNotIn((32,33,15),castle,"The Toyland turret is hollow, never a recoloured cottage")
        self.assertNotIn((32,59,5),castle,"The entrance between curtain walls remains genuinely open")
        self.assertIn((4,4,16),castle,"Individual battlements are true XYZ cells")
        self.assertNotIn((8,4,16),castle,"Crenellation gaps remain real air")

    def test_climate_ground_and_toyland_structures_do_not_alias_unrelated_source_art(self):
        yards = [self.joined(0,climate) for climate in range(4)]
        for first in range(4):
            for second in range(first+1,4): self.assertNotEqual(yards[first],yards[second])
        self.assertTrue(set(yards[0][23,29,19]) <= set(range(198,204)))
        self.assertTrue(set(yards[3][35,32,63]) <= {200,202,203})
        self.assertNotIn((23,29,19),yards[3],"Toyland is a turret and checker field, not the ordinary company cottage")
        self.assertIn(yards[3][4,4,0][-1],{84,206})
        self.assertEqual(yards[3][0,0,0][-1],82)
        self.assertNotEqual(yards[3][0,0,0][-1],yards[3][4,4,0][-1],"The original dark/light Toyland checker lawn must not collapse to one top-face colour")

    def test_one_missing_ground_owner_restores_the_complete_original_family(self):
        partial = copy.deepcopy(self.compiled)
        del partial["bindings"]["object_ground"]["6"]["0"]
        rows = [row for row in self.original["tiles"] if row["object_id"] == 4 and row["size_stage"] == 0]
        for row in rows:
            self.assertIsNone(original_object_layer_model(partial,self.original,row,"ground",0,0))
            self.assertEqual(original_object_layer_model(partial,self.original,row,"ground",0,1),self.name(0,1,row["part"]))

    def test_ordinary_windows_keep_the_original_cool_glazing_not_soil_colours(self):
        # Native source pixels at registered5,27/6,28/21,20 are131 in each
        # ordinary climate.122...127 are rust/brown, not the original glazing.
        for stage in range(2):
            for climate in range(3):
                cells = self.joined(stage,climate)
                self.assertTrue(set(cells[14,31,8]) <= {130,131})
                self.assertTrue(set(cells[27,31,8]) <= {130,131})
                self.assertTrue(set(cells[28,28,8]) <= {130,131})
                self.assertGreater(len({paint[-1] for (x,y,z),paint in cells.items() if z == 0 and x < 4}),1,
                                   "Source-owned outer turf must retain separate original palette grain, not a uniform strip")

    def test_north_source_keeps_the_complete_cottage_facade_not_an_east_wall_duplicate(self):
        for stage in range(2):
            for climate in range(3):
                north = self.cells(self.name(stage,climate,0))
                east = self.cells(self.name(stage,climate,2))
                self.assertIn((14,31,8),north)
                self.assertIn((21,31,8),north)
                self.assertNotIn((14,32,8),east)
                self.assertNotIn((21,32,8),east)
                self.assertIn((23,32,14),north,"Source ownership is corrected without shrinking the original cottage or its overhanging roof")

    def test_north_original_keeps_the_whole_tall_toyland_turret_and_flag(self):
        for stage in range(2):
            north = self.cells(self.name(stage,3,0))
            self.assertIn((35,33,20),north,"The original north layer owns the full upper turret, not four unrecognizable vertical slices")
            self.assertIn((35,32,63),north,"Original paired roof/flag registration must not move to the south source owner")
            for part in range(1,4):
                self.assertNotIn((35,33,20),self.cells(self.name(stage,3,part)))
                self.assertNotIn((35,32,63),self.cells(self.name(stage,3,part)))

    def test_small_fence_has_an_open_original_path_and_the_source_sized_outer_margin(self):
        for climate in range(3):
            small = self.joined(1,climate)
            self.assertIn((6,6,6),small)
            self.assertNotIn((2,2,6),small,"Source fence is inset from the original turf perimeter")
            self.assertNotIn((6,6,7),small,"Pickets are not stretched above the original source height")
            self.assertTrue(all((x,58,z) not in small for x in range(18,24) for z in range(2,7)),
                            "Original path remains physically open, including posts and rails")


if __name__ == "__main__":
    unittest.main()

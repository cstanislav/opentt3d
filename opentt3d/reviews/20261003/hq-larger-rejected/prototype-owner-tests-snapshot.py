"""Larger original HQ source owners; structural gates never approve native fidelity."""
import copy
import json
from pathlib import Path
import unittest

from compile_voxels import compile_catalogue
from original_objects import catalogue
from quality_audit import original_object_layer_model

ROOT = Path(__file__).resolve().parents[2]
CLIMATES = ("temperate","arctic","tropic","toyland")
STAGES = ("medium","large","huge")
PARTS = ("north","west","east","south")


class CompleteHeadquartersOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT/"assets/3d/voxels.json").read_text())
        cls.source["models"] = {name:model for name,model in cls.source["models"].items()
                                if name.startswith(tuple(f"hq_{role}_{stage}_" for role in ("ground","body") for stage in STAGES))}
        cls.source["bindings"] = {category:{layout:states for layout,states in cls.source["bindings"][category].items()
                                            if 12 <= int(layout) < 24} for category in ("object_ground","objects")}
        cls.compiled = compile_catalogue(cls.source)
        cls.original = catalogue()
        cls.occupied = {name:{(x+i,y,z):tuple(cls.compiled["materials"][material-1])
                              for x,y,z,length,material in model["runs"] for i in range(length)}
                        for name,model in cls.compiled["models"].items()}

    def name(self,stage,climate,part,role):
        return f"hq_{role}_{STAGES[stage-2]}_{CLIMATES[climate]}_{PARTS[part]}"

    def joined(self,stage,climate):
        joined = {}
        for role in ("ground","body"):
            for part in range(4 if role == "ground" else 3):
                cells = self.occupied[self.name(stage,climate,part,role)]
                self.assertFalse(joined.keys() & cells.keys(),"Original source owners must not duplicate a physical cell")
                joined.update(cells)
        return joined

    def test_all_three_sizes_have_four_ground_three_body_owners_and_no_south_body(self):
        self.assertEqual(len(self.compiled["models"]),84)
        self.assertEqual(set(self.compiled["bindings"]["object_ground"]),{str(layout) for layout in range(12,24)})
        self.assertEqual(set(self.compiled["bindings"]["objects"]),{str(layout) for layout in range(12,24) if (layout-4)%4 != 3})
        for row in self.original["tiles"]:
            if row["object_id"] != 4 or row["size_stage"] < 2: continue
            for climate in range(4):
                self.assertEqual(original_object_layer_model(self.compiled,self.original,row,"ground",0,climate),
                                 self.name(row["size_stage"],climate,row["part"],"ground"))
                body = original_object_layer_model(self.compiled,self.original,row,"body",0,climate)
                self.assertEqual(body,self.name(row["size_stage"],climate,row["part"],"body") if row["body"] else None)

    def test_source_tile_sequence_registration_and_complete_opaque_ground_contact_are_exact(self):
        for stage in range(2,5):
            for climate in range(4):
                for role in ("ground","body"):
                    for part in range(4 if role == "ground" else 3):
                        name = self.name(stage,climate,part,role);model = self.compiled["models"][name]
                        self.assertEqual(model["cell_size"],[0.5,0.5,0.5])
                        self.assertEqual(model["origin"],[-16*(part%2),-16*(part//2),-0.5])
                        self.assertEqual(self.source["models"][name]["review_status"],"work-in-progress")
                        cells = self.occupied[name]
                        self.assertTrue(cells)
                        if role == "ground":
                            x0,y0 = 32*(part%2),32*(part//2)
                            self.assertEqual({(x,y) for x,y,z in cells if z == 0},
                                             {(x,y) for x in range(x0,x0+32) for y in range(y0,y0+32)})
                            for x,y,z in cells:
                                if stage != 2 or climate == 3:
                                    self.assertGreaterEqual(2*x-z,0)
                                    self.assertGreaterEqual(2*y-z,0)
                                    self.assertEqual(2*x-z >= 64,bool(part%2))
                                    self.assertEqual(2*y-z >= 64,bool(part//2))
                        else:
                            for x,y,z in cells:
                                self.assertTrue(2*x-z < 0 or 2*y-z < 0)
                                self.assertGreater(z,0)
                                if stage != 2 or climate == 3:
                                    self.assertEqual(part,1 if y-x < -32 else 2 if y-x >= 33 else 0)

    def test_seven_owners_are_the_exact_authored_compound_without_resizing_repainting_or_gaps(self):
        for stage in range(2,5):
            for climate in range(4):
                source = copy.deepcopy(self.source)
                name = self.name(stage,climate,0,"ground")
                source["models"] = {"joined":{**source["models"][name],
                                              "ops":[["use",f"hq_{STAGES[stage-2]}_compound_{CLIMATES[climate]}"]]}}
                source["bindings"] = {}
                compiled = compile_catalogue(source)
                expected = {(x+i,y,z):tuple(compiled["materials"][material-1])
                            for x,y,z,length,material in compiled["models"]["joined"]["runs"] for i in range(length)}
                self.assertEqual(self.joined(stage,climate),expected)

    def test_each_missing_ground_or_body_owner_restores_the_whole_original_family(self):
        for stage in range(2,5):
            rows = [row for row in self.original["tiles"] if row["object_id"] == 4 and row["size_stage"] == stage]
            for climate in range(4):
                for category,part in (("object_ground",0),("object_ground",3),("objects",0),("objects",1),("objects",2)):
                    partial = {**self.compiled,"bindings":copy.deepcopy(self.compiled["bindings"])}
                    del partial["bindings"][category][str(4+stage*4+part)][str(climate)]
                    for row in rows:
                        self.assertIsNone(original_object_layer_model(partial,self.original,row,"ground",0,climate))
                        self.assertIsNone(original_object_layer_model(partial,self.original,row,"body",0,climate))
                        other = (climate+1)%4
                        self.assertEqual(original_object_layer_model(partial,self.original,row,"ground",0,other),
                                         self.name(stage,other,row["part"],"ground"))

    def test_ordinary_l_office_shed_upper_storeys_and_low_entrance_wing_keep_real_air(self):
        medium = self.joined(2,0);large = self.joined(3,0);huge = self.joined(4,0)
        self.assertNotIn((20,20,8),medium)
        self.assertNotIn((48,17,7),medium)
        self.assertIn((18,35,10),medium)
        self.assertNotIn((18,36,10),medium,"Glazing remains recessed rather than a painted solid wall")
        self.assertNotIn((30,30,40),large)
        self.assertNotIn((40,20,50),huge)
        self.assertIn((19,31,18),huge)
        self.assertIn((19,36,18),huge,"The huge lower company wing retains its own ground-owned recessed glazing")
        self.assertTrue(all((20,61,z) not in medium and (55,61,z) not in large and (40,61,z) not in huge
                            for z in range(1,7)),"Original perimeter entrances remain physically open")
        self.assertGreater(max(z for x,y,z in huge),max(z for x,y,z in large))
        self.assertGreater(max(z for x,y,z in large),max(z for x,y,z in medium))

    def test_all_three_toyland_castles_are_structurally_distinct_and_hollow(self):
        castles = [self.joined(stage,3) for stage in range(2,5)]
        for first in range(3):
            for second in range(first+1,3):self.assertNotEqual(set(castles[first]),set(castles[second]))
        for castle in castles:
            self.assertNotIn((32,23,30),castle)
            self.assertNotIn((32,59,10),castle,"Curtain-wall entrance remains real air")
        for castle in castles[1:]:
            self.assertNotIn((52,12,20),castle,"Front corner turrets retain a real hollow centre")
            self.assertIn((56,12,20),castle)
        self.assertIn((30,50,147),castles[2],"Huge Toyland adds a distinct tall rear turret/flag, not a stage rename")
        self.assertIn((34,37,122),castles[2],"The original huge castle has a separate intermediate square turret/flag too")
        self.assertNotIn((30,50,110),castles[2],"The tall added turret remains truly hollow below its roof")
        for x,y in ((55,9),(9,55),(55,55)):
            self.assertIn((x,y,36),castles[0],"All three original medium corner flags are physical, including the front flag")

    def test_huge_office_is_the_original_rectangle_and_has_no_square_roof_shortcut(self):
        huge = self.joined(4,0)
        roof = {(x,y) for x,y,z in huge if z == 112 and 14 <= x < 55 and 8 <= y < 36}
        self.assertEqual(roof,{(x,y) for x in range(16,53) for y in range(10,34)})
        self.assertNotEqual(53-16,34-10)
        self.assertIn((19,36,10),huge)
        self.assertNotIn((19,37,10),huge,"The shallow source entrance wing retains its glass recession")

    def test_source_matching_ordinary_bodies_alias_only_identical_original_climate_art(self):
        for stage in range(2,5):
            for part in range(3):
                base = self.occupied[self.name(stage,0,part,"body")]
                for climate in (1,2):self.assertEqual(base,self.occupied[self.name(stage,climate,part,"body")])
            self.assertNotEqual(self.joined(stage,0),self.joined(stage,3))
            self.assertNotEqual(self.joined(stage,0),self.joined(stage,1))
            self.assertNotEqual(self.joined(stage,0),self.joined(stage,2))

    def test_medium_east_body_retains_its_registered_continuous_brick_perimeter(self):
        # Original2614 occupies local native x1..32,y-3..14 at the east tile.
        # The registered XYZ right edge is low-X, high-Y, not the opposite wall.
        # A tiny flag remnant is not source-owner coverage even if the union exists.
        for climate in (0,1,2):
            east = self.occupied[self.name(2,climate,2,"body")]
            for y in range(34,63):
                self.assertIn((1,y,6),east)
            self.assertGreaterEqual(len({y for x,y,z in east if x < 3 and 3 <= z < 7}),29)

    def test_medium_original_north_trim_is_one_diagonal_without_foreign_ground_roof_or_bricks(self):
        for climate in (0,1,2):
            north = self.occupied[self.name(2,climate,0,"body")]
            self.assertEqual(set(north),{(x,13,27) for x in range(14,38)})
            self.assertEqual(set(north.values()),{tuple(self.source["materials"]["hq_office_frame"])})
            ground = self.occupied[self.name(2,climate,0,"ground")]
            self.assertTrue(all((13,y,27) in ground for y in range(14,38)),
                            "The other original roof branch remains real ground-owned volume, not deleted")
            self.assertFalse(north.keys() & ground.keys())

    def test_medium_perimeter_tips_keep_their_own_original_body_not_a_diagonal_partition_remnant(self):
        for climate in (0,1,2):
            west = self.occupied[self.name(2,climate,1,"body")]
            east = self.occupied[self.name(2,climate,2,"body")]
            self.assertEqual(set(west),{(x,y,z) for x in range(61,63) for y in (1,2)
                                        for z in range(2*y+1,7)})
            self.assertEqual(set(east),{(x,y,z) for x in (1,2) for y in range(33,63)
                                        for z in range(2*x+1,7)})

    def test_medium_office_shed_and_flag_each_belong_wholly_to_their_original_ground_layer(self):
        source = copy.deepcopy(self.source)
        source["models"] = {component:{"size":[64,64,48],"cell_size":[0.5,0.5,0.5],"origin":[0,0,-0.5],
                                       "ops":[["use",component]]}
                            for component in ("hq_medium_office","hq_medium_shed","hq_medium_flag")}
        source["bindings"] = {}
        compiled = compile_catalogue(source)
        for part,component in enumerate(("hq_medium_office","hq_medium_shed","hq_medium_flag")):
            expected = {(x+i,y,z):tuple(compiled["materials"][material-1])
                        for x,y,z,length,material in compiled["models"][component]["runs"] for i in range(length) if z > 0}
            if part == 0:
                expected = {p:paint for p,paint in expected.items() if p not in {(x,13,27) for x in range(14,38)}}
            for climate in (0,1,2):
                owner = self.occupied[self.name(2,climate,part,"ground")]
                self.assertEqual({p:owner[p] for p in expected if p in owner},expected)
                for other in range(4):
                    if other != part:
                        self.assertFalse(expected.keys() & self.occupied[self.name(2,climate,other,"ground")].keys(),
                                         "A geometric plane must not assign a foreign architectural fragment to another source ground")

    def test_medium_ground_perimeter_retains_its_source_tile_without_foreign_north_brick_fragments(self):
        source = copy.deepcopy(self.source)
        source["models"] = {"site":{"size":[64,64,48],"cell_size":[0.5,0.5,0.5],"origin":[0,0,-0.5],
                                    "ops":[["use","hq_medium_site"]]}}
        source["bindings"] = {}
        compiled = compile_catalogue(source)
        points = {(x+i,y,z) for x,y,z,length,material in compiled["models"]["site"]["runs"]
                  for i in range(length) if z > 0}
        for climate in (0,1,2):
            bodies = set().union(*(self.occupied[self.name(2,climate,part,"body")].keys() for part in range(3)))
            for x,y,z in points-bodies:
                self.assertIn((x,y,z),self.occupied[self.name(2,climate,(x>=32)+2*(y>=32),"ground")])
            north = self.occupied[self.name(2,climate,0,"ground")]
            self.assertFalse(points & north.keys(),"Original2611 does not own the neighbouring perimeter's lower brick tips")


if __name__ == "__main__":
    unittest.main()

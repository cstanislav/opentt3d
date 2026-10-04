"""Screen independent river relief; these tests cannot establish aesthetic approval."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from compile_voxels import compile_catalogue
from quality_audit import fingerprint


def cells(model):
    return {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}


class RiverReliefStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((HERE / "authored-source.json").read_text())
        cls.compiled = compile_catalogue(cls.source)
        cls.index = json.loads((HERE / "source-index.json").read_text())

    def test_all_eight_actual_sources_are_complete_and_byte_exact(self):
        self.assertEqual(len(self.index),8)
        self.assertEqual({(row["climate"],row["slope"]) for row in self.index},
                         {(climate,slope) for climate in (0,3) for slope in (3,6,9,12)})
        for row in self.index:
            with self.subTest(climate=row["climate"],slope=row["slope"]):
                self.assertEqual(hashlib.sha256((ROOT / row["portable_source"]).read_bytes()).hexdigest(),row["sha256"])
                self.assertTrue(row["complete_uncropped_source"])
                self.assertFalse(row["raised_water_ownership_verified"])
                self.assertFalse(row["geometry_approved"])

    def test_no_runtime_bindings_or_flat_state_inventions(self):
        self.assertEqual(self.source["bindings"],{})
        self.assertEqual(self.compiled["bindings"],{})
        self.assertEqual(set(self.compiled["models"]),
                         {f"river_relief_study_{kind}_{slope}" for kind in ("rock","island") for slope in ("sw","se","nw","ne")})
        for model in self.source["models"].values():
            self.assertEqual(model["review_status"],"unbound-source-study")

    def test_all_observed_climates_keep_their_own_selector_and_no_inherited_approval(self):
        rows = json.loads((HERE / "climate-source-index.json").read_text())
        self.assertEqual(len(rows),20)
        self.assertEqual({(row["climate"],row["slope"]) for row in rows},
                         {(climate,slope) for climate in range(4) for slope in (0,3,6,9,12)})
        self.assertEqual(sum(row["study_model"] is not None for row in rows),16)
        for row in rows:
            self.assertFalse(row["quality_approved"])
            self.assertFalse(row["runtime_bound"])
            self.assertEqual(hashlib.sha256((ROOT / row["portable_source"]).read_bytes()).hexdigest(),row["sha256"])
            self.assertEqual(row["study_model"] is None,row["slope"] == 0)

    def test_relief_has_volume_and_retains_original_tile_units(self):
        for name,model in self.compiled["models"].items():
            with self.subTest(model=name):
                self.assertEqual(model["size"],[64,64,64])
                self.assertEqual(model["cell_size"],[0.25,0.25,0.25])
                self.assertEqual(model["origin"],[0,0,0])
                occupied = cells(model)
                self.assertEqual(len(occupied),model["occupied"])
                self.assertGreater(len(occupied),300)
                self.assertGreater(len({z for x,y,z in occupied}),4)
                self.assertLess(len({(x,y) for x,y,z in occupied}),64*64//2,"No water tile is filled as a relief slab")

    def test_each_original_water_plane_is_unscaled_and_has_no_buried_relief(self):
        for name,model in self.compiled["models"].items():
            slope = name.rsplit("_",1)[1]
            for x,y,z in cells(model):
                plane = 2*z-x if slope == "sw" else 2*z-y if slope == "se" else 2*z+y-64 if slope == "nw" else 2*z+x-64
                self.assertGreaterEqual(plane,0,f"{name} buried cell {(x,y,z)}")

    def test_each_vertical_relief_column_is_connected_not_a_billboard(self):
        for name,model in self.compiled["models"].items():
            columns = {}
            for x,y,z in cells(model): columns.setdefault((x,y),[]).append(z)
            for xy,zs in columns.items():
                self.assertEqual(len(zs),max(zs)-min(zs)+1,f"{name}: floating fragment at {xy}")

    def test_islands_retain_both_wall_colours_and_top_face_only_grass(self):
        for name,model in self.compiled["models"].items():
            if "_island_" not in name: continue
            painted = [self.compiled["materials"][material-1] for material in cells(model).values()]
            self.assertTrue(any(50 in colours[:4] for colours in painted))
            self.assertTrue(any(13 in colours[:4] for colours in painted))
            self.assertTrue(all(colours[5] in (83,84) for colours in painted))
            self.assertTrue(all(83 not in colours[:5] and 84 not in colours[:5] for colours in painted))

    def test_rock_counts_are_inspected_per_source_not_copied_from_a_rotation(self):
        for slope,count in (("sw",6),("se",6),("nw",6),("ne",5)):
            ops = self.source["models"]["river_relief_study_rock_"+slope]["ops"]
            self.assertEqual(sum(op[0] == "hull" for op in ops),count)
        self.assertEqual(len({fingerprint(model,self.compiled["materials"]) for model in self.compiled["models"].values()}),8)

    def test_no_independent_water_foam_company_or_light_animation_is_baked_into_relief(self):
        used = {colour for material in self.compiled["materials"] for colour in material}
        self.assertFalse(used & set(range(215,256)))

    def test_fine_paint_does_not_inflate_source_silhouettes(self):
        before = copy.deepcopy(self.source)
        for model in before["models"].values():
            model["ops"] = [op for op in model["ops"] if op[0] not in ("face_paint","scatter_paint")]
        unpainted = compile_catalogue(before)
        for name,model in self.compiled["models"].items():
            self.assertEqual(cells(model).keys(),cells(unpainted["models"][name]).keys())


if __name__ == "__main__":
    unittest.main()

"""Structural checks for all separate original-datum sloped bank owners; not approval."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent / "river-relief-ownership/approved-compiler-snapshot.py"
spec = importlib.util.spec_from_file_location("approved_sloped_bank_compiler",COMPILER)
compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)


def cells(model,materials):
    return {(x,y,z):tuple(materials[material-1]) for start,y,z,length,material in model["runs"] for x in range(start,start+length)}


class SlopedBankStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((HERE / "authored-source.json").read_text())
        cls.compiled = compiler.compile_catalogue(cls.source)
        cls.sources = json.loads((HERE / "actual-source-index.json").read_text())

    def test_all_four_original_planes_keep_two_separate_owners_per_climate(self):
        self.assertEqual(len(self.compiled["models"]),32)
        self.assertEqual(self.compiled["bindings"],{})
        self.assertEqual({(row["climate"],row["slope"],row["edge"]) for row in self.sources},
            {(climate,slope,edge) for climate in range(4) for slope,edges in ((3,(1,3)),(6,(0,2)),(9,(0,2)),(12,(1,3))) for edge in edges})
        for name,model in self.compiled["models"].items():
            self.assertEqual(model["size"],[64,64,36],name)
            self.assertEqual(model["cell_size"],[0.25,0.25,0.25],name)
            self.assertEqual(model["origin"],[0,0,0],name)

    def test_original_plane_rise_is_not_doubled_and_every_bank_column_is_solid_and_thin(self):
        for row in self.sources:
            label = ("temperate","arctic","tropic","toyland")[row["climate"]]
            name = f"river_bank_slope_study_{label}_{row['direction']}_edge{row['edge']:02d}"
            occupied = cells(self.compiled["models"][name],self.compiled["materials"])
            columns = {}
            for x,y,z in occupied: columns.setdefault((x,y),[]).append(z)
            for (x,y),zs in columns.items():
                t = x if row["slope"] in (3,12) else y
                bottom = (t+1)//2 if row["slope"] in (3,6) else 32-(t+1)//2
                self.assertEqual(min(zs),bottom,(name,x,y))
                self.assertEqual(sorted(zs),list(range(bottom,bottom+len(zs))),(name,x,y))
                self.assertIn(len(zs),(1,2,4),(name,x,y))
                self.assertFalse(12 <= x < 52 and 12 <= y < 52,(name,x,y))
            self.assertEqual(max(z for x,y,z in occupied),35,name)

    def test_paint_only_detail_never_supplies_bank_occupancy(self):
        for name,model in self.source["models"].items():
            bare = compiler.compile_catalogue({**self.source,"models":{name:{**model,"ops":[op for op in model["ops"] if op[0] == "prism"]}}})
            self.assertEqual(cells(bare["models"][name],bare["materials"]).keys(),cells(self.compiled["models"][name],self.compiled["materials"]).keys(),name)
            self.assertEqual({op[0] for op in model["ops"]}-{ "prism" },{"scatter_paint","face_paint"} if "toyland" in name else {"scatter_paint"},name)

    def test_wave_fringes_and_unobserved_slots_never_become_voxel_water_or_invented_absence(self):
        for name,material in self.source["materials"].items():
            self.assertFalse(any(245 <= colour <= 254 for colour in material),name)
        inventory = json.loads((HERE / "complete-conditional-family-inventory.json").read_text())
        self.assertEqual(inventory["source_states"],{"elevated":26,"sea-level-observation":6})
        self.assertEqual(sum(row["sloped_slot_unobserved_in_this_increment"] for row in inventory["states"]),160)
        self.assertTrue(all(not row["runtime_source_coverage_accepted"] and not row["quality_approved"] for row in inventory["states"]))
        for row in self.sources:
            self.assertEqual(hashlib.sha256((HERE.parents[3] / row["source_pam"]).read_bytes()).hexdigest(),row["source_pam_sha256"])


if __name__ == "__main__": unittest.main()

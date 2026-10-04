"""Every snowy bank keeps real occupied columns, original datum and independent paint."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location("approved_snow_bank_compiler",HERE.parent / "river-relief-ownership/approved-compiler-snapshot.py")
compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)


def cells(model,materials):
    return {(x,y,z):tuple(materials[material-1]) for start,y,z,length,material in model["runs"] for x in range(start,start+length)}


class SnowBankStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((HERE / "authored-source.json").read_text())
        cls.compiled = compiler.compile_catalogue(cls.source)
        cls.sources = json.loads((HERE / "actual-source-index.json").read_text())

    def test_all_twenty_actual_snow_paint_owners_are_separate_and_unbound(self):
        self.assertEqual(len(self.compiled["models"]),20)
        self.assertEqual(self.compiled["bindings"],{})
        self.assertEqual(Counter(row["slope"] for row in self.sources),{0:12,3:2,6:2,9:2,12:2})
        for row in self.sources:
            self.assertEqual(row["requested_offset"],row["resolved_offset"])
            self.assertGreater(row["source_height"],0)
            self.assertFalse(row["absent"] or row["quality_approved"] or row["public_terrain_type_query_performed"])
            self.assertEqual(hashlib.sha256((ROOT / row["source_pam"]).read_bytes()).hexdigest(),row["source_pam_sha256"])

    def test_both_snowy_corner_arms_remain_solid_with_a_clear_water_centre(self):
        for offset in range(12):
            name = f"river_bank_snow_study_arctic_offset{offset:02d}"; model = self.compiled["models"][name]
            occupied = cells(model,self.compiled["materials"]); columns = {}
            self.assertEqual(model["size"],[64,64,4])
            for x,y,z in occupied:
                columns.setdefault((x,y),[]).append(z)
                self.assertFalse(24 <= x < 40 and 24 <= y < 40,(name,x,y))
            for (x,y),zs in columns.items(): self.assertEqual(sorted(zs),list(range(len(zs))),(name,x,y))
            self.assertEqual(max(z for x,y,z in occupied),3,name)
            if 4 <= offset < 8:
                self.assertGreater(max(x for x,y,z in occupied)-min(x for x,y,z in occupied),15,name)
                self.assertGreater(max(y for x,y,z in occupied)-min(y for x,y,z in occupied),15,name)

    def test_original_planes_never_double_bank_thickness(self):
        for source in self.sources:
            if source["slope"] == 0: continue
            name = f"river_bank_snow_study_arctic_offset{source['requested_offset']:02d}"; model = self.compiled["models"][name]
            self.assertEqual(model["size"],[64,64,36]); columns = {}
            for x,y,z in cells(model,self.compiled["materials"]): columns.setdefault((x,y),[]).append(z)
            for (x,y),zs in columns.items():
                t = x if source["slope"] in (3,12) else y
                low = (t+1)//2 if source["slope"] in (3,6) else 32-(t+1)//2
                self.assertEqual(sorted(zs),list(range(low,low+len(zs))),(name,x,y))
                self.assertIn(len(zs),(1,2,4),(name,x,y))
                self.assertFalse(12 <= x < 52 and 12 <= y < 52,(name,x,y))

    def test_snow_soil_detail_only_paints_real_occupied_cells(self):
        for name,model in self.source["models"].items():
            bare = compiler.compile_catalogue({**self.source,"models":{name:{**model,"ops":[op for op in model["ops"] if op[0] == "prism"]}}})
            self.assertEqual(cells(bare["models"][name],bare["materials"]).keys(),cells(self.compiled["models"][name],self.compiled["materials"]).keys(),name)
            self.assertTrue(all(op[0] in ("prism","scatter_paint") for op in model["ops"]))
            self.assertEqual(model["origin"],[0,0,0]); self.assertEqual(model["cell_size"],[0.25,0.25,0.25])
        self.assertTrue(all(not 245 <= colour <= 254 for material in self.source["materials"].values() for colour in material))


if __name__ == "__main__": unittest.main()

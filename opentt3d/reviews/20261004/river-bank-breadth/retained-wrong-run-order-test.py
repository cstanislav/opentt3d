"""Screen small bank ownership without inferring source/runtime/aesthetic acceptance."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location("approved_bank_compiler",ROOT / "opentt3d/reviews/20261004/river-relief-ownership/approved-compiler-snapshot.py")
compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)


class FlatBankStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((HERE / "authored-source.json").read_text())
        cls.compiled = compiler.compile_catalogue(cls.source)

    def test_every_flat_owner_and_climate_is_a_separate_unbound_model(self):
        self.assertEqual(self.compiled["bindings"],{})
        expected = {f"river_bank_study_{climate}_flat_{edge:02d}" for climate in ("temperate","arctic","tropic","toyland") for edge in range(12)}
        self.assertEqual(set(self.compiled["models"]),expected)

    def test_all_occupied_cells_are_small_solid_strata_and_leave_water_centre_empty(self):
        for name,model in self.compiled["models"].items():
            self.assertEqual(model["size"],[64,64,4]); self.assertEqual(model["origin"],[0,0,0])
            self.assertEqual(model["cell_size"],[0.25,0.25,0.25])
            cells = {(x,y,z) for y,z,start,length,material in model["runs"] for x in range(start,start+length)}
            self.assertTrue(cells,name)
            self.assertFalse(any(12 <= x < 52 and 12 <= y < 52 for x,y,z in cells),name)
            columns = {(x,y) for x,y,z in cells}
            self.assertTrue(all((x,y,z) in cells for x,y in columns for z in range(4)),name)

    def test_no_water_palette_or_source_image_can_supply_geometry(self):
        self.assertTrue(all(value < 245 for material in self.compiled["materials"] for value in material))
        allowed = {"prism","scatter_paint","face_paint"}
        for model in self.source["models"].values(): self.assertTrue(all(op[0] in allowed for op in model["ops"]))

    def test_paint_only_detail_preserves_footprint_and_height(self):
        for name,model in self.source["models"].items():
            data = {**self.source,"models":{name:{**model,"ops":model["ops"][:2]}}}
            plain = compiler.compile_catalogue(data)["models"][name]
            occupied = lambda value:{(x,y,z) for y,z,start,length,material in value["runs"] for x in range(start,start+length)}
            self.assertEqual(occupied(plain),occupied(self.compiled["models"][name]),name)


if __name__ == "__main__": unittest.main()

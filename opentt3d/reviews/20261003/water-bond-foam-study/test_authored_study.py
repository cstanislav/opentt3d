"""Structural source-study regressions do not approve locks or runtime coverage."""
import json
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from compile_voxels import compile_catalogue
from quality_audit import fingerprint


class LockStoneAndFoamStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((HERE / "authored-source.json").read_text())
        cls.prior_source = json.loads((HERE / "before-authored-source.json").read_text())
        cls.compiled = compile_catalogue(cls.source)
        cls.prior = compile_catalogue(cls.prior_source)
        cls.cells = {name: {(x+i,y,z):tuple(cls.compiled["materials"][material-1])
                            for x,y,z,length,material in model["runs"] for i in range(length)}
                     for name,model in cls.compiled["models"].items()}
        cls.before = {name: {(x+i,y,z):tuple(cls.prior["materials"][material-1])
                             for x,y,z,length,material in model["runs"] for i in range(length)}
                      for name,model in cls.prior["models"].items()}

    def test_all48_independent_unbound_owners_keep_their_names_origins_and_cell_scale(self):
        self.assertEqual(self.compiled["models"].keys(),self.prior["models"].keys())
        self.assertEqual(len(self.cells),48)
        self.assertEqual(self.source["bindings"],{})
        for name,model in self.compiled["models"].items():
            self.assertEqual(model["origin"],self.prior["models"][name]["origin"])
            self.assertEqual(model["cell_size"],[0.25]*3)
            self.assertNotEqual(fingerprint(model,self.compiled["materials"]),
                                fingerprint(self.prior["models"][name],self.prior["materials"]))

    def test_face_detail_and_lantern_paint_do_not_inflate_walls_rails_openings_or_registration(self):
        for name,cells in self.cells.items():
            with self.subTest(name=name):
                self.assertEqual({point for point,paint in cells.items() if paint != (252,)*6},
                                 {point for point,paint in self.before[name].items() if paint != (252,)*6})
                before_height = max(point[2] for point in self.before[name])
                self.assertEqual(max(point[2] for point in cells),before_height)
                expected_size = list(self.prior["models"][name]["size"])
                axis = 0 if "_ne_" in name or "_sw_" in name else 1
                if "_lower_" in name and "_front_" in name and name.endswith("_sea"):
                    expected_size[1-axis] += 1
                self.assertEqual(self.compiled["models"][name]["size"],expected_size)

    def test_foam_has_exact_explicit_directional_ownership_and_keeps_elevated_absences(self):
        for name,cells in self.cells.items():
            axis = 0 if "_ne_" in name or "_sw_" in name else 1
            points = {(point[axis],point[1-axis],point[2]) for point,paint in cells.items() if paint == (252,)*6}
            expected = set()
            if "_lower_" in name and name.endswith("_sea"):
                far = "_ne_" in name or "_nw_" in name
                if "_front_" in name:
                    expected = {(x,12,0) for x in range(4,68)}
                    expected |= {(68 if far else 3,y,0) for y in range(2,13)}
                elif far:
                    expected = {(68,y,0) for y in range(2,12)}
            self.assertEqual(points,expected,name)
            if "_rear_" in name:
                self.assertFalse(any(4 <= x < 68 for x,y,z in points),"A rear source does not justify hidden full-length foam")

    def test_lamps_retain_all_four_open_glazed_sides_and_original_sea_only_selection(self):
        for name,cells in self.cells.items():
            glass = {point for point,paint in cells.items() if set(paint) <= {65,66,67}}
            lower_sea = "_lower_" in name and name.endswith("_sea")
            self.assertEqual(bool(glass),lower_sea,name)
            if not lower_sea:
                continue
            axis = 0 if "_ne_" in name or "_sw_" in name else 1
            lamp_x = 68 if "_ne_" in name or "_nw_" in name else 4
            point = lambda x,y,z: (x,y,z) if axis == 0 else (y,x,z)
            self.assertIn(point(lamp_x,2,78),glass)
            for x,y in ((lamp_x,1),(lamp_x,6),(lamp_x-3,3),(lamp_x+2,3)):
                self.assertNotIn(point(x,y,78),cells,"The pane is not hidden behind an opaque lamp shell")

    def test_every_source_stone_bond_is_face_paint_not_a_solid_or_image_extrusion(self):
        def kinds(ops):
            for op in ops:
                yield op[0]
                if op[0] == "repeat":
                    yield from kinds(op[3])
        for name,ops in self.source["components"].items():
            if "bond" in name or "joints" in name:
                self.assertEqual(set(kinds(ops)),{"repeat","face_paint"})
        for name,cells in self.cells.items():
            axis = 0 if "_ne_" in name or "_sw_" in name else 1
            front = "_front_" in name
            rail_y = 6 if front else 2
            rail_base = 9 if "_upper_" in name else 41
            point = (7,rail_y,rail_base+8) if axis == 0 else (rail_y,7,rail_base+8)
            self.assertNotIn(point,cells,"Fine detail must not fill the original guard openings")


if __name__ == "__main__":
    unittest.main()

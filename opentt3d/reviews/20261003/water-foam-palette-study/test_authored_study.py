"""Source-palette/foam regressions do not approve geometry, phases or runtime coverage."""
import json
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compile_voxels import compile_catalogue
from quality_audit import fingerprint


class FoamPaletteStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((HERE / "authored-source.json").read_text())
        cls.before_source = json.loads((HERE / "before-authored-source.json").read_text())
        cls.current = compile_catalogue(cls.source)
        cls.before = compile_catalogue(cls.before_source)
        def cells(catalogue):
            return {name:{(x+i,y,z):tuple(catalogue["materials"][material-1])
                         for x,y,z,length,material in model["runs"] for i in range(length)}
                    for name,model in catalogue["models"].items()}
        cls.cells,cls.before_cells = cells(cls.current),cells(cls.before)

    def test_six_source_owned_foam_models_change_and_forty_two_models_keep_exact_fingerprints(self):
        changed = {name for name,model in self.current["models"].items()
                   if fingerprint(model,self.current["materials"]) != fingerprint(self.before["models"][name],self.before["materials"])}
        self.assertEqual(changed,{f"lock_study_lower_{direction}_{face}_sea" for direction,faces in
                                 (("ne",("rear","front")),("nw",("rear","front")),("sw",("front",)),("se",("front",))) for face in faces})
        self.assertEqual(len(self.current["models"])-len(changed),42)
        self.assertEqual(self.source["bindings"],{})

    def test_every_nonfoam_cell_face_colour_anchor_and_height_is_word_exact(self):
        for name,cells in self.cells.items():
            self.assertEqual({point:paint for point,paint in cells.items() if paint != (250,)*6},
                             {point:paint for point,paint in self.before_cells[name].items() if paint != (252,)*6},name)
            self.assertEqual(self.current["models"][name]["origin"],self.before["models"][name]["origin"])
            self.assertEqual(self.current["models"][name]["cell_size"],[0.25]*3)
            self.assertEqual(max(z for x,y,z in cells),max(z for x,y,z in self.before_cells[name]))

    def test_directional_half_unit_foam_width_keeps_all_original_accessory_absences(self):
        for name,cells in self.cells.items():
            axis = 0 if "_ne_" in name or "_sw_" in name else 1
            points = {(point[axis],point[1-axis],point[2]) for point,paint in cells.items() if paint == (250,)*6}
            expected = set()
            if "_lower_" in name and name.endswith("_sea"):
                far = "_ne_" in name or "_nw_" in name
                if "_front_" in name:
                    expected = {(x,y,0) for x in range(4,68) for y in range(12,14)}
                    expected |= {(x,y,0) for x in (range(68,70) if far else range(2,4)) for y in range(2,14)}
                elif far:
                    expected = {(x,y,0) for x in range(68,70) for y in range(2,12)}
            self.assertEqual(points,expected,name)
            expected_size = list(self.before["models"][name]["size"])
            if "_lower_" in name and "_front_" in name and name.endswith("_sea"):
                expected_size[1-axis] += 1
            self.assertEqual(self.current["models"][name]["size"],expected_size)

    def test_foam_remains_original_animated_glitter_palette_not_static_white(self):
        self.assertEqual(self.source["materials"]["lock_foam"],250)
        palette = (ROOT / "src/table/palettes.h").read_text()
        self.assertIn("EPV_CYCLES_GLITTER_WATER = 15",palette)
        block = palette.split("/* glittery water */",1)[1].split("/* glittery water Toyland */",1)[0]
        values = [tuple(map(int,colour)) for colour in re.findall(r"M\(\s*(\d+),\s*(\d+),\s*(\d+)\)",block)]
        self.assertEqual(values[0],(216,244,252))
        self.assertEqual(values[6],(72,100,144))
        animation = (ROOT / "src/palette.cpp").read_text()
        self.assertIn("palette_animation_counter = 0;",animation)
        self.assertIn("j += 3;",animation)
        # Actual full original lower-sea sources retained the pale first glitter
        # colour at the nonanimated32bpp baseline. Do not treat this one phase as
        # full animation acceptance, or freeze that RGB into authored materials.
        def pixels(path):
            data = path.read_bytes();header,rgba = data.split(b"ENDHDR\n",1)
            return {tuple(rgba[i:i+4]) for i in range(0,len(rgba),4)}
        rows = json.loads((ROOT / "opentt3d/reviews/20261003/water-live-selectors/breadth-original-lock-live-source-verification.json").read_text())["selected_sources"]["temperate"]["bodies"]
        files = {row["sha256"]:ROOT / row["portable_image"] for row in
                 json.loads((ROOT / "opentt3d/reviews/20261003/water-live-selectors/source-file-map.json").read_text())}
        count = 0
        for row in rows:
            if row["part"] == 1 and row["elevation"] == 0 and (row["face"] == "front" or row["direction"] in (0,3)):
                self.assertIn((216,244,252,255),pixels(files[row["source"]["source_image_sha256"]]))
                count += 1
        self.assertEqual(count,6)


if __name__ == "__main__":
    unittest.main()

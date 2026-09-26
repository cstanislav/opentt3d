"""Runtime-pack validation before invalid materials reach the GPU/caches."""

import copy
import json
from pathlib import Path
import unittest
from validate_models import validate


class RuntimeModelTests(unittest.TestCase):
    def setUp(self):
        self.tree = {
            "tree_materials": {"wood_colour": [0.4, 0.3, 0.2], "foliage_crop": [0.2, 0.2, 0.6, 0.5]},
            "parts": [["wood", [["branch", [[0, 0, 0, 0.5], [0, 0, 20, 0.02]]]]],
                      ["foliage", [["crown", 0, 0, 5, 3, 3, 15, 1.2]]]],
        }
        self.pack = {"format": 2, "models": {"1576": self.tree}, "aliases": {}}

    def test_editable_packs(self):
        root = Path(__file__).resolve().parents[2] / "assets/3d"
        for name in ("houses", "trees", "industries"):
            with self.subTest(pack=name):
                validate(json.loads((root / f"{name}.json").read_text()))

    def test_crop_cannot_sample_outside_or_collapse(self):
        for region in ([-0.1, 0, 1, 1], [0.8, 0, 0.3, 1], [0, 0.5, 1, 0.5], [0, 0, 1, float("inf")]):
            with self.subTest(region=region), self.assertRaises(ValueError):
                self.tree["tree_materials"]["foliage_crop"] = region
                validate(self.pack)

    def test_all_seven_stages_have_valid_material_options(self):
        for key, value in (("growth", [1]*6), ("growth", [1]*6+[0]), ("scale", [1, 0]),
                           ("repeat", [float("inf"), 4]), ("retain_dead_foliage", "false"),
                           ("foliage_crop_by_stage", {"7": [0, 0, 1, 1]})):
            pack = copy.deepcopy(self.pack)
            pack["models"]["1576"]["tree_materials"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(pack)

    def test_bare_state_requires_real_wood(self):
        self.tree["parts"] = self.tree["parts"][1:]
        with self.assertRaises(ValueError):
            validate(self.pack)

    def test_degenerate_branch_rejected(self):
        for points in ([[0, 0, 0, 0.5]], [[0, 0, 0, 0.5], [0, 0, 0, 0.2]],
                       [[0, 0, 0, 0.5], [0, 0, 10, -0.1]]):
            self.tree["parts"][0][1][0][1] = points
            with self.subTest(points=points), self.assertRaises(ValueError):
                validate(self.pack)

    def test_snow_alias_resolves_a_component_model(self):
        self.pack["aliases"]["1765"] = {"model": 1576, "wood_colour": [0.8, 0.9, 0.9]}
        validate(self.pack)
        self.pack["aliases"]["1765"]["model"] = 1765
        with self.assertRaises(ValueError):
            validate(self.pack)


if __name__ == "__main__":
    unittest.main()

import unittest

from compile_voxels import compile_catalogue


def source():
    return {
        "format": 1,
        "materials": {"soil": [2, 3, 4, 5, 6, 7], "grass": [8, 9, 10, 11, 12, 13]},
        "components": {},
        "models": {
            "bank": {
                "size": [4, 4, 2],
                "cell_size": [0.25, 0.25, 0.25],
                "origin": [0, 0, 0],
                "ops": [["box", "soil", 0, 0, 0, 4, 4, 1],
                        ["box", "grass", 0, 0, 1, 4, 4, 2]],
            },
            "bank_toy": {
                "size": [4, 4, 2],
                "cell_size": [0.25, 0.25, 0.25],
                "origin": [0, 0, 0],
                "ops": [["box", "grass", 0, 0, 0, 4, 4, 2]],
            },
        },
        "bindings": {
            "river_bank": {
                str(offset): {str(climate): "bank_toy" if climate == 3 else "bank" for climate in range(4)}
                for offset in range(12)
            }
        },
    }


class RiverBankBindingsTests(unittest.TestCase):
    def test_all_twelve_offsets_and_four_climates_stay_separate(self):
        compiled = compile_catalogue(source())
        self.assertEqual(len(compiled["bindings"]["river_bank"]), 12)
        self.assertEqual(sum(len(states) for states in compiled["bindings"]["river_bank"].values()), 48)
        self.assertEqual(compiled["bindings"]["river_bank"]["11"]["3"], "bank_toy")

    def test_foreign_offset_and_climate_are_rejected(self):
        changed = source()
        changed["bindings"]["river_bank"]["12"] = {"0": "bank"}
        with self.assertRaises(ValueError):
            compile_catalogue(changed)
        changed = source()
        changed["bindings"]["river_bank"]["0"]["4"] = "bank"
        with self.assertRaises(ValueError):
            compile_catalogue(changed)

    def test_partial_family_is_retained_for_runtime_fallback(self):
        changed = source()
        del changed["bindings"]["river_bank"]["7"]["2"]
        compiled = compile_catalogue(changed)
        self.assertEqual(sum(len(states) for states in compiled["bindings"]["river_bank"].values()), 47)


if __name__ == "__main__":
    unittest.main()

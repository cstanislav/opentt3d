"""Original lock ordinals must not alias independent source or climate owners."""
import copy
import unittest

from compile_voxels import compile_catalogue


class LockBindingTests(unittest.TestCase):
    def source(self):
        return {"format": 1, "materials": {"stone": 7},
                "models": {"wall": {"size": [2, 2, 2], "ops": [["box", "stone", 0, 0, 0, 2, 2, 2]]}},
                "bindings": {"lock_walls": {str(owner): {str(climate): "wall" for climate in range(4)}
                                             for owner in range(48)}}}

    def test_all48_original_ordinals_have_explicit_climates_without_source_mutation(self):
        source = self.source()
        before = copy.deepcopy(source)
        compiled = compile_catalogue(source)
        self.assertEqual(compiled["bindings"]["lock_walls"], source["bindings"]["lock_walls"])
        self.assertEqual(source, before)

    def test_foreign_ordinals_and_climate_states_are_rejected(self):
        for owner, state in (("48", "0"), ("0", "4"), ("0", "-1"), ("-1", "0")):
            source = self.source()
            source["bindings"] = {"lock_walls": {owner: {state: "wall"}}}
            with self.assertRaises(ValueError):
                compile_catalogue(source)

    def test_partial_family_is_preserved_for_runtime_complete_family_fallback(self):
        source = self.source()
        source["bindings"]["lock_walls"].pop("17")
        compiled = compile_catalogue(source)
        self.assertNotIn("17", compiled["bindings"]["lock_walls"])
        self.assertEqual(len(compiled["bindings"]["lock_walls"]), 47)


if __name__ == "__main__":
    unittest.main()

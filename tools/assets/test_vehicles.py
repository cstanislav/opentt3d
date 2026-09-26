"""Validate complete bindings and upstream direction/cargo metadata independently."""
import copy
import json
import unittest
from compile_vehicles import ROOT, compile_catalogue, definitions


class VehicleCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT / "assets/3d/vehicles.json").read_text())

    def test_all_vanilla_engines_have_explicit_geometry(self):
        result = compile_catalogue(self.source)["models"]
        self.assertEqual(set(result), {str(i) for i in range(256)})
        self.assertTrue(all(value["parts"] for value in result.values()))
        self.assertEqual(result["0"]["assembly"], "tank_steam")
        self.assertEqual(result["208"]["assembly"], "hovercraft")
        self.assertEqual(result["253"]["assembly"], "helicopter")

    def test_direction_and_cargo_follow_original_tables(self):
        source = definitions()
        self.assertEqual(source["27"]["sprites"], [0xAAD, 0xAAE, 0xAAF, 0xAB0] * 2)
        self.assertEqual(source["29"]["loaded_sprites"], [sprite + 44 for sprite in source["29"]["sprites"]])
        self.assertEqual(source["204"]["sprites"], list(range(0xE55, 0xE5D)))
        self.assertEqual(source["215"]["sprites"], list(range(0xEBD, 0xEC5)))

    def test_missing_or_duplicate_bindings_are_rejected(self):
        missing = copy.deepcopy(self.source)
        missing["bindings"].pop()
        with self.assertRaisesRegex(ValueError, "Unbound"):
            compile_catalogue(missing)
        duplicate = copy.deepcopy(self.source)
        duplicate["bindings"].append(duplicate["bindings"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compile_catalogue(duplicate)

    def test_cyclic_assemblies_are_rejected(self):
        self.source["assemblies"]["rail_chassis"]["extends"] = ["tank_steam"]
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            compile_catalogue(self.source)


if __name__ == "__main__":
    unittest.main()

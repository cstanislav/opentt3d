"""River relief bindings cannot invent flat decoration or share climate approval."""
import copy
import unittest

from compile_voxels import compile_catalogue
from original_water import ROOT


class RiverReliefBindingTests(unittest.TestCase):
    def source(self):
        return {"format":1,"materials":{"rock":7},"models":{
            "study":{"size":[2,2,2],"ops":[["box","rock",0,0,0,2,2,2]]}},
            "bindings":{"river_relief":{str(slope):{str(climate):"study" for climate in range(4)}
                                          for slope in (3,6,9,12)}}}

    def test_all_four_slopes_and_climates_stay_separate_without_source_mutation(self):
        source = self.source(); before = copy.deepcopy(source)
        compiled = compile_catalogue(source)
        self.assertEqual(source,before)
        self.assertEqual(compiled["bindings"],source["bindings"])
        self.assertEqual(sum(len(states) for states in compiled["bindings"]["river_relief"].values()),16)

    def test_flat_foreign_slope_and_climate_states_are_rejected(self):
        for slope,state in (("0","0"),("1","0"),("15","0"),("3","4"),("3","-1"),("-1","0")):
            source = self.source(); source["bindings"] = {"river_relief":{slope:{state:"study"}}}
            with self.subTest(slope=slope,state=state), self.assertRaises(ValueError): compile_catalogue(source)

    def test_partial_family_remains_partial_for_complete_original_runtime_fallback(self):
        source = self.source(); del source["bindings"]["river_relief"]["9"]["2"]
        compiled = compile_catalogue(source)
        self.assertNotIn("2",compiled["bindings"]["river_relief"]["9"])
        self.assertEqual(sum(len(states) for states in compiled["bindings"]["river_relief"].values()),15)

    def test_runtime_selector_capture_is_separate_from_default_off_source_tracing(self):
        capture = (ROOT / "src/renderer3d/world_capture.cpp").read_text()
        runtime = capture.split("void CaptureOriginalRiverSelector(",1)[1].split("bool BeginVoxelLockCapture(",1)[0]
        observer = capture.split("void ObserveRiverSelector(",1)[1].split("void CaptureOriginalRiverSelector(",1)[0]
        self.assertIn("!WaterSourceTracingEnabled()",observer)
        self.assertIn("RetainRiverSelector",observer)
        self.assertNotIn("river_ground =",observer)
        self.assertIn("capture->river_ground = selector",runtime)
        self.assertNotIn("RetainRiverSelector",runtime)
        self.assertNotIn("WaterSourceTracingEnabled",runtime)
        for name in ("GetCanalSprite", "GetCanalSpriteOffset", "Random", "InteractiveRandom", "ExportSpriteReference"):
            self.assertNotIn(name+"(",runtime)


if __name__ == "__main__": unittest.main()

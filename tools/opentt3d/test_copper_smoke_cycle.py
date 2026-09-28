import unittest

from copper_smoke_cycle import audit, SOURCES


class CopperSmokeCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    def line(self, frame, progress, vehicle=0):
        rise = progress//4-3
        return f"voxel effect frame {frame} vehicle {vehicle} type 11 sprite {2040+(progress-4)//16} climate 2 animation 0,0 progress {progress} raw 166,166,{59+rise} origin 166,166,{75+rise} opacity 1 pick 0"

    def test_original_industry_first_tick_and_ordered_lifetime(self):
        lines = [self.line(i,progress) for i,progress in enumerate(range(13,84))]
        report = audit("\n".join(lines),*self.sources)
        self.assertEqual(report["complete_presented_lifetimes"],1)
        self.assertEqual(report["observed_source_sprites"],list(range(2040,2045)))
        self.assertEqual(report["lifetimes"][0]["anchor"],(166,166,59))
        self.assertEqual(audit("\n".join(lines[1:]),*self.sources)["complete_presented_lifetimes"],0)
        sparse = audit("\n".join(lines[i] for i in (0,7,23,39,55,70)),*self.sources)
        self.assertEqual(sparse["observed_source_sprites"],list(range(2040,2045)))
        self.assertEqual(sparse["complete_presented_lifetimes"],0)
        with self.assertRaisesRegex(ValueError,"five-frame lifetime"):
            audit(self.line(0,84),*self.sources)

    def test_rise_placement_and_visibility_reject_corruption(self):
        line = self.line(0,16)
        for corrupt in (line.replace("sprite 2040","sprite 2041"),line.replace("climate 2","climate 1"),
                        line.replace("origin 166,166,76","origin 166,166,77"),line.replace("opacity 1","opacity 0.38"),
                        line.replace("pick 0","pick 6"),line.replace("166,166","167,166")):
            with self.assertRaises(ValueError):
                audit(corrupt,*self.sources)
        with self.assertRaisesRegex(ValueError,"conflicting"):
            audit(line+"\n"+self.line(0,17),*self.sources)
        with self.assertRaisesRegex(ValueError,"rise anchor"):
            audit(line+"\n"+self.line(1,17).replace("166,166","182,166"),*self.sources)

    def test_reused_ids_and_uncaptured_gaps_are_separate(self):
        reset = audit(self.line(0,83)+"\n"+self.line(10,13),*self.sources)
        self.assertEqual(len(reset["lifetimes"]),2)
        self.assertEqual(reset["complete_presented_lifetimes"],0)
        moved = self.line(10,20).replace("166,166","182,166")
        self.assertIn("ambiguous",audit(self.line(0,13)+"\n"+moved,*self.sources)["lifetimes"][1]["boundary"])
        sources = list(self.sources)
        sources[2] = sources[2].replace("RunTileLoop();\n\t\tCallVehicleTicks();","CallVehicleTicks();\n\t\tRunTileLoop();")
        with self.assertRaisesRegex(ValueError,"tick order"):
            audit(self.line(0,13),*sources)


if __name__ == "__main__":
    unittest.main()

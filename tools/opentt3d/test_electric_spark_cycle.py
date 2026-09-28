import unittest

from electric_spark_cycle import audit, SOURCES


class ElectricSparkCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    def line(self, frame, sprite=3084, progress=1, vehicle=0):
        return f"voxel effect frame {frame} vehicle {vehicle} type 3 sprite {sprite} climate 0 animation 0,0 progress {progress} raw 160,160,42 origin 160,160,74 opacity 1 pick 0"

    def lifetime(self):
        phases = [(3084,1),(3084,2)]
        phases += [(sprite,progress) for sprite in (3085,3086,3087,3088,3089) for progress in (0,1,2)]
        return [self.line(i,sprite,progress) for i,(sprite,progress) in enumerate(phases)]

    def test_original_lifetime_preserves_both_source_identical_final_frames(self):
        lines = self.lifetime()
        report = audit("\n".join(lines),*self.sources,1)
        self.assertEqual(report["complete_presented_lifetimes"],1)
        self.assertEqual(report["observed_source_sprites"],list(range(3084,3090)))
        self.assertEqual(report["lifetimes"][0]["longest_phase_run"],17)
        # Aliasing the art does not alias the original animation's last sprite.
        shortened = audit("\n".join(lines[:-3]),*self.sources,1)
        self.assertEqual(shortened["complete_presented_lifetimes"],0)
        sparse = audit("\n".join(lines[i] for i in (0,2,5,8,11,14,16)),*self.sources,1)
        self.assertEqual(sparse["observed_source_sprites"],list(range(3084,3090)))
        self.assertEqual(sparse["complete_presented_lifetimes"],0)
        with self.assertRaisesRegex(ValueError,"six-frame lifetime"):
            audit(self.line(0,3084,0),*self.sources,1)

    def test_stationary_anchor_altitude_and_ownership_reject_corruption(self):
        first,second = self.lifetime()[:2]
        for corrupt in (second.replace("origin 160,160,74","origin 160,160,75"),
                        second.replace("opacity 1","opacity 0.38"),second.replace("pick 0","pick 6")):
            with self.assertRaises(ValueError):
                audit(first+"\n"+corrupt,*self.sources,1)
        moved = second.replace("160,160","161,160")
        with self.assertRaisesRegex(ValueError,"stationary anchor"):
            audit(first+"\n"+moved,*self.sources,1)
        raised = second.replace("160,42","160,43").replace("160,74","160,76")
        with self.assertRaisesRegex(ValueError,"stationary anchor"):
            audit(first+"\n"+raised,*self.sources,1)
        with self.assertRaisesRegex(ValueError,"conflicting spark states"):
            audit(first+"\n"+self.line(0,3084,2),*self.sources,1)

    def test_pool_order_reuse_and_ambiguous_gaps_keep_lifetimes_distinct(self):
        lines = self.lifetime()
        self.assertEqual(audit("\n".join(lines[1:]),*self.sources,1)["complete_presented_lifetimes"],0)
        later = "\n".join(lines[1:]).replace("vehicle 0","vehicle 2")
        self.assertEqual(audit(later,*self.sources,1)["complete_presented_lifetimes"],1)
        reset = self.line(20).replace("160,160","165,160")
        reused = audit(lines[-1]+"\n"+reset,*self.sources,1)
        self.assertEqual(len(reused["lifetimes"]),2)
        self.assertEqual(reused["complete_presented_lifetimes"],0)
        moved = self.line(20,3084,2).replace("160,160","166,160")
        self.assertIn("ambiguous",audit(lines[0]+"\n"+moved,*self.sources,1)["lifetimes"][1]["boundary"])


if __name__ == "__main__":
    unittest.main()

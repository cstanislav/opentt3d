import unittest

from small_explosion_cycle import audit, SOURCES


class SmallExplosionCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    def trace(self, small):
        return "voxel effect frame 0 vehicle 2 type 5 sprite 3709 climate 0 animation 0,0 progress 1 raw 160,160,40 origin 160,160,72 opacity 1 pick 0\n"+small

    def line(self, frame, progress):
        return f"voxel effect frame {frame} vehicle 3 type 7 sprite {3725+progress//4} climate 0 animation 0,0 progress {progress} raw 162,159,39 origin 162,159,71 opacity 1 pick 0"

    def test_ordered_lifetime_preserves_random_local_offsets(self):
        lines = [self.line(i,p) for i,p in enumerate(range(1,48))]
        result = audit(self.trace("\n".join(lines)),*self.sources,[0])
        self.assertEqual(result["complete_presented_lifetimes"],1)
        self.assertEqual(result["observed_source_sprites"],list(range(3725,3737)))
        self.assertEqual(result["lifetimes"][0]["possible_spawn_offsets"],[[6,3,7]])
        self.assertEqual(audit(self.trace("\n".join(lines[1:])),*self.sources,[0])["complete_presented_lifetimes"],0)
        with self.assertRaisesRegex(ValueError,"12-frame lifetime"):
            audit(self.trace(self.line(0,48)),*self.sources,[0])

    def test_offsets_state_and_pool_order_reject_corruption(self):
        line = self.line(0,1)
        for bad in (line.replace("sprite 3725","sprite 3726"),line.replace("162,159","166,159"),
                    line.replace("origin 162,159,71","origin 162,159,72"),line.replace("opacity 1","opacity 0.38"),
                    line.replace("pick 0","pick 6"),line.replace("animation 0,0","animation 1,0"),line.replace("vehicle 3","vehicle 0")):
            with self.assertRaises(ValueError):
                audit(self.trace(bad),*self.sources,[0])
        with self.assertRaisesRegex(ValueError,"stationary anchor"):
            audit(self.trace(line+"\n"+self.line(1,2).replace("162,159","163,159")),*self.sources,[0])
        with self.assertRaisesRegex(ValueError,"conflicting"):
            audit(self.trace(line+"\n"+self.line(0,2)),*self.sources,[0])
        with self.assertRaisesRegex(ValueError,"one distinct observed"):
            audit(self.trace(line),*self.sources,[0,1])

    def test_gaps_pool_reuse_and_source_drift_cannot_pass(self):
        lines = [self.line(i if i<10 else i+100,p) for i,p in enumerate(range(1,48))]
        result = audit(self.trace("\n".join(lines)),*self.sources,[0])
        self.assertEqual(result["complete_presented_lifetimes"],0)
        self.assertEqual(len(result["lifetimes"]),2)
        reset = audit(self.trace(self.line(0,47)+"\n"+self.line(1,1)),*self.sources,[0])
        self.assertEqual(len(reset["lifetimes"]),2)
        sources = list(self.sources)
        sources[1] = sources[1].replace("GB(r,  0, 3) + 5","GB(r,  0, 3) + 6")
        with self.assertRaisesRegex(ValueError,"random crash offsets"):
            audit(self.trace(self.line(0,1)),*sources,[0])


if __name__ == "__main__":
    unittest.main()

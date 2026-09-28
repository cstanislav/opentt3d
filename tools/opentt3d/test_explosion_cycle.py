import unittest

from explosion_cycle import audit, SOURCES


class ExplosionCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    def line(self, frame, progress, vehicle=2):
        return f"voxel effect frame {frame} vehicle {vehicle} type 5 sprite {3709+progress//4} climate 0 animation 0,0 progress {progress} raw 160,160,40 origin 160,160,72 opacity 1 pick 0"

    def test_ordered_full_lifetime_and_missing_phases(self):
        lines = [self.line(i,p) for i,p in enumerate(range(1,64))]
        report = audit("\n".join(lines),*self.sources,[0,1])
        self.assertEqual(report["complete_presented_lifetimes"],1)
        self.assertEqual(report["observed_source_sprites"],list(range(3709,3725)))
        self.assertEqual(audit("\n".join(lines[1:]),*self.sources,[0,1])["complete_presented_lifetimes"],0)
        with self.assertRaisesRegex(ValueError,"16-frame lifetime"):
            audit(self.line(0,64),*self.sources,[0,1])

    def test_placement_and_pool_order_reject_corruption(self):
        line = self.line(0,1)
        for bad in (line.replace("sprite 3709","sprite 3710"),line.replace("origin 160,160,72","origin 160,160,73"),
                    line.replace("opacity 1","opacity 0.38"),line.replace("pick 0","pick 6"),line.replace("animation 0,0","animation 1,0")):
            with self.assertRaises(ValueError):
                audit(bad,*self.sources,[0,1])
        with self.assertRaisesRegex(ValueError,"pool IDs"):
            audit(line,*self.sources,[0,3])
        with self.assertRaisesRegex(ValueError,"stationary anchor"):
            audit(line+"\n"+self.line(1,2).replace("160,160","161,160"),*self.sources,[0,1])
        with self.assertRaisesRegex(ValueError,"conflicting"):
            audit(line+"\n"+self.line(0,2),*self.sources,[0,1])

    def test_gaps_and_reused_ids_cannot_splice_a_complete_lifetime(self):
        lines = [self.line(i if i<10 else i+100,p) for i,p in enumerate(range(1,64))]
        report = audit("\n".join(lines),*self.sources,[0,1])
        self.assertEqual(report["complete_presented_lifetimes"],0)
        self.assertEqual(len(report["lifetimes"]),2)
        reset = audit(self.line(0,63)+"\n"+self.line(1,1),*self.sources,[0,1])
        self.assertEqual(len(reset["lifetimes"]),2)
        sources = list(self.sources)
        sources[1] = sources[1].replace("CreateEffectVehicleRel(v, 4, 4, 8, EV_EXPLOSION_LARGE)","CreateEffectVehicleRel(v, 4, 4, 9, EV_EXPLOSION_LARGE)")
        with self.assertRaisesRegex(ValueError,"eight-unit altitude"):
            audit(self.line(0,1),*sources,[0,1])


if __name__ == "__main__":
    unittest.main()

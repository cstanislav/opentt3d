import unittest

from breakdown_smoke_cycle import audit, SOURCES


class BreakdownSmokeCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [p.read_text() for p in SOURCES]

    def line(self, frame, elapsed, vehicle=0, duration=334):
        progress = elapsed%256
        return (f"breakdown train frame {frame} vehicle 1 engine 13 delay 167 raw 1105,456,16 origin 1105,456,32\n"
                f"voxel effect frame {frame} vehicle {vehicle} type 6 sprite {3737+(progress//8)%4} climate 0 animation {duration-elapsed},0 progress {progress} raw 1109,460,21 origin 1109,460,37 opacity 1 pick 0\n")

    def test_full_lower_pool_lifetime_includes_zero_and_wraps_progress(self):
        result = audit("".join(self.line(p,p) for p in range(334)),*self.sources,1,13)
        self.assertEqual(result["complete_presented_lifetimes"],1)
        self.assertEqual(len(result["lifetimes"]),1)
        self.assertEqual(result["lifetimes"][0]["original_duration"],334)
        self.assertEqual(result["lifetimes"][0]["longest_phase_run"],334)
        self.assertEqual(result["observed_source_sprites"],list(range(3737,3741)))

    def test_higher_pool_lifetime_starts_after_original_first_tick(self):
        text = "".join(self.line(p,p,4) for p in range(1,334))
        result = audit(text,*self.sources,1,13)
        self.assertEqual(result["complete_presented_lifetimes"],1)
        self.assertEqual(result["lifetimes"][0]["first_presented_progress"],1)
        self.assertEqual(audit("".join(self.line(p,p) for p in range(1,334)),*self.sources,1,13)["complete_presented_lifetimes"],0)

    def test_missing_phase_or_terminal_countdown_cannot_pass(self):
        for elapsed in ([p for p in range(334) if p!=21],range(333)):
            self.assertEqual(audit("".join(self.line(i,p) for i,p in enumerate(elapsed)),*self.sources,1,13)["complete_presented_lifetimes"],0)

    def test_capture_gap_and_reused_id_cannot_splice(self):
        text = "".join(self.line(p if p<90 else p+20,p) for p in range(334))
        result = audit(text,*self.sources,1,13)
        self.assertEqual(result["complete_presented_lifetimes"],0)
        self.assertEqual(len(result["lifetimes"]),2)
        text = "".join(self.line(p,p) for p in range(90))+"".join(self.line(p+90,p) for p in range(1,334))
        self.assertEqual(audit(text,*self.sources,1,13)["complete_presented_lifetimes"],0)

    def test_stationary_puff_can_outlive_its_stopped_emitter(self):
        lines = [self.line(p,p) if p<332 else self.line(p,p).split("\n",1)[1] for p in range(334)]
        result = audit("".join(lines),*self.sources,1,13)
        self.assertEqual(result["complete_presented_lifetimes"],1)
        self.assertEqual(result["lifetimes"][0]["anchored_without_stopped_emitter"],2)
        with self.assertRaisesRegex(ValueError,"stationary anchor"):
            audit("".join(lines[:-1])+lines[-1].replace("1109,460","1110,460"),*self.sources,1,13)
        with self.assertRaisesRegex(ValueError,"lifetime boundary"):
            audit(lines[0].split("\n",1)[1]+"".join(lines[1:]),*self.sources,1,13)

    def test_emitter_offsets_altitude_palette_owner_and_countdown_corruption_rejected(self):
        text = self.line(0,0)
        cases = (text.replace("sprite 3737","sprite 3738"),text.replace("raw 1109,460,21","raw 1110,460,21"),
                 text.replace("origin 1109,460,37","origin 1109,460,42"),text.replace("opacity 1","opacity 0.38"),
                 text.replace("pick 0","pick 4"),text.replace("engine 13","engine 14"),text.split("\n",1)[1],
                 self.line(0,0)+self.line(1,1).replace("progress 1","progress 2"))
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audit(bad,*self.sources,1,13)

    def test_conflicting_observations_and_source_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"conflicting original breakdown smoke"):
            audit(self.line(0,0)+self.line(0,1),*self.sources,1,13)
        with self.assertRaisesRegex(ValueError,"conflicting original breakdown emitters"):
            audit(self.line(0,0)+self.line(0,0).replace("delay 167","delay 166"),*self.sources,1,13)
        with self.assertRaisesRegex(ValueError,"Original breakdown smoke timing"):
            audit(self.line(0,0),self.sources[0].replace("(v->progress & 7) == 0","(v->progress & 3) == 0"),self.sources[1],1,13)

    def test_absence_and_even_original_duration(self):
        self.assertTrue(audit("",*self.sources,1,13,True)["expected_absence"])
        with self.assertRaisesRegex(ValueError,"Expected absence"):
            audit(self.line(0,0),*self.sources,1,13,True)
        result = audit("".join(self.line(p,p,duration=333) for p in range(333)),*self.sources,1,13)
        self.assertEqual(result["complete_presented_lifetimes"],0)


if __name__ == "__main__":
    unittest.main()

import unittest

from chimney_cycle import audit, SOURCES


class ChimneyCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    def line(self, frame, sprite=3708, progress=0):
        return f"voxel effect frame {frame} vehicle 5 type 0 sprite {sprite} climate 1 animation 0,0 progress {progress} raw 831,574,67 origin 831,574,75 opacity 1 pick 0"

    def test_original_wrap_keeps_the_chimney_stationary_and_unclickable(self):
        text = self.line(3)+"\n"+self.line(4,3701,7)
        result = audit(text,*self.sources)
        self.assertEqual(result["chimneys"][0]["sequential_tick_steps"],1)
        self.assertEqual(result["complete_ordered_cycles"],0)
        for corrupt in (text.replace("origin 831,574,75","origin 831,574,134"),text.replace("pick 0","pick 6"),
                        text.replace("opacity 1","opacity 0.38"),text.replace("sprite 3701","sprite 3709"),
                        text.replace("progress 7","progress 8")):
            with self.assertRaises(ValueError):
                audit(corrupt,*self.sources)
        moved = self.line(4,3701,7).replace("831,574","847,574")
        with self.assertRaisesRegex(ValueError,"Stationary chimney moved"):
            audit(self.line(3)+"\n"+moved,*self.sources)

    def test_all_phases_out_of_order_do_not_establish_a_cycle(self):
        def trace(phases):
            return "\n".join(self.line(frame,3701+phase//8,7-phase%8) for frame,phase in enumerate(phases))
        ordered = [(phase+37)%64 for phase in range(65)]
        self.assertEqual(audit(trace(ordered),*self.sources)["complete_ordered_cycles"],1)
        shuffled = list(range(0,64,2))+list(range(1,64,2))+[0]
        result = audit(trace(shuffled),*self.sources)
        self.assertTrue(result["all_original_phases_observed"])
        self.assertEqual(result["complete_ordered_cycles"],0)

    def test_multiple_viewports_only_deduplicate_identical_observations(self):
        line = self.line(8)
        self.assertEqual(audit(line+"\n"+line,*self.sources)["samples"],1)
        with self.assertRaisesRegex(ValueError,"conflicting chimney states"):
            audit(line+"\n"+self.line(8,3701,7),*self.sources)


if __name__ == "__main__":
    unittest.main()

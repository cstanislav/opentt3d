import unittest

from diesel_cycle import audit, SOURCES


class DieselCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    def line(self, frame, sprite=3073, progress=0, z=42, rendered=74, vehicle=0):
        return f"voxel effect frame {frame} vehicle {vehicle} type 2 sprite {sprite} climate 0 animation 0,0 progress {progress} raw 160,160,{z} origin 160,160,{rendered} opacity 1 pick 0"

    def test_first_tick_and_four_tick_rise_follow_original_source(self):
        text = "\n".join((self.line(0),self.line(1,3074,1),self.line(4,3074,4,43,75),self.line(9,3075,9,44,76)))
        self.assertEqual(audit(text,*self.sources,1)["lifetimes"][0]["anchor"],(160,160,42))
        for corrupt in (text.replace("sprite 3074","sprite 3073"),text.replace("raw 160,160,43","raw 160,160,44"),
                        text.replace("opacity 1","opacity 0.38"),text.replace("pick 0","pick 6")):
            with self.assertRaises(ValueError):
                audit(corrupt,*self.sources,1)
        with self.assertRaisesRegex(ValueError,"six-frame lifetime"):
            audit(self.line(41,3078,41,52,84),*self.sources,1)
        moved = self.line(1,3074,1).replace("160,160","161,160")
        with self.assertRaisesRegex(ValueError,"moved horizontally"):
            audit(self.line(0)+"\n"+moved,*self.sources,1)

    def test_complete_lifetime_covers_ordered_phases_and_original_pool_order(self):
        # Original frame transitions are1,9,17,25,33; rise ticks are4,8,...,40.
        lines, sprite, z = [], 3073, 42
        for progress in range(41):
            if progress in (1,9,17,25,33):
                sprite += 1
            if progress in (4,8,12,16,20,24,28,32,36,40):
                z += 1
            lines.append(self.line(progress,sprite,progress,z,z+32))
        whole = audit("\n".join(lines),*self.sources,1)
        self.assertEqual(whole["complete_presented_lifetimes"],1)
        self.assertEqual(whole["complete_six_frame_lifetimes"],1)
        self.assertEqual(whole["observed_source_sprites"],list(range(3073,3079)))
        self.assertEqual(audit("\n".join(lines[1:]),*self.sources,1)["complete_presented_lifetimes"],0)
        later = "\n".join(lines[1:]).replace("vehicle 0","vehicle 2")
        self.assertEqual(audit(later,*self.sources,1)["complete_presented_lifetimes"],1)
        # A separate pre-tick-only puff cannot supply the missing first sprite
        # of a different later-ID lifetime.
        mixed = audit(later+"\n"+self.line(90),*self.sources,1)
        self.assertEqual(mixed["observed_source_sprites"],list(range(3073,3079)))
        self.assertEqual(mixed["complete_six_frame_lifetimes"],0)
        sparse = audit("\n".join(lines[i] for i in (0,1,9,17,25,33,40)),*self.sources,1)
        self.assertEqual(sparse["observed_source_sprites"],list(range(3073,3079)))
        self.assertEqual(sparse["complete_presented_lifetimes"],0)
        with self.assertRaisesRegex(ValueError,"conflicting diesel states"):
            audit(lines[0]+"\n"+self.line(0,3074,1),*self.sources,1)

    def test_reused_pool_ids_and_ambiguous_gaps_do_not_join_puffs(self):
        reset = self.line(42).replace("160,160","165,160")
        result = audit(self.line(40,3078,40,52,84)+"\n"+reset,*self.sources,1)
        self.assertEqual(len(result["lifetimes"]),2)
        self.assertEqual(result["complete_presented_lifetimes"],0)
        moved = self.line(20,3074,4,43,75).replace("160,160","166,160")
        self.assertIn("ambiguous",audit(self.line(0)+"\n"+moved,*self.sources,1)["lifetimes"][1]["boundary"])


if __name__ == "__main__":
    unittest.main()

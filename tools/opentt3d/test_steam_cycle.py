import unittest

from steam_cycle import audit, SOURCES


class SteamCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    def line(self, frame, sprite=3079, progress=12, z=42, rendered=74):
        return f"voxel effect frame {frame} vehicle 5 type 1 sprite {sprite} climate 0 animation 0,0 progress {progress} raw 160,160,{z} origin 160,160,{rendered} opacity 1 pick 0"

    def test_original_phase_boundary_and_rise_keep_the_spawn_anchor(self):
        text = self.line(1)+"\n"+self.line(2,3080,20,43,75)+"\n"+self.line(8,3083,83,51,83)
        result = audit(text,*self.sources)
        self.assertEqual(result["lifetimes"][0]["anchor"],(160,160,42))
        self.assertEqual(result["complete_presented_lifetimes"],0)
        for corrupt in (text.replace("sprite 3080","sprite 3079"),text.replace("progress 83","progress 84"),
                        text.replace("origin 160,160,75","origin 160,160,76"),text.replace("opacity 1","opacity 0.38"),
                        text.replace("pick 0","pick 6")):
            with self.assertRaises(ValueError):
                audit(corrupt,*self.sources)
        moved = self.line(2,3080,20,43,75).replace("160,160","161,160")
        with self.assertRaisesRegex(ValueError,"moved horizontally"):
            audit(self.line(1)+"\n"+moved,*self.sources)

    def test_pool_reuse_and_uncaptured_gaps_do_not_join_lifetimes(self):
        last = self.line(10,3083,83,51,83)
        reset = self.line(11).replace("160,160","165,160")
        result = audit(last+"\n"+reset,*self.sources)
        self.assertEqual(len(result["lifetimes"]),2)
        self.assertEqual(result["complete_presented_lifetimes"],0)
        after_gap = self.line(90,3080,20,43,75).replace("160,160","185,160")
        result = audit(self.line(1)+"\n"+after_gap,*self.sources)
        self.assertIn("ambiguous",result["lifetimes"][1]["boundary"])

    def test_sparse_all_sprite_observations_are_not_a_complete_lifetime(self):
        # Independent original boundaries: first frame lasts12..19, then four
        # sixteen-tick frames20..83. Height rises at16,24,...,80.
        lines = []
        progress, sprite, z = 12, 3079, 42
        for frame in range(72):
            lines.append(self.line(frame,sprite,progress,z,z+32))
            progress += 1
            if progress in (16,24,32,40,48,56,64,72,80):
                z += 1
            if progress in (20,36,52,68):
                sprite += 1
        self.assertEqual(audit("\n".join(lines),*self.sources)["complete_presented_lifetimes"],1)
        # Fixture locomotive0 creates a later pool item5, which the ascending
        # original tick loop advances before its first presented frame.
        presented = "\n".join(lines[1:])
        self.assertEqual(audit(presented,*self.sources)["complete_presented_lifetimes"],0)
        after = audit(presented,*self.sources,emitter=0)
        self.assertEqual(after["complete_presented_lifetimes"],1)
        self.assertEqual(after["first_presented_progress"],[13])
        self.assertEqual(audit(presented,*self.sources,emitter=9)["complete_presented_lifetimes"],0)
        sparse = audit("\n".join(lines[::8]),*self.sources)
        self.assertEqual(sparse["observed_source_sprites"],list(range(3079,3084)))
        self.assertEqual(sparse["complete_presented_lifetimes"],0)
        with self.assertRaisesRegex(ValueError,"conflicting steam states"):
            audit(lines[0]+"\n"+self.line(0,3080,20,43,75),*self.sources)


if __name__ == "__main__":
    unittest.main()

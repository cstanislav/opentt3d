import unittest

from demolition_explosion_cycle import audit, SOURCES


class DemolitionExplosionCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [path.read_text() for path in SOURCES]

    command = "original clear-area command tile 10,12 centre 168,200 ground 16 paused 0\n"

    def line(self, frame, progress, vehicle=4):
        return f"voxel effect frame {frame} vehicle {vehicle} type 7 sprite {3725+progress//4} climate 0 animation 0,0 progress {progress} raw 168,200,18 origin 168,200,34 opacity 1 pick 0\n"

    def test_full_lifetime_includes_command_tick_zero(self):
        lines = [self.line(p,p) for p in range(48)]
        result = audit(self.command+"".join(lines),*self.sources)
        self.assertEqual(result["complete_presented_lifetimes"],1)
        self.assertEqual(result["observed_source_sprites"],list(range(3725,3737)))
        self.assertEqual(result["rendered_origin"],[168,200,34])
        self.assertEqual(audit(self.command+"".join(lines[1:]),*self.sources)["complete_presented_lifetimes"],0)
        with self.assertRaisesRegex(ValueError,"48-phase"):
            audit(self.command+self.line(0,48),*self.sources)

    def test_altitude_and_command_ownership_reject_corruption(self):
        line = self.line(0,0)
        for bad in (line.replace("sprite 3725","sprite 3726"),line.replace("raw 168,200,18","raw 168,200,19"),
                    line.replace("origin 168,200,34","origin 168,200,36"),line.replace("opacity 1","opacity 0.38"),
                    line.replace("pick 0","pick 6"),line.replace("animation 0,0","animation 1,0")):
            with self.assertRaises(ValueError):
                audit(self.command+bad,*self.sources)
        with self.assertRaisesRegex(ValueError,"preceded"):
            audit(line+self.command,*self.sources)
        with self.assertRaisesRegex(ValueError,"conflicting"):
            audit(self.command+line+self.line(0,1),*self.sources)
        with self.assertRaisesRegex(ValueError,"moved from its tile centre"):
            audit(self.command+line+self.line(1,1).replace("168,200","169,200"),*self.sources)
        with self.assertRaisesRegex(ValueError,"one successfully"):
            audit(self.command+self.command+line,*self.sources)

    def test_gaps_and_reused_ids_cannot_splice_full_lifetimes(self):
        text = self.command+"".join(self.line(p if p<20 else p+100,p) for p in range(48))
        result = audit(text,*self.sources)
        self.assertEqual(result["complete_presented_lifetimes"],0)
        self.assertEqual(len(result["lifetimes"]),2)
        text = self.command+"".join(self.line(p,p) for p in range(24))+"".join(self.line(p+24,p) for p in range(1,48))
        self.assertEqual(audit(text,*self.sources)["complete_presented_lifetimes"],0)

    def test_original_paused_suppression_and_source_drift(self):
        paused = self.command.replace("paused 0","paused 1")
        self.assertTrue(audit(paused,*self.sources,True)["paused_suppression"])
        with self.assertRaisesRegex(ValueError,"paused suppression"):
            audit(paused+self.line(0,0),*self.sources,True)
        changed = self.sources[1].replace("_pause_mode.None()","_pause_mode.Any()")
        with self.assertRaisesRegex(ValueError,"paused suppression changed"):
            audit(paused,self.sources[0],changed,True)


if __name__ == "__main__":
    unittest.main()

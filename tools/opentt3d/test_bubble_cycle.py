import unittest

from bubble_cycle import audit, source_tables, successors, SOURCES


class BubbleCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [p.read_text() for p in SOURCES]
        cls.tables, cls.spawn = source_tables(*cls.sources)

    def line(self, frame, progress, sample, direction=0, vehicle=0, ground=16):
        mode,state,sprite,x,y,z = sample
        return (f"voxel effect frame {frame} vehicle {vehicle} type 9 sprite {sprite} climate 3 animation {state},{direction} progress {progress} raw {x},{y},{z} origin {x},{y},{z+ground} opacity 1 pick 0\n"
                f"bubble mode frame {frame} vehicle {vehicle} mode {mode} ground {ground}\n")

    def path(self, direction=0, floating=1, burst_at=28, end=None):
        sample = (0,0,4751,800+self.spawn[0][direction],544+self.spawn[1][direction],16+self.spawn[2][direction])
        lines = []
        for elapsed in range(1,end or (344 if direction == 0 else burst_at+16)):
            progress = elapsed%256
            if progress%4 == 0:
                choices = successors(sample,progress,direction,self.tables)
                if not choices:
                    break
                if direction and elapsed == 12:
                    sample = next(edge for edge in choices if edge[0] == floating)
                elif direction and elapsed >= burst_at and any(edge[0] == 5 for edge in choices):
                    sample = next(edge for edge in choices if edge[0] == 5)
                else:
                    sample = min(choices)
            lines.append(self.line(elapsed,progress,sample,direction))
        return lines

    def test_absorption_requires_every_phase_and_preserves_original_wrap_and_skipped_sentinel(self):
        report = audit("".join(self.path()),*self.sources)
        self.assertEqual(report["complete_absorbed_lifetimes"],1)
        self.assertEqual(report["complete_burst_lifetimes"],0)
        row = report["lifetimes"][0]
        self.assertEqual(row["phases"],list(range(1,344)))
        self.assertEqual(row["generator_tile"],(50,34))
        self.assertEqual(row["last_state"],83)
        self.assertNotIn(4754,report["observed_source_sprites"])

    def test_all_four_random_float_tables_can_lead_to_independent_complete_bursts(self):
        for floating in range(1,5):
            with self.subTest(floating=floating):
                report = audit("".join(self.path(1,floating)),*self.sources)
                self.assertEqual(report["complete_burst_lifetimes"],1)
                self.assertEqual(report["lifetimes"][0]["modes"],[0,floating,5] if floating < 5 else [0,5])

    def test_long_float_path_wrap_does_not_reuse_pool_id(self):
        report = audit("".join(self.path(3,4,burst_at=284)),*self.sources)
        self.assertEqual(len(report["lifetimes"]),1)
        self.assertEqual(report["complete_burst_lifetimes"],1)

    def test_missing_phase_and_terminal_hold_remain_incomplete(self):
        lines = self.path()
        for partial in (lines[:20]+lines[21:],lines[:-1],lines[1:]):
            report = audit("".join(partial),*self.sources)
            self.assertEqual(report["complete_presented_lifetimes"],0)

    def test_capture_gap_and_reused_pool_id_cannot_splice(self):
        lines = self.path()
        changed = [line.replace(f"frame {i}",f"frame {i+20}") if i>=50 else line for i,line in enumerate(lines,1)]
        report = audit("".join(changed),*self.sources)
        self.assertEqual(report["complete_presented_lifetimes"],0)
        self.assertEqual(len(report["lifetimes"]),2)
        reused = lines[:40]+[line.replace(f"frame {i}",f"frame {i+40}") for i,line in enumerate(lines[1:],2)]
        report = audit("".join(reused),*self.sources)
        self.assertEqual(report["complete_presented_lifetimes"],0)

    def test_mode_selection_displacement_and_spawn_corruption_are_rejected(self):
        lines = self.path()
        for bad in (lines[0].replace("raw 811,540,65","raw 812,540,65").replace("origin 811,540,81","origin 812,540,81"),
                    lines[0].replace("mode 0","mode 6"),lines[0].replace("ground 16","ground 17"),
                    lines[0].replace("opacity 1","opacity 0.38"),lines[0].replace("pick 0","pick 4"),
                    lines[0].split("bubble mode",1)[0],lines[0].replace("sprite 4751","sprite 4754")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audit(bad,*self.sources)
        with self.assertRaisesRegex(ValueError,"displacement"):
            audit(lines[0]+lines[1].replace("raw 811,540,65","raw 811,540,66").replace("origin 811,540,81","origin 811,540,82"),*self.sources)

    def test_duplicate_observations_and_modes_are_consistent(self):
        line = self.path()[0]
        self.assertEqual(audit(line+line,*self.sources)["samples"],1)
        with self.assertRaisesRegex(ValueError,"conflicting bubble modes"):
            audit(line+line.replace("mode 0","mode 1"),*self.sources)
        with self.assertRaisesRegex(ValueError,"conflicting original bubble"):
            audit(line+line.replace("progress 1","progress 2"),*self.sources)

    def test_absence_and_unpaired_mode_records_are_rejected(self):
        self.assertTrue(audit("",*self.sources,True)["expected_absence"])
        with self.assertRaisesRegex(ValueError,"Expected absence"):
            audit(self.path()[0],*self.sources,True)
        with self.assertRaisesRegex(ValueError,"do not reconcile"):
            audit("bubble mode frame 1 vehicle 0 mode 0 ground 16\n",*self.sources)

    def test_source_timing_movement_spawn_and_tick_order_drift_fail(self):
        changes = ((0,"(v->progress & 3) != 0","(v->progress & 7) != 0"),
                   (0,"MK(1, 0, 1, 1)","MK(2, 0, 1, 1)"),
                   (1,"{ 11,   0, -4, -14 }","{ 12,   0, -4, -14 }"),
                   (2,"RunTileLoop();\n\t\tCallVehicleTicks();","CallVehicleTicks();\n\t\tRunTileLoop();"))
        for index,old,new in changes:
            sources = self.sources.copy()
            sources[index] = sources[index].replace(old,new)
            with self.subTest(index=index), self.assertRaises(ValueError):
                audit("".join(self.path()),*sources)

    def test_original_mode_table_order_and_high_altitude_forced_burst_are_not_randomized(self):
        changed = self.sources.copy()
        changed[0] = changed[0].replace("\t_bubble_float_sw,\n\t_bubble_float_ne,","\t_bubble_float_ne,\n\t_bubble_float_sw,")
        with self.assertRaisesRegex(ValueError,"mode order"):
            audit("".join(self.path()),*changed)
        edges = successors((2,3,4750,800,540,181),28,1,self.tables)
        self.assertEqual(edges,{(5,0,4750,800,540,182)})


if __name__ == "__main__":
    unittest.main()

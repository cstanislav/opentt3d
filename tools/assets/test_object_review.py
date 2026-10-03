"""Source registration/evidence stays testable without optional Pillow authoring."""
from pathlib import Path
import unittest

from object_review import owner_native_offset, source_evidence_paths, source_layer_registrations, source_owner_registrations


class ObjectReviewRegistrationTests(unittest.TestCase):
    def row(self,part,offset):
        return {"part":part,"tile_offset":offset,
                "ground":{"image":f"ground{part}.pam","sprite_offset":[-128,0]},
                "body":[{"image":f"body{part}.pam","origin":[7,7,0],"sprite_offset":[-104,-320]}]}

    def test_original_tile_and_sortable_anchors_are_not_visible_centres(self):
        rows = [self.row(3,[1,1]),self.row(2,[0,1]),self.row(1,[1,0]),self.row(0,[0,0])]
        actual = source_layer_registrations(rows)
        self.assertEqual(actual[:4],[("ground0.pam",-32,0),("ground1.pam",-64,16),
                                    ("ground2.pam",0,16),("ground3.pam",-32,32)])
        self.assertEqual(actual[4:],[("body0.pam",-26,-66),("body1.pam",-58,-50),
                                    ("body2.pam",6,-50),("body3.pam",-26,-34)])
        self.assertEqual(source_evidence_paths(rows,Path("references")),[Path("references")/name for name,x,y in actual])

    def test_body_absence_does_not_drop_raised_ground_or_duplicate_evidence(self):
        row = self.row(0,[0,0])
        row["body"] = []
        self.assertEqual(source_evidence_paths([row],Path("references")),[Path("references/ground0.pam")])

    def test_sub_native_offsets_and_boolean_offsets_are_not_silently_rounded(self):
        for bad in ([1,0],[False,0],[-128,2],[-128,0,0]):
            with self.subTest(offset=bad):
                row = self.row(0,[0,0])
                row["ground"]["sprite_offset"] = bad
                with self.assertRaisesRegex(ValueError,"native sprite scale"):
                    source_layer_registrations([row])

    def test_owner_sheet_does_not_include_another_layer_or_apply_the_tile_root_twice(self):
        row = self.row(1,[1,0])
        self.assertEqual(source_owner_registrations(row,"ground"),[("ground1.pam",-32,0)])
        self.assertEqual(source_owner_registrations(row,"body"),[("body1.pam",-26,-66)])
        self.assertEqual(owner_native_offset(row,{"origin":[23,7,0]}),(0,14))
        self.assertEqual(owner_native_offset(row,{"origin":[16,0,0]}),(0,0))
        self.assertEqual(row["tile_offset"],[1,0],"Display framing must not mutate source metadata")

    def test_owner_sheet_keeps_absence_and_sequence_height(self):
        row = self.row(3,[1,1]); row["body"] = []
        self.assertEqual(source_owner_registrations(row,"body"),[])
        self.assertEqual(owner_native_offset(row,{"origin":[18,19,5]}),(2,0))
        with self.assertRaisesRegex(ValueError,"source owner"):
            source_owner_registrations(row,"joined")

    def test_exported_integral_float_anchors_do_not_round_fractional_positions(self):
        row = self.row(1,[1,0])
        self.assertEqual(owner_native_offset(row,{"origin":[16.0,0.0,0.0]}),(0,0))
        self.assertTrue(all(type(value) is int for value in owner_native_offset(row,{"origin":[16.0,0.0,0.0]})))
        with self.assertRaisesRegex(ValueError,"native sprite scale"):
            owner_native_offset(row,{"origin":[16.25,0.0,0.0]})


if __name__ == "__main__":
    unittest.main()

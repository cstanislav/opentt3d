"""Source registration/evidence stays testable without optional Pillow authoring."""
from pathlib import Path
import unittest

from object_review import source_evidence_paths, source_layer_registrations


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


if __name__ == "__main__":
    unittest.main()

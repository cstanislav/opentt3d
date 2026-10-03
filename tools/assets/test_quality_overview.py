from pathlib import Path
import tempfile
import unittest

from quality_overview import model_images


class QualityOverviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.model = {"size":[1,1,1],"cell_size":[1,1,1],"origin":[0,0,0],"runs":[[0,0,0,1,1]]}
        self.catalogue = {"models":{"sample":self.model},"materials":[[1]*6],"bindings":{"effects":{"1":{"0":"sample"}}}}
        for view in (*range(8),"native"):
            (self.root/f"model-voxel-sample-{view}.pam").touch()
        (self.root/"model-voxel-sample-native.json").write_text('{}')

    def test_each_model_keeps_all_views_registration_fingerprint_and_owners(self):
        records = model_images(self.root,self.catalogue)
        self.assertEqual(len(records),1)
        self.assertEqual(len(records[0]["views"]),8)
        self.assertEqual(records[0]["owners"],["effects/1/0"])
        self.assertEqual(len(records[0]["fingerprint"]),64)

    def test_partial_gallery_and_missing_registration_cannot_be_complete(self):
        (self.root/"model-voxel-sample-7.pam").unlink()
        with self.assertRaisesRegex(ValueError,"Missing native review image"):
            model_images(self.root,self.catalogue)
        (self.root/"model-voxel-sample-7.png").touch()
        (self.root/"model-voxel-sample-native.json").unlink()
        with self.assertRaisesRegex(ValueError,"Missing source-scale registration"):
            model_images(self.root,self.catalogue)


if __name__ == "__main__":
    unittest.main()

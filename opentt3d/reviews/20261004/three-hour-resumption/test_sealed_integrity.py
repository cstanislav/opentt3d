"""Path schemes are explicit; missing evidence never changes a manifest root."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sealed_integrity',HERE/'verify-sealed-integrity.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class SealedIntegrityTests(unittest.TestCase):
    def test_repository_relative_historical_path(self):
        manifest=HERE/'nested/evidence-sha256.json'
        key='opentt3d/reviews/historical/source.pam'
        self.assertEqual(audit.evidence_path(manifest,key),audit.ROOT/key)

    def test_portable_relative_schema_even_when_missing(self):
        manifest=HERE/'never-created/evidence-sha256.json'
        key='native-controls/source.png'
        self.assertEqual(audit.evidence_path(manifest,key),manifest.parent/key)

    def test_unrelated_prefix_does_not_become_repository_root(self):
        manifest=HERE/'never-created/evidence-sha256.json'
        self.assertEqual(audit.evidence_path(manifest,'opentt3d-copy/source.png'),manifest.parent/'opentt3d-copy/source.png')

    def test_reject_absolute_empty_and_traversing_paths(self):
        for key in ('','/source.pam','../source.pam','native-controls/../source.pam'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                audit.evidence_path(HERE/'evidence-sha256.json',key)


if __name__=='__main__':unittest.main()

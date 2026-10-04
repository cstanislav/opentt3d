"""Windows release checkout preserves long original evidence paths without exclusions."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


class ReleaseCheckoutTests(unittest.TestCase):
    def test_longpaths_is_enabled_before_windows_checkout(self):
        workflow=(ROOT/'.github/workflows/opentt3d-release.yml').read_text()
        windows=workflow.split('\n  windows:',1)[1].split('\n  linux:',1)[0]
        self.assertLess(windows.index('git config --global core.longpaths true'),windows.index('uses: actions/checkout@v6'))
        self.assertIn('shell: pwsh',windows[:windows.index('uses: actions/checkout@v6')])

    def test_no_source_or_evidence_exclusion_is_used_as_a_checkout_workaround(self):
        workflow=(ROOT/'.github/workflows/opentt3d-release.yml').read_text()
        self.assertNotIn('sparse-checkout',workflow)
        self.assertNotIn('filter: blob:none',workflow)
        self.assertNotIn('rm -rf',workflow)


if __name__=='__main__':unittest.main()

"""Windows and nightly checkouts preserve long original evidence paths."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]


class ReleaseCheckoutTests(unittest.TestCase):
    def windows_sections(self):
        yield 'ci-mingw.yml',(ROOT/'.github/workflows/ci-mingw.yml').read_text()
        yield 'ci-windows.yml',(ROOT/'.github/workflows/ci-windows.yml').read_text()
        text=(ROOT/'.github/workflows/opentt3d-ci.yml').read_text()
        yield 'opentt3d-ci.yml',text.split('\n  windows:',1)[1]
        text=(ROOT/'.github/workflows/opentt3d-release.yml').read_text()
        yield 'opentt3d-release.yml',text.split('\n  windows:',1)[1].split('\n  linux:',1)[0]

    def test_longpaths_precedes_every_windows_checkout(self):
        for name,text in self.windows_sections():
            self.assertIn('git config --global core.longpaths true',text,name)
            for match in re.finditer(r'uses: actions/checkout@v6',text):
                self.assertIn('git config --global core.longpaths true',text[:match.start()],name)

    def test_release_windows_job_enables_longpaths_with_powershell(self):
        text=(ROOT/'.github/workflows/opentt3d-release.yml').read_text()
        windows=text.split('\n  windows:',1)[1].split('\n  linux:',1)[0]
        self.assertLess(windows.index('git config --global core.longpaths true'),windows.index('uses: actions/checkout@v6'))
        self.assertIn('shell: pwsh',windows[:windows.index('uses: actions/checkout@v6')])

    def test_nightly_allows_slow_renderer_regressions(self):
        for name in ('ci-macos.yml','ci-mingw.yml','ci-windows.yml','ci-linux.yml'):
            text=(ROOT/'.github/workflows'/name).read_text()
            self.assertNotIn('--timeout 120',text,name)
            self.assertIn('--timeout 300',text,name)

    def test_nightly_fetches_pinned_opengfx2(self):
        sha='2f4d0d8cd82b9b15d7c5a742581bfd11a08d4fd54fc0743f1f8a1032e3b5eeaf'
        for name in ('ci-macos.yml','ci-mingw.yml'):
            text=(ROOT/'.github/workflows'/name).read_text()
            self.assertIn('OpenGFX2_Classic-0.8.1.tar',text,name)
            self.assertIn(sha,text,name)
            self.assertLess(text.index('Install pinned OpenGFX2 Classic'),text.index('- name: Test'),name)

    def test_nightly_macos_uses_filesystem_capable_deployment_target(self):
        text=(ROOT/'.github/workflows/ci-macos.yml').read_text()
        target=re.search(r'MACOSX_DEPLOYMENT_TARGET:\s*([0-9.]+)',text)
        self.assertIsNotNone(target)
        self.assertGreaterEqual(tuple(int(part) for part in target[1].split('.')),(10,15))

    def test_no_source_or_evidence_exclusion_is_used_as_a_checkout_workaround(self):
        for name,text in self.windows_sections():
            self.assertNotIn('sparse-checkout',text,name)
            self.assertNotIn('filter: blob:none',text,name)
            self.assertNotIn('rm -rf',text,name)


if __name__=='__main__':unittest.main()

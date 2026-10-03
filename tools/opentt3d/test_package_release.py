"""Exercise archive extraction with the pre-filter Python used by Debian 12."""

import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from package_release import extract_generated_tar


class PackageArchiveTests(unittest.TestCase):
    def test_draft_lookup_has_scoped_access_without_early_publication(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/opentt3d-release.yml").read_text()
        self.assertIn("permissions:\n  contents: read\n",workflow)
        source = workflow.split("  source:\n",1)[1].split("\n  linux:\n",1)[0]
        self.assertIn("    permissions:\n      contents: write\n",source)
        self.assertIn('gh release view "$RELEASE_TAG"',source)
        self.assertIn("ref: ${{ inputs.tag || github.event.release.tag_name }}",source)
        for job, following in (("linux","macos"),("macos","windows"),("windows","publish")):
            block = workflow.split(f"\n  {job}:\n",1)[1].split(f"\n  {following}:\n",1)[0]
            self.assertNotIn("contents: write",block)
            self.assertIn("ref: ${{ needs.source.outputs.sha }}",block)
        self.assertNotIn("gh release edit",workflow)
        self.assertNotIn("--draft=false",workflow)
        self.assertIn("needs: [source, linux, macos, windows]",workflow)

    def test_extended_linux_review_keeps_all_original_contact_gates_and_immutable_source(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/opentt3d-release.yml").read_text()
        command = next(line for line in workflow.splitlines() if "--output build-release/electric-check " in line)
        for required in ("--vulkan-validation", "--reference-catenary", "--verify-live-tunnel",
                         "--verify-rail-details", "--verify-stations", "--verify-depots",
                         "--verify-crossings", "--verify-road-stops", "--verify-trees",
                         "--verify-train-support 26", "--verify-train-collectors 26",
                         "--first-person auto", "--running", "--benchmark-frames 1800",
                         "--timeout 2400", "--memory-limit-mib 6144"):
            self.assertIn(required,command)
        self.assertIn("ref: ${{ needs.source.outputs.sha }}",workflow)
        self.assertIn("needs: [source, linux, macos, windows]",workflow)

    def test_generated_archive_extracts_with_and_without_filter_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "package.tar.xz"
            with tarfile.open(archive, "w:xz") as output:
                entry = tarfile.TarInfo("package/opentt3d.sh")
                entry.mode = 0o755
                payload = b"#!/bin/sh\nexit 0\n"
                entry.size = len(payload)
                output.addfile(entry, io.BytesIO(payload))
            extract_generated_tar(archive, root / "current")
            self.assertEqual((root / "current/package/opentt3d.sh").read_bytes(), payload)

            original = tarfile.TarFile.extractall
            filter_options = {"filter": "fully_trusted"} if hasattr(tarfile, "data_filter") else {}
            def old_extractall(source, path=".", members=None, *, numeric_owner=False):
                # An unexpected filter keyword reproduces the CI TypeError.
                return original(source, path, members=members, numeric_owner=numeric_owner, **filter_options)

            with mock.patch.object(tarfile, "data_filter", create=True), mock.patch.object(tarfile.TarFile, "extractall", old_extractall):
                del tarfile.data_filter
                extract_generated_tar(archive, root / "debian12")
            self.assertEqual((root / "debian12/package/opentt3d.sh").read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()

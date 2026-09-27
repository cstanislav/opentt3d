"""Exercise archive extraction with the pre-filter Python used by Debian 12."""

import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from package_release import extract_generated_tar


class PackageArchiveTests(unittest.TestCase):
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

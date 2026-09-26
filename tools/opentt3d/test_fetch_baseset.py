"""Verified graphics staging must share disk data without damaging good archives."""

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fetch_baseset import fetch, link_or_copy


class GraphicsCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.content = b"pinned graphics fixture\0" * 1024
        self.pin = {"filename": "graphics.tar", "sha256": hashlib.sha256(self.content).hexdigest(),
                    "name": "Fixture", "tag": "1", "url": "https://invalid.example/graphics.tar"}
        self.seed = self.root / "original.tar"
        self.seed.write_bytes(self.content)

    def install(self, name):
        return fetch(self.root / name, seed=self.seed, cache=self.root / "cache", pin=self.pin)

    def test_existing_verified_archive_is_shared_without_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected download")):
            first, second = self.install("first"), self.install("second")
            self.assertTrue(first.samefile(second))
            self.assertEqual(first.read_bytes(), self.content)
            # Removing one isolated test directory must not remove the shared archive.
            first.unlink()
            self.assertEqual(second.read_bytes(), self.content)

    def test_corrupt_destination_is_replaced_from_verified_cache(self):
        first = self.install("first")
        destination = self.root / "second" / "graphics.tar"
        destination.parent.mkdir()
        destination.write_bytes(b"truncated download")
        with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected download")):
            second = self.install("second")
        self.assertTrue(first.samefile(second))
        self.assertEqual(second.read_bytes(), self.content)

    def test_cross_filesystem_copy_is_complete_and_atomic(self):
        destination = self.root / "other-device" / "graphics.tar"
        with patch("fetch_baseset.os.link", side_effect=OSError("Cross-device link")):
            link_or_copy(self.seed, destination)
        self.assertEqual(destination.read_bytes(), self.content)
        self.assertFalse(destination.samefile(self.seed))
        self.assertEqual(list(destination.parent.iterdir()), [destination])

    def test_failed_download_preserves_existing_archive_and_cleans_temporary(self):
        destination = self.root / "destination" / "graphics.tar"
        destination.parent.mkdir()
        destination.write_bytes(b"previous archive")
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"bad response")):
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                fetch(destination.parent, cache=self.root / "cache", pin=self.pin)
        self.assertEqual(destination.read_bytes(), b"previous archive")
        self.assertEqual(list((self.root / "cache").iterdir()), [])


if __name__ == "__main__":
    unittest.main()

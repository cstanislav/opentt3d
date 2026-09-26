"""Regression tests for accepting only completely written game screenshots."""

from pathlib import Path
import random
import struct
import tempfile
import unittest
import zlib

from smoke import completed_png_size


def png_fixture():
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    width, height = 64, 32
    random_pixels = random.Random(314159)
    rows = b"".join(b"\0" + random_pixels.randbytes(width * 3) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows))
            + chunk(b"IEND", b""))


class ScreenshotCompletionTests(unittest.TestCase):
    def test_partial_write_is_not_a_completed_screenshot(self):
        image = png_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "screenshot.png"
            self.assertIsNone(completed_png_size(path))
            for end in (8, 20, len(image) // 2, len(image) - 12, len(image) - 1):
                path.write_bytes(image[:end])
                self.assertIsNone(completed_png_size(path))
            # A partial large file used to pass the old >1024-byte readiness test.
            self.assertGreater(path.stat().st_size, 1024)
            path.write_bytes(image)
            self.assertEqual(completed_png_size(path), (64, 32))

    def test_unrelated_file_is_not_a_screenshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "screenshot.png"
            path.write_bytes(b"not a PNG" * 2000)
            self.assertIsNone(completed_png_size(path))

    def test_damaged_end_marker_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "screenshot.png"
            image = png_fixture()
            path.write_bytes(image[:-1] + bytes([image[-1] ^ 1]))
            self.assertIsNone(completed_png_size(path))


if __name__ == "__main__":
    unittest.main()

"""Regression tests for accepting only completely written game screenshots."""

from pathlib import Path
import contextlib
import errno
import io
import random
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zlib

import smoke
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
    def test_failed_memory_report_still_reaps_the_live_child(self):
        child = subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                build = root / "build"
                build.mkdir()
                (build / ("opentt3d.exe" if sys.platform == "win32" else "opentt3d")).touch()
                monitor = mock.Mock()
                monitor.sample.side_effect = RuntimeError("sampled memory exceeded the limit")
                monitor.close.side_effect = OSError(errno.ENOSPC,"memory report disk is full")
                argv = ["smoke.py","--build-dir",str(build),"--output",str(root / "review"),"--memory-limit-mib","64","--timeout","2"]
                with mock.patch.object(sys,"argv",argv), mock.patch("smoke.subprocess.Popen",return_value=child), mock.patch("process_memory.MemoryMonitor",return_value=monitor):
                    with self.assertRaises(OSError) as raised:
                        smoke.main()
                self.assertEqual(raised.exception.errno,errno.ENOSPC)
                monitor.sample.assert_called_once_with(child.pid)
                self.assertIsNotNone(child.poll(),"A failed memory report must not orphan the native process")
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)

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


class ExplicitClearCommandTests(unittest.TestCase):
    def test_canal_gate_rejects_gallery_only_and_partial_live_evidence(self):
        gallery = "voxel mesh selection 'canal_dike' passed exact geometry, palettes and picking"
        with self.assertRaisesRegex(RuntimeError,"not captured"):
            smoke.require_live_canal_dikes(gallery,[0,3])
        first = "live voxel canal dike 0 climate 0 source 9808 captured at 44,28 with original ground ownership"
        with self.assertRaisesRegex(RuntimeError,r"\[3\]"):
            smoke.require_live_canal_dikes(gallery+first,[0,3])
        second = "live voxel canal dike 3 climate 0 source 9811 captured at 44,28 with original ground ownership"
        smoke.require_live_canal_dikes(first+"\n"+second,[0,3])

    def generated_script(self, *flags):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            (build / ("opentt3d.exe" if sys.platform == "win32" else "opentt3d")).touch()
            output = root / "review"
            argv = ["smoke.py", "--build-dir", str(build), "--output", str(output), *flags]
            with mock.patch.object(sys, "argv", argv), mock.patch("smoke.subprocess.Popen", side_effect=RuntimeError("stop before launch")) as launch:
                with self.assertRaisesRegex(RuntimeError, "stop before launch"):
                    smoke.main()
                launch.assert_called_once()
                return (output / "scripts/game_start.scr").read_text().splitlines(), launch.call_args.kwargs["env"]

    def test_original_object_export_does_not_create_objects_change_ratings_or_start_simulation(self):
        commands, env = self.generated_script("--export-objects", "--background")
        self.assertIn("renderer3d object-references", commands)
        self.assertEqual(commands.count("renderer3d object-references"), 1)
        self.assertNotIn("unpause", commands)
        self.assertFalse(any("build_object" in command or "rating" in command for command in commands))
        self.assertEqual(env["OPENTT3D_BACKGROUND"], "1")

    def test_catalogue_overview_is_read_only_and_retains_optional_prefix(self):
        for flags,command in (((),"renderer3d voxel-overview"),(("--gallery-voxel-prefix","bank"),"renderer3d voxel-overview bank")):
            commands,env = self.generated_script("--gallery-voxel-overview","--background",*flags)
            self.assertIn(command,commands)
            self.assertEqual(commands.count(command),1)
            self.assertNotIn("unpause",commands)
            self.assertEqual(env["OPENTT3D_BACKGROUND"],"1")

    def test_original_command_runs_after_gallery_with_explicit_draw_delay(self):
        commands, env = self.generated_script("--clear-tile", "64", "65", "--running", "--benchmark-frames", "240", "--gallery-voxel-prefix", "effect_explosion_small_")
        clear = "renderer3d clear-tile 64 65 60"
        self.assertLess(commands.index("renderer3d voxel-gallery effect_explosion_small_"), commands.index(clear))
        self.assertLess(commands.index(clear), commands.index("renderer3d benchmark 240 capture"))
        self.assertNotIn("setting construction.command_pause_level 3", commands)
        self.assertEqual(env["OPENTT3D_RENDERER"], "1")

    def test_paused_permission_is_explicit_and_classic_capture_keeps_renderer_off(self):
        commands, env = self.generated_script("--renderer", "classic", "--clear-tile", "64", "64", "--clear-tile-delay", "10", "--benchmark-frames", "75", "--allow-paused-clearing")
        self.assertEqual(commands[0], "pause")
        self.assertLess(commands.index("setting construction.command_pause_level 3"), commands.index("renderer3d clear-tile 64 64 10"))
        self.assertNotIn("renderer3d on", commands)
        self.assertNotIn("renderer3d zoom 1", commands)
        self.assertEqual(env["OPENTT3D_RENDERER"], "0")

    def test_invalid_clear_controls_fail_before_launch(self):
        cases = (("--clear-tile", "-1", "64"),
                 ("--clear-tile", "64", "64", "--menu"),
                 ("--clear-tile", "64", "64", "--benchmark-frames", "60"),
                 ("--clear-tile", "64", "64", "--clear-tile-delay", "3601"),
                 ("--clear-tile", "64", "64", "--benchmark-frames", "240", "--allow-paused-clearing", "--running"),
                 ("--clear-tile", "64", "64", "--executable", "external-openttd"))
        for flags in cases:
            with self.subTest(flags=flags), mock.patch.object(sys, "argv", ["smoke.py", "--build-dir", "missing", "--output", "unused", *flags]), mock.patch("smoke.subprocess.Popen") as launch, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    smoke.main()
                self.assertEqual(raised.exception.code, 2)
                launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()

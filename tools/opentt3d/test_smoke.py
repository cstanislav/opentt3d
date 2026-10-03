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
    def test_synchronous_save_checks_original_file_not_dedicated_server_console_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"fixture.sav"
            with self.assertRaisesRegex(RuntimeError,"did not complete"):
                smoke.require_synchronous_fixture_save(path)
            path.write_bytes(b"OTTX")
            with self.assertRaisesRegex(RuntimeError,"did not complete"):
                smoke.require_synchronous_fixture_save(path)
            for tag in (b"OTTD",b"OTTN",b"OTTZ",b"OTTX"):
                path.write_bytes(tag+bytes(100))
                smoke.require_synchronous_fixture_save(path)
            path.write_bytes(b"nope"+bytes(100))
            with self.assertRaisesRegex(RuntimeError,"format header"):
                smoke.require_synchronous_fixture_save(path)

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
    def test_object_palette_gate_never_splices_tiles_or_accepts_missing_phases(self):
        for kind,materials in ((0,2),(1,3)):
            text = f"focused voxel object {kind} size 0 at 44,28\nlive voxel object {kind} size 0 part 0 body climate 0 source 2600 captured at 44,28 with original body ownership\n"
            marker = f"voxel object palette observation passed: type {kind} tile 44,28, 4 original phases across {materials} emitted animated materials"
            smoke.require_object_palette(text+marker,kind)
            for invalid in ("",marker.replace("tile 44,28","tile 45,28"),marker.replace("4 original phases","3 original phases"),marker.replace(f"{materials} emitted","1 emitted")):
                with self.subTest(kind=kind,marker=invalid), self.assertRaisesRegex(RuntimeError,"palette observation incomplete"):
                    smoke.require_object_palette(text+invalid,kind)

    def test_object_gate_rejects_gallery_only_wrong_tile_and_wrong_layer_ownership(self):
        focus = "focused voxel object 2 size 0 at 44,28"
        body = "live voxel object 2 size 0 part 0 body climate 3 source 2632 captured at 44,28 with original body ownership"
        with self.assertRaisesRegex(RuntimeError,"not located"):
            smoke.require_live_voxel_object("voxel gallery object_company_gnome",2)
        for invalid in (focus,focus+body.replace("44,28","45,28"),focus+body.replace("original body ownership","original ground ownership")):
            with self.assertRaisesRegex(RuntimeError,"did not emit"):
                smoke.require_live_voxel_object(invalid,2)
        smoke.require_live_voxel_object(focus+body,2)

    def test_object_gate_retains_all_hq_tile_owners_and_intentional_body_absences(self):
        for size in range(5):
            text = f"focused voxel object 4 size {size} at 44,28\n"
            for part in range(4):
                text += f"live voxel object 4 size {size} part {part} ground climate 0 source 1000 captured at {44+part%2},{28+part//2} with original ground ownership\n"
            if size >= 2:
                with self.assertRaisesRegex(RuntimeError,"body"):
                    smoke.require_live_voxel_object(text,4)
                for part in range(3):
                    text += f"live voxel object 4 size {size} part {part} body climate 0 source 2000 captured at {44+part%2},{28+part//2} with original body ownership\n"
            smoke.require_live_voxel_object(text,4)
            with self.assertRaisesRegex(RuntimeError,"ground"):
                smoke.require_live_voxel_object(text.replace("part 3 ground","part 2 ground"),4)

    def test_canal_gate_rejects_gallery_only_and_partial_live_evidence(self):
        gallery = "voxel mesh selection 'canal_dike' passed exact geometry, palettes and picking"
        with self.assertRaisesRegex(RuntimeError,"not captured"):
            smoke.require_live_canal_dikes(gallery,[0,3])
        first = "live voxel canal dike 0 climate 0 source 9808 captured at 44,28 with original ground ownership"
        with self.assertRaisesRegex(RuntimeError,r"\[3\]"):
            smoke.require_live_canal_dikes(gallery+first,[0,3])
        second = "live voxel canal dike 3 climate 0 source 9811 captured at 44,28 with original ground ownership"
        smoke.require_live_canal_dikes(first+"\n"+second,[0,3])

    def generated_script(self, *flags, host=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            platform = host or smoke.platform.system()
            (build / ("opentt3d.exe" if platform == "Windows" else "opentt3d")).touch()
            output = root / "review"
            argv = ["smoke.py", "--build-dir", str(build), "--output", str(output), *flags]
            with mock.patch("smoke.platform.system",return_value=platform), mock.patch.object(sys, "argv", argv), mock.patch("smoke.subprocess.Popen", side_effect=RuntimeError("stop before launch")) as launch:
                with self.assertRaisesRegex(RuntimeError, "stop before launch"):
                    smoke.main()
                launch.assert_called_once()
                self.launched_command = launch.call_args.args[0]
                self.generated_config = (output / "openttd.cfg").read_text()
                return (output / "scripts/game_start.scr").read_text().splitlines(), launch.call_args.kwargs["env"]

    def test_original_object_export_does_not_create_objects_change_ratings_or_start_simulation(self):
        for host in ("Darwin","Linux","Windows"):
            with self.subTest(host=host):
                flags = ("--background",) if host == "Darwin" else ()
                commands, env = self.generated_script("--export-objects",*flags,host=host)
                self.assertIn("renderer3d object-references", commands)
                self.assertEqual(commands.count("renderer3d object-references"), 1)
                self.assertNotIn("unpause", commands)
                self.assertFalse(any("build_object" in command or "rating" in command for command in commands))
                if host == "Darwin": self.assertEqual(env["OPENTT3D_BACKGROUND"], "1")

    def test_explicit_alternate_graphics_does_not_test_saved_setting_migration(self):
        self.generated_script("--graphics","OpenGFX2 High Def","--export-objects")
        index = self.launched_command.index("-I")
        self.assertEqual(self.launched_command[index+1],"OpenGFX2 High Def")
        self.generated_script("--graphics-from-config","OpenGFX2 High Def","--export-objects")
        self.assertNotIn("-I",self.launched_command)

    def test_explicit_and_saved_graphics_selection_are_mutually_exclusive(self):
        arguments = ["smoke.py","--build-dir","unused","--output","unused","--graphics","OpenGFX2 High Def","--graphics-from-config","OpenGFX2 Classic"]
        with mock.patch.object(sys,"argv",arguments), contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit) as stopped:
            smoke.main()
        self.assertEqual(stopped.exception.code,2)
        self.assertIn("not allowed with argument",error.getvalue())

    def test_exact_fixture_saving_uses_original_io_setting_not_simulation_changes(self):
        commands,env = self.generated_script("--synchronous-save")
        self.assertIn("threaded_saves = false",self.generated_config)
        self.assertIn("save smoke-state",commands)
        self.assertNotIn("unpause",commands)
        self.generated_script()
        self.assertIn("threaded_saves = true",self.generated_config)

    def test_live_object_reference_is_a_read_only_focus_not_object_construction(self):
        commands,env = self.generated_script("--reference-object","2","--background",host="Darwin")
        self.assertIn("renderer3d object-locate 2",commands)
        self.assertEqual(commands.count("renderer3d object-locate 2"),1)
        self.assertNotIn("unpause",commands)
        self.assertFalse(any("build_object" in command or "rating" in command for command in commands))
        self.assertEqual(env["OPENTT3D_BACKGROUND"],"1")
        commands,env = self.generated_script("--reference-object","3","--reference-object-tile","45","8")
        self.assertIn("renderer3d object-locate 3 45 8",commands)
        self.assertNotIn("unpause",commands)

    def test_landmark_palette_script_observes_real_simulation_without_forcing_clock_or_paint(self):
        for kind in (0,1):
            commands,env = self.generated_script("--reference-object",str(kind),"--verify-object-palette",str(kind),"--running","--benchmark-frames","240","--blitter","40bpp-anim")
            self.assertLess(commands.index(f"renderer3d object-locate {kind}"),commands.index(f"renderer3d verify-object-palette {kind}"))
            self.assertIn("unpause",commands)
            self.assertFalse(any("build_object" in command or "rating" in command or "set_palette" in command for command in commands))

    def test_landmark_palette_rejects_the_non_animating_blitter_before_starting(self):
        arguments = ["smoke.py","--build-dir","unused","--output","unused","--reference-object","0","--verify-object-palette","0","--running","--benchmark-frames","240"]
        with mock.patch.object(sys,"argv",arguments), contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit) as stopped:
            smoke.main()
        self.assertEqual(stopped.exception.code,2)
        self.assertIn("--blitter 40bpp-anim",error.getvalue())

    def test_catalogue_overview_is_read_only_and_retains_optional_prefix(self):
        for host in ("Darwin","Linux","Windows"):
            for flags,command in (((),"renderer3d voxel-overview"),(("--gallery-voxel-prefix","bank"),"renderer3d voxel-overview bank")):
                with self.subTest(host=host,prefix=flags):
                    background = ("--background",) if host == "Darwin" else ()
                    commands,env = self.generated_script("--gallery-voxel-overview",*background,*flags,host=host)
                    self.assertIn(command,commands)
                    self.assertEqual(commands.count(command),1)
                    self.assertNotIn("unpause",commands)
                    if host == "Darwin": self.assertEqual(env["OPENTT3D_BACKGROUND"],"1")

    def test_background_platform_guard_is_not_relaxed_for_portable_script_tests(self):
        for host in ("Linux","Windows"):
            with self.subTest(host=host), mock.patch("smoke.platform.system",return_value=host), mock.patch.object(sys,"argv",["smoke.py","--build-dir","unused","--output","unused","--background"]), mock.patch("smoke.subprocess.Popen") as launch, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    smoke.main()
                self.assertEqual(raised.exception.code,2)
                launch.assert_not_called()

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

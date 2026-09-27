#!/usr/bin/env python3
"""Launch an extracted release with only its own resources and default 3D settings."""

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

from smoke import completed_png_size


def verify(package, output, driver=None, *, headless=False, without_vulkan_device=False):
    package, output = Path(package).resolve(), Path(output).resolve()
    is_mac = package.suffix == ".app"
    resources = package / "Contents/Resources" if is_mac else package
    executable = (package / "Contents/MacOS/opentt3d" if is_mac else
                  package / ("opentt3d.exe" if platform.system() == "Windows" else "opentt3d.sh"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "scripts").mkdir()
    (output / "scripts/game_start.scr").write_text(
        "pause\nsave package-smoke\nquit\n" if headless else
        # A close, small viewport also exercises hosted macOS's software OpenGL.
        # Keep ordinary default renderer selection and the complete title save;
        # this checks package startup/resources, not wide-scene performance.
        "pause\nscrollto instant 64 64\nrenderer3d zoom -2\nrenderer3d benchmark 3 capture\nsave package-smoke\n")
    (output / "openttd.cfg").write_text(
        "[misc]\nlanguage = english.lng\nfullscreen = false\nresolution = 640,480\n"
        "screenshot_format = png\n[gui]\nautosave_interval = 0\nrefresh_rate = 60\n")
    shutil.copyfile(resources / "baseset/opntitle.dat", output / "input.sav")
    # Upstream -X also excludes a macOS app's Resources directory. Exercise the
    # normal bundle lookup there, with an empty personal-data directory instead.
    command = [str(executable), "-c", str(output / "openttd.cfg"), "-x", *([] if is_mac else ["-X"]),
               "-s", "null", "-m", "null", "-S", "NoSound", "-M", "NoMusic",
               "-d", "driver=2,console=1", "-g", str(output / "input.sav")]
    if headless:
        command.extend(["-v", "null"])
    elif driver:
        command.extend(["-v", driver])
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("OPENTT3D_") and k not in ("DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "LD_LIBRARY_PATH")}
    env["OPENTT3D_ALLOW_SOFTWARE_GL"] = "1"
    (output / "home").mkdir()
    env["HOME"] = str(output / "home")
    if without_vulkan_device:
        if platform.system() != "Linux" or driver or headless:
            raise ValueError("The absent-Vulkan-device check requires automatic Linux video selection")
        env["VK_DRIVER_FILES"] = env["VK_ICD_FILENAMES"] = str(output / "absent-vulkan-driver.json")
    if is_mac:
        env["OPENTT3D_BACKGROUND"] = "1"
    log_path = output / "run.log"
    with log_path.open("w") as log:
        if headless:
            subprocess.run(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=120, check=True)
            saved = output / "save/package-smoke.sav"
            if not saved.is_file() or saved.stat().st_size < 100:
                raise RuntimeError(f"Extracted game did not load and re-save its title world: {log_path}")
            (output / "result.json").write_text(json.dumps(
                {"native_load_save": True, "package": str(package), "command": command}, indent=2) + "\n")
            print(f"Extracted package native load/save passed: {package}")
            return
        process = subprocess.Popen(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                text = log_path.read_text(errors="replace")
                if process.poll() is not None:
                    raise RuntimeError(f"Packaged game exited ({process.returncode}): {log_path}")
                errors = (re.sub(r"^.*OpenTT3D: Vulkan rendering failed:.*$", "", text, flags=re.MULTILINE)
                          if without_vulkan_device else text)
                if re.search(r"Crash encountered|Assertion failed|uncaught exception|OpenTT3D: .*failed", errors):
                    raise RuntimeError(f"Packaged game failed: {log_path}")
                if (completed_png_size(output / "screenshot/smoke.png") and
                        (output / "benchmark.json").is_file() and
                        (output / "save/package-smoke.sav").is_file()):
                    break
                time.sleep(0.25)
            else:
                if is_mac:
                    # Preserve a real startup hang before reaping the process;
                    # a two-line driver log alone cannot identify AppKit/GL waits.
                    with (output / "sample-driver.log").open("w") as sample_log:
                        try:
                            subprocess.run(["/usr/bin/sample", str(process.pid), "3", "-file", str(output / "sample.txt")],
                                           stdout=sample_log, stderr=subprocess.STDOUT, timeout=20, check=False)
                        except subprocess.TimeoutExpired:
                            sample_log.write("Process sampling timed out.\n")
                raise TimeoutError(f"Packaged game did not render and save: {log_path}")
            if not re.search(r"captured (?:OpenGL|Vulkan) presentation with [1-9]\d* GPU viewport regions", text):
                raise RuntimeError(f"Default launch did not present a 3D viewport: {log_path}")
            if without_vulkan_device and not (
                    "Probing video driver 'sdl-vulkan' failed" in text and
                    "Successfully probed video driver 'sdl-opengl'" in text and
                    "captured OpenGL presentation" in text):
                raise RuntimeError(f"Missing Vulkan device did not fall back to working OpenGL: {log_path}")
            if is_mac and "background Cocoa window active=false, key=false, visible=false, policy=2" not in text:
                raise RuntimeError("Package launch was not hidden and nonactivating")
            result = {"default_3d": True, "rendered_and_saved": True, "package": str(package),
                      "driver_override": driver, "without_vulkan_device": without_vulkan_device, "command": command,
                      "benchmark": json.loads((output / "benchmark.json").read_text())}
            (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(f"Packaged default 3D launch, GPU presentation and save passed: {package}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--driver")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    verify(args.package, args.output, args.driver, headless=args.headless)

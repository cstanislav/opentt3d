#!/usr/bin/env python3
"""Launch the native game with isolated data and capture its own framebuffer.

Uses upstream console scripts and screenshot support. No GUI automation,
screen-recording permission, external Python packages, or host installation.
"""

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--renderer", choices=("classic", "3d"), default="3d")
    parser.add_argument("--rotation", type=int, choices=range(4), default=0)
    parser.add_argument("--year", type=int, default=1950)
    parser.add_argument("--savegame", type=Path)
    parser.add_argument("--executable", type=Path, help="Override game executable, for official upstream interoperability checks")
    parser.add_argument("--reference-model", action="store_true")
    parser.add_argument("--blitter", choices=("32bpp-optimized", "40bpp-anim"), default="32bpp-optimized")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()
    build = args.build_dir.resolve()
    output = args.output.resolve()
    executable = args.executable.resolve() if args.executable else build / ("openttd.exe" if platform.system() == "Windows" else "openttd")
    if not executable.is_file():
        parser.error(f"Missing executable: {executable}")
    if output.exists():
        parser.error("Use a new output directory to avoid confusing stale screenshots with a successful run")
    output.mkdir(parents=True)
    scripts = output / "scripts"
    scripts.mkdir()
    if args.executable:
        # Stock binaries have their own bundled fonts/languages. Supply only the
        # pinned OpenGFX pack via this isolated test's data directory.
        (output / "baseset").mkdir()
        resources = executable.parent.parent / "Resources"
        if resources.is_dir():
            shutil.copytree(resources / "baseset", output / "baseset", dirs_exist_ok=True)
            shutil.copytree(resources / "lang", output / "lang")
        shutil.copy2(build / "baseset" / "opengfx-8.0.tar", output / "baseset")
    driver = {"Darwin": "cocoa-opengl", "Windows": "win32-opengl"}.get(platform.system(), "sdl-opengl")
    (output / "openttd.cfg").write_text("""[misc]
language = english.lng
display_opt = SHOW_TOWN_NAMES|SHOW_STATION_NAMES|SHOW_SIGNS|FULL_ANIMATION|FULL_DETAIL|WAYPOINTS
fullscreen = false
resolution = 1280,800
screenshot_format = png

[gui]
autosave_interval = 0
show_finances = false
refresh_rate = 30

[game_creation]
map_x = 7
map_y = 7
starting_year = 1950
generation_seed = 314159

[network]
server_advertise = false
""")
    commands = ["pause", "scrollto 64 64"]
    if args.renderer == "3d":
        commands.append("renderer3d on")
        commands.extend(["renderer3d right"] * args.rotation)
    if args.reference_model:
        commands.append("renderer3d locate")
    commands.append("zoomto 1")
    commands.extend(["save smoke-state", "screenshot viewport smoke"])
    (scripts / "game_start.scr").write_text("\n".join(commands) + "\n")
    command = [str(executable), "-c", str(output / "openttd.cfg"), "-x", "-X",
               "-v", driver, "-b", args.blitter, "-s", "null", "-m", "null",
               "-I", "OpenGFX", "-S", "NoSound", "-M", "NoMusic", "-r", "1280x800", "-d", "driver=2,console=1", "-G", "314159", "-t", str(args.year), "-g"]
    if args.savegame:
        command.append(str(args.savegame.resolve()))
    env = dict(os.environ, OPENTT3D_RENDERER="1" if args.renderer == "3d" else "0", OPENTT3D_ALLOW_SOFTWARE_GL="1")
    screenshot = output / "screenshot" / "smoke.png"
    with (output / "run.log").open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Game exited with {process.returncode}; see {output / 'run.log'}")
                if screenshot.exists() and screenshot.stat().st_size > 1024:
                    time.sleep(1)  # Let the screenshot writer finish.
                    break
                time.sleep(0.25)
            else:
                raise TimeoutError(f"No screenshot after {args.timeout}s; see {output / 'run.log'}")
            log.flush()
            text = (output / "run.log").read_text()
            if args.renderer == "3d" and "OpenTT3D: depth-tested mesh renderer initialized" not in text:
                raise RuntimeError("3D backend did not initialize; a classic-renderer fallback is not a passing smoke test")
            if "OpenTT3D: OpenGL rendering failed" in text or "Assertion failed" in text:
                raise RuntimeError("Rendering error; inspect run.log")
            result = {"renderer": args.renderer, "rotation": args.rotation, "platform": platform.platform(),
                      "screenshot": str(screenshot), "command": command, "pid": process.pid}
            (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, indent=2))
            if args.keep_open:
                return
        finally:
            if not args.keep_open or not screenshot.exists():
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    main()

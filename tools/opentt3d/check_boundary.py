#!/usr/bin/env python3
"""Check that the fork's engine delta stays inside reviewed presentation files.

This is a file-level regression guard, not a substitute for simulation/replay
tests or code review of the mixed presentation/simulation files in the allowlist.
"""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PRESENTATION_FILES = {
    "src/CMakeLists.txt", "src/console_cmds.cpp", "src/main_gui.cpp",
    "src/vehicle.cpp", "src/viewport.cpp", "src/viewport_gui.cpp", "src/window.cpp",
    "src/video/opengl.cpp", "src/video/opengl.h", "src/video/video_driver.cpp",
    "src/video/sdl2_opengl_v.cpp",  # GPU-resident viewport/UI composition and upload ordering.
    "src/spritecache.cpp", "src/screenshot.cpp", "src/screenshot.h",
    "src/gfx.cpp", "src/gfx_func.h", "src/video/cocoa/cocoa_wnd.mm",
    "src/video/sdl2_v.cpp", "src/video/win32_v.cpp",
    "src/video/cocoa/cocoa_v.mm", "src/vehicle_gui.cpp", "src/widgets/vehicle_widget.h",
    "src/lang/english.txt",
    "src/intro_gui.cpp",
    "src/os/windows/ottdres.rc.in",
    "src/misc_gui.cpp", "src/help_gui.cpp",
    "src/network/network_survey.h",  # Fork service branding; existing disabled-service path.
    "src/video/cocoa/cocoa_ogl.mm",
    "src/video/cocoa/cocoa_v.h",
    "src/video/cocoa/cocoa_wnd.h", "src/video/video_driver.hpp", "src/window_func.h",  # Native input/focus recovery.
    "src/blitter/32bpp_base.hpp", "src/video/CMakeLists.txt", "src/video/cocoa/CMakeLists.txt",
    "src/video/cocoa/cocoa_vulkan.h", "src/video/cocoa/cocoa_vulkan.mm",
    "src/video/sdl2_vulkan_v.h", "src/video/sdl2_vulkan_v.cpp",
    "src/palette.cpp", "src/palette_func.h",
    "src/bridge.h", "src/tunnelbridge_cmd.cpp",  # Resolved bridge presentation/capture only.
    "src/clear_cmd.cpp", "src/rail_cmd.cpp",  # Terrain-following fence drawing; no game commands changed.
    "src/landscape.cpp",  # Foundation drawing adapter only.
    "src/station_cmd.cpp",  # Vanilla station drawing adapter after upstream foundation selection.
    "src/station_func.h",  # Read-only vanilla airport animation layout access.
    "src/elrail.cpp",  # Resolved overhead-wire and pylon drawing metadata only.
    "src/road_cmd.h", "src/road_cmd.cpp",  # Read-only road drawing layouts and presentation adapters.
    "src/water_cmd.cpp",  # Ship-depot body drawing adapter after original water-class ground selection.
    "src/openttd.cpp",  # Default Classic graphics selection / former High Def recommendation migration.
    "src/texteff.cpp", "src/texteff.hpp",  # World-anchored text-effect presentation only.
    "src/os/macosx/CMakeLists.txt", "src/os/macosx/autorelease_pool.hpp", "src/os/macosx/macos.mm",  # Scoped MoltenVK readback temporary ownership only.
}


def main():
    pin = json.loads((ROOT / "opentt3d/upstream.json").read_text())["openttd"]
    commit = subprocess.check_output(["git", "rev-parse", f"{pin['tag']}^{{commit}}"], cwd=ROOT, text=True).strip()
    if commit != pin["commit"]:
        raise SystemExit("Upstream tag no longer resolves to the pinned commit")
    changed = subprocess.check_output(["git", "diff", "--name-only", pin["commit"], "--", "src"], cwd=ROOT, text=True).splitlines()
    changed += subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "--", "src"], cwd=ROOT, text=True).splitlines()
    changed = sorted(set(changed))
    unexpected = [p for p in changed if p not in PRESENTATION_FILES and not p.startswith("src/renderer3d/")]
    if unexpected:
        print("Changes outside the rendering integration boundary:\n" + "\n".join(unexpected), file=sys.stderr)
        return 1
    print(f"OpenTTD {pin['tag']} boundary checked: {len(changed)} changed source files, all within the reviewed presentation boundary")
    return 0


if __name__ == "__main__":
    sys.exit(main())

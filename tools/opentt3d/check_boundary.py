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
    "src/video/opengl.cpp", "src/video/video_driver.cpp",
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

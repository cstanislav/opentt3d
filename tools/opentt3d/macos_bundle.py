#!/usr/bin/env python3
"""Assemble a build-local macOS app for LaunchServices input/lifecycle testing.

Resources are linked to the current build and dependencies retain their build
paths. This is a development runner, not a distributable release package.
"""

import argparse
from pathlib import Path
import platform
import plistlib

from fetch_baseset import link_or_copy


def assemble(build):
    build = Path(build).resolve()
    executable = build / "opentt3d"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    bundle = build / "OpenTT3D.app"
    contents = bundle / "Contents"
    resources = contents / "Resources"
    resources.mkdir(parents=True, exist_ok=True)
    link_or_copy(executable, contents / "MacOS/opentt3d")
    for name in ("baseset", "lang", "ai", "game"):
        destination = resources / name
        if destination.is_symlink() and destination.readlink() != build / name:
            destination.unlink()
        if not destination.exists():
            destination.symlink_to(build / name, target_is_directory=True)
    link_or_copy(build / "baseset/opentt3d.icns", resources / "OpenTT3D.icns")
    info = {
        "CFBundleIdentifier": "org.opentt3d.development",
        "CFBundleName": "OpenTT3D", "CFBundleDisplayName": "OpenTT3D",
        "CFBundleExecutable": "opentt3d", "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.2.0", "CFBundleVersion": "0.2.0",
        "CFBundleIconFile": "OpenTT3D.icns", "NSPrincipalClass": "NSApplication",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": platform.mac_ver()[0],
        "LSApplicationCategoryType": "public.app-category.simulation-games",
    }
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    print(assemble(parser.parse_args().build))

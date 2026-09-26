#!/usr/bin/env python3
"""Build and test without installing dependencies on the host."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 2, 8))
    parser.add_argument("--configure-only", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    build = args.build_dir.resolve()
    if build == source:
        parser.error("Choose an out-of-source build directory")
    if args.jobs < 1:
        parser.error("--jobs must be positive")

    subprocess.run([
        "cmake", "-S", str(source), "-B", str(build),
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo", "-DOPTION_USE_ASSERTS=ON",
        "-DCMAKE_DISABLE_FIND_PACKAGE_Grfcodec=ON",
    ], check=True)
    if args.configure_only:
        return
    subprocess.run(["cmake", "--build", str(build), "--parallel", str(args.jobs)], check=True)
    pin = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())
    baseset = build / "baseset" / pin["graphics"]["filename"]
    if not baseset.is_file():
        subprocess.run([sys.executable, str(Path(__file__).with_name("fetch_baseset.py")), str(build / "baseset")], check=True)
    subprocess.run(["ctest", "--test-dir", str(build), "--output-on-failure"], check=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)

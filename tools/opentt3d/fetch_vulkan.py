#!/usr/bin/env python3
"""Fetch the pinned macOS Vulkan implementation into a build-local directory."""

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    pin = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())["moltenvk"]
    target = args.directory.resolve()
    target.mkdir(parents=True, exist_ok=True)
    archive = target / pin["filename"]
    if not archive.is_file():
        request = urllib.request.Request(pin["url"], headers={"User-Agent": "OpenTT3D-build"})
        with tempfile.NamedTemporaryFile(dir=target, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            try:
                with urllib.request.urlopen(request, timeout=120) as source:
                    while chunk := source.read(1024 * 1024):
                        temporary.write(chunk)
                temporary.flush()
            except BaseException:
                temporary_path.unlink(missing_ok=True)
                raise
        archive = temporary_path
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != pin["sha256"]:
        raise SystemExit(f"MoltenVK checksum mismatch: {digest}")
    pinned_archive = target / pin["filename"]
    if archive != pinned_archive:
        archive.replace(pinned_archive)
    with tarfile.open(pinned_archive) as source:
        source.extractall(target, filter="data")
    print(f"Verified and extracted {pin['tag']} to {target}")


if __name__ == "__main__":
    main()

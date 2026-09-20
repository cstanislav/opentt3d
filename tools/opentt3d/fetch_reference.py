#!/usr/bin/env python3
"""Fetch the checksum-pinned, official macOS 15.3 build for interoperability tests."""

import argparse
import hashlib
from pathlib import Path
import platform
import subprocess
import urllib.request

URL = "https://cdn.openttd.org/openttd-releases/15.3/openttd-15.3-macos-universal.zip"
SHA256 = "c2ac22ab3ac9ac1e82a8d9029b7e4ab069e425904420076605d860e64460f579"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("This reference package is for native macOS tests")
    destination = args.destination.resolve()
    if destination.exists():
        parser.error("Choose a new destination")
    request = urllib.request.Request(URL, headers={"User-Agent": "OpenTT3D/0.1.0 (compatibility testing)"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise SystemExit("Official OpenTTD reference package checksum mismatch")
    destination.mkdir(parents=True)
    archive = destination / "openttd-15.3-macos-universal.zip"
    archive.write_bytes(data)
    subprocess.run(["ditto", "-x", "-k", str(archive), str(destination)], check=True)
    print(f"Official OpenTTD 15.3 verified and extracted to {destination}")


if __name__ == "__main__":
    main()

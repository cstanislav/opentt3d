#!/usr/bin/env python3
"""Install the pinned OpenGFX release into a build-local baseset directory."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    pin = json.loads((root / "opentt3d/upstream.json").read_text())["opengfx"]
    request = urllib.request.Request(pin["url"], headers={
        "User-Agent": "OpenTT3D/0.1.0 (https://github.com/cstanislav/opentt3d)",
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != pin["sha256"]:
        raise SystemExit(f"OpenGFX checksum mismatch: expected {pin['sha256']}, got {actual}")
    destination = args.destination.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination):
                raise SystemExit(f"Invalid archive path: {member.filename}")
        destination.mkdir(parents=True, exist_ok=True)
        archive.extractall(destination)
    print(f"OpenGFX {pin['tag']} verified and installed in {destination}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch the pinned OpenGFX2 Classic base set, streaming and checking its digest."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request


def link_or_copy(source, target):
    """Atomically share immutable data on one filesystem; copy across devices."""
    source, target = Path(source), Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and source.samefile(target):
        return
    descriptor, name = tempfile.mkstemp(prefix=".opentt3d-", dir=target.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.unlink()
        try:
            os.link(source, temporary)
        except OSError:
            shutil.copy2(source, temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def verified(path, digest):
    if not path.is_file():
        return False
    with path.open("rb") as existing:
        return hashlib.file_digest(existing, "sha256").hexdigest() == digest


def fetch(destination, *, seed=None, cache=None, pin=None):
    root = Path(__file__).resolve().parents[2]
    if pin is None:
        pin = json.loads((root / "opentt3d/upstream.json").read_text())["graphics"]
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / pin["filename"]
    cache = Path(cache) if cache is not None else root / ".opentt3d-local/downloads"
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / (pin["sha256"] + "-" + pin["filename"])
    cache_valid = verified(cached, pin["sha256"])
    if not cache_valid:
        for candidate in (target, Path(seed) if seed is not None else target):
            if verified(candidate, pin["sha256"]):
                link_or_copy(candidate, cached)
                cache_valid = True
                break
    if cache_valid:
        link_or_copy(cached, target)
        print(f"Verified shared {target}")
        return target
    request = urllib.request.Request(pin["url"], headers={"User-Agent": "OpenTT3D/0.2.0 (https://github.com/cstanislav/opentt3d)"})
    temporary = None
    try:
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=120) as response, tempfile.NamedTemporaryFile(dir=cache, delete=False) as output:
            temporary = Path(output.name)
            while block := response.read(1024 * 1024):
                digest.update(block)
                output.write(block)
        if digest.hexdigest() != pin["sha256"]:
            raise ValueError(f"Graphics checksum mismatch: {digest.hexdigest()}")
        temporary.replace(cached)
        temporary = None
        link_or_copy(cached, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"{pin['name']} {pin['tag']} verified and installed in {target}")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--seed", type=Path, help="Use an existing verified archive instead of downloading it again")
    args = parser.parse_args()
    fetch(args.destination, seed=args.seed)


if __name__ == "__main__":
    main()

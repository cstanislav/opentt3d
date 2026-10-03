#!/usr/bin/env python3
"""Build sea-level/elevated original locks at natural slopes, with acknowledged saves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time

from fetch_baseset import fetch


def validate_manifest(row):
    if not isinstance(row, dict) or type(row.get("company")) is not int or row["company"] < 0:
        raise ValueError("Missing original lock company")
    width, height = row.get("map_width"), row.get("map_height")
    if any(type(value) is not int or value < 16 for value in (width, height)):
        raise ValueError("Missing integral original map dimensions")
    locks = row.get("locks")
    if not isinstance(locks, list) or len(locks) != 8:
        raise ValueError("All four directions and two natural elevations are required")
    found, occupied = set(), set()
    for lock in locks:
        if not isinstance(lock, dict) or any(type(lock.get(key)) is not int for key in ("tile", "x", "y", "direction", "elevation", "height", "lower", "upper")):
            raise ValueError("Lock site metadata must be exact integers")
        direction, elevation = lock["direction"], lock["elevation"]
        if direction not in range(4) or elevation not in range(2) or (elevation == 0 and lock["height"] != 0) or (elevation == 1 and lock["height"] <= 0):
            raise ValueError("Invalid natural original lock elevation/direction")
        if (elevation, direction) in found or lock.get("connected_both_ways") is not True:
            raise ValueError("Missing original bidirectional lock connectivity or duplicate selector")
        delta = (-1, width, 1, -width)[direction]
        if not (4 <= lock["x"] < width-4 and 4 <= lock["y"] < height-4) or lock["tile"] != lock["x"]+width*lock["y"]:
            raise ValueError("Original lock tile registration differs")
        tiles = {lock["lower"], lock["tile"], lock["upper"]}
        if lock["lower"] != lock["tile"]-delta or lock["upper"] != lock["tile"]+delta or len(tiles) != 3 or occupied & tiles:
            raise ValueError("Original three-part lock sites overlap or have wrong direction")
        occupied.update(tiles)
        found.add((elevation, direction))
    return row


def verify_save(path):
    if not path.is_file() or path.stat().st_size <= 100 or path.read_bytes()[:4] not in (b"OTTZ", b"OTTX", b"OTTN", b"OTTD"):
        raise ValueError("Missing or incomplete acknowledged original save")
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--climate", choices=("temperate", "arctic", "tropic", "toyland"), default="temperate")
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = args.executable.resolve() if args.executable else build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists():
        parser.error("Use a built executable and a new output directory to retain failed sites/saves")
    if args.timeout < 1 or not 0 <= args.seed <= 0xffffffff:
        parser.error("Use a positive timeout and an original unsigned map seed")
    graphics = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "locks", output / "ai/lock-fixture")
    # -X uses the isolated config directory for data. An external Mac app's
    # dedicated executable does not automatically search its Resources folder.
    if (build / "lang").is_dir():
        shutil.copytree(build / "lang", output / "lang")
    fetch(output / "baseset", seed=build / "baseset" / graphics["filename"])
    for source in (build / "baseset").iterdir():
        if source.is_file() and source.suffix in (".grf", ".obs", ".obm", ".ttf", ".obg"):
            shutil.copy2(source, output / "baseset" / source.name)
    (output / "openttd.cfg").write_text(f"""[misc]
language = english.lng
[gui]
autosave_interval = 0
threaded_saves = false
[game_creation]
map_x = 7
map_y = 7
starting_year = 1950
generation_seed = {args.seed}
landscape = {args.climate}
land_generator = 1
custom_sea_level = 12
custom_town_number = 1
amount_of_rivers = 2
[difficulty]
terrain_type = 0
quantity_sea_lakes = 4
number_towns = 4
industry_density = 0
max_loan = 50000000
[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
""")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [str(executable), "-D", f"127.0.0.1:{port}", "-c", str(output / "openttd.cfg"), "-x", "-X",
               "-s", "null", "-m", "null", "-I", graphics["name"], "-S", "NoSound", "-M", "NoMusic",
               "-d", "script=4,console=1,net=3", "-G", str(args.seed), "-t", "1950", "-g"]
    logfile = output / "run.log"
    acknowledgements = []
    with logfile.open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=dict(os.environ, OPENTT3D_RENDERER="0", OPENTT3D_BACKGROUND="1"),
                                   stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
        deadline = time.monotonic() + args.timeout

        def observe(pattern, start=0, timeout=None, allow_failed=False):
            until = deadline if timeout is None else min(deadline, time.monotonic()+timeout)
            while time.monotonic() < until:
                text = logfile.read_text()
                if process.poll() is not None or (not allow_failed and ("LOCK_FIXTURE_FAILED" in text or "script died unexpectedly" in text)):
                    raise RuntimeError(f"Original lock fixture failed; inspect {logfile}")
                match = re.search(pattern, text[start:])
                if match:
                    return match
                time.sleep(0.1)
            raise TimeoutError(f"No acknowledgement for {pattern}; inspect {logfile}")

        def send(value, acknowledgement, timeout=None, allow_failed=False):
            start = len(logfile.read_text())
            process.stdin.write(value + "\n")
            process.stdin.flush()
            match = observe(acknowledgement, start, timeout, allow_failed)
            acknowledgements.append({"command": value, "acknowledgement": match[0]})
            (output / "command-acknowledgements.json").write_text(json.dumps(acknowledgements, indent=2) + "\n")
            return match

        try:
            observe(r"Listening on 127\.0\.0\.1:")
            send("unpause", r"Game (?:is already unpaused|unpaused|still paused)")
            ready = send('start_ai "OpenTT3D Original Lock Fixture"', r"LOCK_FIXTURE_READY (\{[^\n]+\})")
            manifest = validate_manifest(json.loads(ready[1]))
            send("pause", r"Game (?:paused|is already paused)")
            send("save lock-fixture", r"Map successfully saved to 'lock-fixture\.sav'\.", timeout=30)
            save = output / "save/lock-fixture.sav"
            manifest.update(climate=args.climate, seed=args.seed, save="save/lock-fixture.sav", save_sha256=verify_save(save),
                source="Original public AIMarine.BuildLock at preexisting inclined terrain; no terraform or forced state.",
                source_height_units="Original map height levels, not doubled rendered terrain heights.",
                simulation_mutations="Original company-name/loan/build-lock commands only; normal simulation and RNG.",
                geometry_or_quality_approved=False, ship_traversal_verified=False, command=command)
            (output / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n")
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.wait(timeout=15)
        except (RuntimeError, TimeoutError, ValueError):
            if process.poll() is None:
                # Preserve whatever the original public commands actually built.
                deadline = max(deadline, time.monotonic()+30)
                send("pause", r"Game (?:paused|is already paused)", timeout=10, allow_failed=True)
                send("save failed-fixture", r"Map successfully saved to 'failed-fixture\.sav'\.", timeout=20, allow_failed=True)
                verify_save(output / "save/failed-fixture.sav")
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print(json.dumps({"savegame": str(save), "locks": 8, "source": manifest["source"], "approved": False}))


if __name__ == "__main__":
    main()

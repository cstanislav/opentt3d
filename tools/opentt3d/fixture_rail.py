#!/usr/bin/env python3
"""Build a live electric-rail review save through the unmodified public NoAI API."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    airports = ("commuter", "city", "metropolitan", "international", "intercontinental")
    parser.add_argument("--airport", choices=airports, default="commuter", help="Choose the main review airport through an ordinary NoAI setting")
    parser.add_argument("--aircraft", action="store_true", help="Build a small passenger plane and require service at both airports through public NoAI commands")
    parser.add_argument("--aircraft-hold", action="store_true", help="Keep the verified returning plane loading at its main-airport stand for geometry review")
    parser.add_argument("--train-engine", type=int, choices=range(116), help="Select an available vanilla electric locomotive through the public NoAI engine list")
    parser.add_argument("--train-hold", action="store_true", help="Stop the verified train near the east terminus with an ordinary public vehicle command")
    args = parser.parse_args()
    if args.aircraft_hold and not args.aircraft:
        parser.error("--aircraft-hold requires --aircraft")
    year = 2005 if args.airport == "intercontinental" else 2000
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file():
        parser.error(f"Missing executable: {executable}")
    if output.exists():
        parser.error("Use a new output directory")
    graphics = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "rail", output / "ai/rail-fixture")
    (output / "scripts").mkdir()
    (output / "openttd.cfg").write_text(f"""[misc]
language = english.lng
[gui]
autosave_interval = 0
[game_creation]
map_x = 7
map_y = 7
starting_year = {year}
generation_seed = 314159
landscape = temperate
land_generator = 1
custom_sea_level = 1
custom_town_number = 1
amount_of_rivers = 0
[difficulty]
terrain_type = 0
quantity_sea_lakes = 4
number_towns = 4
industry_density = 0
max_loan = 50000000
town_council_tolerance = 0
vehicle_breakdowns = 0
[station]
never_expire_airports = true
[construction]
terraform_per_64k_frames = 1000000
terraform_frame_burst = 4096
[vehicle]
never_expire_vehicles = true
[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
""")
    aircraft_mode = 2 if args.aircraft_hold else int(args.aircraft)
    train_engine = 0 if args.train_engine is None else args.train_engine + 1
    (output / "scripts/game_start.scr").write_text(f'unpause\nstart_ai "OpenTT3D Rail Fixture" "review_airport={airports.index(args.airport)},review_aircraft={aircraft_mode},review_train_engine={train_engine},review_train_hold={int(args.train_hold)}"\n')
    (output / "scripts/save_fixture.scr").write_text("pause\nsave rail-fixture\n")
    (output / "scripts/save_failed_fixture.scr").write_text("pause\nsave failed-fixture\n")
    # Bind only loopback, choosing an unused local port so regular games can coexist.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [str(executable), "-D", f"127.0.0.1:{port}", "-c", str(output / "openttd.cfg"), "-x", "-X",
               "-s", "null", "-m", "null", "-I", graphics["name"], "-S", "NoSound", "-M", "NoMusic",
               "-d", "script=4,console=1", "-G", "314159", "-t", str(year), "-g"]
    result = output / "save/rail-fixture.sav"
    with (output / "run.log").open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=dict(os.environ, OPENTT3D_RENDERER="0"),
                                   stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if process.poll() is not None or "RAIL_FIXTURE_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Fixture construction failed; inspect {output / 'run.log'}")
                ready = re.search(r"RAIL_FIXTURE_READY (\{[^\n]+\})", text)
                if ready:
                    manifest = json.loads(ready[1])
                    manifest["starting_year"] = year
                    if args.train_engine is not None and manifest.get("train_engine") != args.train_engine:
                        raise RuntimeError("The fixture did not build the requested electric locomotive")
                    manifest["train_held"] = False
                    if args.train_hold:
                        if f"RAIL_FIXTURE_TRAIN_HELD {manifest['vehicle']} engine={manifest['train_engine']}" not in text:
                            raise RuntimeError("The train did not stop at the review terminus")
                        manifest["train_held"] = True
                    if args.aircraft and (manifest.get("aircraft", -1) < 0 or not manifest.get("aircraft_verified") or manifest.get("aircraft_peak_speed", 0) <= 0):
                        raise RuntimeError("Aircraft fixture did not complete its actual airport service loop")
                    if args.aircraft_hold and not manifest.get("aircraft_held"):
                        raise RuntimeError("The verified aircraft was not held for stand-clearance review")
                    # One stdin line: dedicated's select/fgets loop can buffer a
                    # second pipe line without seeing another readable fd event.
                    process.stdin.write("exec scripts/save_fixture.scr\n")
                    process.stdin.flush()
                    break
                time.sleep(0.25)
            else:
                raise TimeoutError(f"Fixture construction timed out; inspect {output / 'run.log'}")
            # Saving may run on the upstream worker; wait for its completion message.
            deadline = min(deadline, time.monotonic() + 15)
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if "Saving map failed" in text or "Script file 'scripts/save_fixture.scr' not found" in text:
                    raise RuntimeError(f"Fixture save failed; inspect {output / 'run.log'}")
                if result.is_file() and result.stat().st_size > 100 and "Map successfully saved" in text:
                    break
                if process.poll() is not None:
                    raise RuntimeError(f"Game exited before saving; inspect {output / 'run.log'}")
                time.sleep(0.25)
            else:
                raise TimeoutError(f"Fixture save did not finish; inspect {output / 'run.log'}")
            (output / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n")
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.wait(timeout=15)
        except (RuntimeError, TimeoutError):
            # Preserve an inspectable ordinary save when construction/traffic
            # verification fails; never turn that partial world into a ready fixture.
            if process.poll() is None:
                process.stdin.write("exec scripts/save_failed_fixture.scr\n")
                process.stdin.flush()
                failed = output / "save/failed-fixture.sav"
                until = time.monotonic() + 15
                while time.monotonic() < until and process.poll() is None:
                    if failed.is_file() and failed.stat().st_size > 100 and "Map successfully saved" in (output / "run.log").read_text():
                        break
                    time.sleep(0.25)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print(f"Electric-rail fixture: {result}\nLayout: {json.dumps(manifest, sort_keys=True)}")


if __name__ == "__main__":
    main()

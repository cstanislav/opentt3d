#!/usr/bin/env python3
"""Save ordinary industry construction checkpoints through the public NoAI API."""

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
    parser.add_argument("--industry", type=int, choices=range(37), default=0)
    parser.add_argument("--climate", choices=("temperate", "arctic", "tropic", "toyland"), default="temperate")
    parser.add_argument("--terrain-type", type=int, choices=range(4), default=0, help="Normal map-generation terrain setting; Arctic forests require a sufficiently high site")
    parser.add_argument("--snow-coverage", type=int, choices=range(101), help="Normal Arctic map-generation snow percentage")
    parser.add_argument("--desert-coverage", type=int, choices=range(101), help="Normal tropical map-generation desert percentage")
    parser.add_argument("--town-site", action="store_true", help="Fund a town-only industry on an existing house through ordinary commands")
    parser.add_argument("--city-size", type=int, choices=range(1,11), help="Normal initial city-size multiplier, for industries requiring a sufficiently large town")
    services = parser.add_mutually_exclusive_group()
    services.add_argument("--coal-service", action="store_true", help="After construction, require a real truck to load coal, deliver it to a funded power station and return")
    services.add_argument("--cargo-service", action="store_true", help="Operate the producer's real cargo to --destination-industry, requiring loading, delivery and return")
    parser.add_argument("--destination-industry", type=int, choices=range(37), help="Original accepting industry to fund for --cargo-service")
    parser.add_argument("--destination-town-site", action="store_true", help="Fund the accepting industry on an actual town house and connect its public road network")
    parser.add_argument("--truck-engine", type=int, choices=range(116,204), help="Select one original road engine for the route; its real cargo type and availability are checked by NoAI")
    parser.add_argument("--year", type=int, default=1970, help="Normal world start year; later trucks need an appropriate year")
    parser.add_argument("--cargo-snapshots", action="store_true", help="Also pause/save the actual full truck and its empty state after delivery")
    parser.add_argument("--depot-directions", action="store_true", help="Build and verify all four original road-depot exits through normal public commands")
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()
    service_requested = args.coal_service or args.cargo_service
    if args.coal_service and args.industry != 0:
        parser.error("--coal-service requires original industry type0")
    if args.cargo_service != (args.destination_industry is not None):
        parser.error("--cargo-service and --destination-industry require each other")
    if args.destination_industry == args.industry:
        parser.error("The cargo destination must be a separate industry type")
    if args.destination_town_site and not args.cargo_service:
        parser.error("--destination-town-site requires --cargo-service")
    if args.truck_engine is not None and not service_requested:
        parser.error("--truck-engine requires --coal-service or --cargo-service")
    if not 0 <= args.year <= 5000000:
        parser.error("--year must be a supported normal calendar year")
    if args.cargo_snapshots and not service_requested:
        parser.error("--cargo-snapshots requires --coal-service or --cargo-service")
    if args.depot_directions and not service_requested:
        parser.error("--depot-directions requires --coal-service or --cargo-service")
    if args.snow_coverage is not None and args.climate != "arctic":
        parser.error("--snow-coverage requires the Arctic climate")
    if args.desert_coverage is not None and args.climate != "tropic":
        parser.error("--desert-coverage requires the tropical climate")
    if args.town_site and service_requested:
        parser.error("--town-site is a construction fixture; the producer cargo route requires an open site")
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file():
        parser.error(f"Missing executable: {executable}")
    if output.exists():
        parser.error("Use a new output directory")
    graphics = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "industry", output / "ai/industry-fixture")
    scripts = output / "scripts"
    scripts.mkdir()
    vehicle_settings = "[vehicle]\nnever_expire_vehicles = true\n" if args.truck_engine is not None else ""
    snow_setting = f"snow_coverage = {args.snow_coverage}\n" if args.snow_coverage is not None else ""
    desert_setting = f"desert_coverage = {args.desert_coverage}\n" if args.desert_coverage is not None else ""
    city_setting = f"[economy]\nlarger_towns = 1\ninitial_city_size = {args.city_size}\n" if args.city_size is not None else ""
    (output / "openttd.cfg").write_text(f"""[misc]
language = english.lng
[gui]
autosave_interval = 0
[game_creation]
map_x = 7
map_y = 7
starting_year = {args.year}
generation_seed = 314159
landscape = {args.climate}
land_generator = 1
custom_sea_level = {60 if args.industry == 5 else 1}
custom_town_number = 1
amount_of_rivers = 0
{snow_setting}{desert_setting}[difficulty]
terrain_type = {args.terrain_type}
quantity_sea_lakes = 4
number_towns = 4
industry_density = 0
max_loan = 50000000
town_council_tolerance = 0
[construction]
raw_industry_construction = 1
terraform_per_64k_frames = 1000000
terraform_frame_burst = 4096
{vehicle_settings}{city_setting}[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
""")
    destination = args.destination_industry if args.cargo_service else 1
    (scripts / "game_start.scr").write_text(f'unpause\nstart_ai "OpenTT3D Industry Fixture" "review_industry={args.industry},review_town_site={int(args.town_site)},review_coal_service={int(args.coal_service)},review_cargo_service={int(args.cargo_service)},review_destination={destination},review_destination_town_site={int(args.destination_town_site)},review_depot_directions={int(args.depot_directions)},review_truck_engine={args.truck_engine if args.truck_engine is not None else -1}"\n')
    days = (0, 16, 30, 44)
    for day in days:
        (scripts / f"save_day_{day}.scr").write_text(f"pause\nsave industry-day-{day}\n")
    (scripts / "save_failed.scr").write_text("pause\nsave failed-fixture\n")
    (scripts / "save_service.scr").write_text("pause\nsave industry-service\n")
    for state in ("empty", "full"):
        (scripts / f"save_cargo_{state}.scr").write_text(f"pause\nsave industry-cargo-{state}\n")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [str(executable), "-D", f"127.0.0.1:{port}", "-c", str(output / "openttd.cfg"), "-x", "-X",
               "-s", "null", "-m", "null", "-I", graphics["name"], "-S", "NoSound", "-M", "NoMusic",
               "-d", "script=4,console=1", "-G", "314159", "-t", str(args.year), "-g"]
    snapshots = []
    with (output / "run.log").open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=dict(os.environ, OPENTT3D_RENDERER="0"),
                                   stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
        deadline = time.monotonic() + args.timeout

        def send(command):
            process.stdin.write(command + "\n")
            process.stdin.flush()

        def wait_for(check, label):
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if process.poll() is not None or "INDUSTRY_FIXTURE_FAILED" in text or "script died unexpectedly" in text or "Saving map failed" in text:
                    raise RuntimeError(f"Fixture failed while {label}; inspect {output / 'run.log'}")
                result = check(text)
                if result:
                    return result
                time.sleep(0.1)
            raise TimeoutError(f"Fixture timed out while {label}; inspect {output / 'run.log'}")

        try:
            for day in days:
                def snapshot(text):
                    return next((entry for match in re.finditer(r"INDUSTRY_FIXTURE_SNAPSHOT (\{[^\n]+\})", text)
                                 if (entry := json.loads(match[1]))["day"] == day), None)
                entry = wait_for(snapshot, f"observing day {day}")
                if entry["type"] != args.industry or entry["industry"] < 0:
                    raise RuntimeError("The fixture did not fund the requested industry")
                count = (output / "run.log").read_text().count("Map successfully saved")
                send(f"exec scripts/save_day_{day}.scr")
                saved = output / f"save/industry-day-{day}.sav"
                wait_for(lambda text: saved.is_file() and saved.stat().st_size > 100 and text.count("Map successfully saved") > count,
                         f"saving day {day}")
                entry["save"] = str(saved.relative_to(output))
                snapshots.append(entry)
                if day != days[-1] or service_requested:
                    send("unpause")
            manifest = {"starting_year": args.year, "climate": args.climate, "terrain_type": args.terrain_type,
                        "snow_coverage": args.snow_coverage, "desert_coverage": args.desert_coverage,
                        "town_site": args.town_site, "destination_town_site": args.destination_town_site,
                        "initial_city_size": args.city_size, "snapshots": snapshots}
            if service_requested:
                cargo_snapshots = {}

                def service_ready(text):
                    if args.cargo_snapshots:
                        for match in re.finditer(r"INDUSTRY_CARGO_SNAPSHOT (\{[^\n]+\})", text):
                            entry = json.loads(match[1])
                            state = entry["state"]
                            if state in cargo_snapshots:
                                continue
                            if state not in ("empty", "full") or entry["capacity"] <= 0 or entry["amount"] != (0 if state == "empty" else entry["capacity"]):
                                raise RuntimeError("Cargo snapshot did not report a genuine empty/full state")
                            count = (output / "run.log").read_text().count("Map successfully saved")
                            send(f"exec scripts/save_cargo_{state}.scr")
                            saved = output / f"save/industry-cargo-{state}.sav"
                            wait_for(lambda current: saved.is_file() and saved.stat().st_size > 100 and current.count("Map successfully saved") > count,
                                     f"saving the actual {state} truck")
                            entry["save"] = str(saved.relative_to(output))
                            cargo_snapshots[state] = entry
                            send("unpause")
                    return re.search(r"INDUSTRY_SERVICE_READY (\{[^\n]+\})", text)

                ready = wait_for(service_ready, "verifying actual cargo service")
                service = json.loads(ready[1])
                if service["truck"] < 0 or service["acceptance"] < 8 or service["peak_load"] <= 0 or service["peak_speed"] <= 0 or not service["returned"]:
                    raise RuntimeError("The cargo-service route did not complete its live cargo checks")
                if args.truck_engine is not None and service["engine"] != args.truck_engine:
                    raise RuntimeError("The cargo-service route did not operate the requested original engine")
                if service["source_type"] != args.industry or service["destination_type"] != destination:
                    raise RuntimeError("The cargo route did not connect the requested original industries")
                count = (output / "run.log").read_text().count("Map successfully saved")
                send("exec scripts/save_service.scr")
                saved = output / "save/industry-service.sav"
                wait_for(lambda text: saved.is_file() and saved.stat().st_size > 100 and text.count("Map successfully saved") > count,
                         "saving the working cargo-service route")
                service["save"] = str(saved.relative_to(output))
                manifest["coal_service" if args.coal_service else "cargo_service"] = service
                if args.depot_directions:
                    directions = re.search(r"INDUSTRY_DEPOT_DIRECTIONS_READY (\{[^\n]+\})", (output / "run.log").read_text())
                    if not directions or (depots := json.loads(directions[1]))["directions"] != list(range(4)):
                        raise RuntimeError("The four actual road-depot exits were not verified")
                    if f"INDUSTRY_DEPOT_SERVICE_VERIFIED vehicle={service['truck']} " not in (output / "run.log").read_text():
                        raise RuntimeError("The service truck did not enter, stop in and leave its actual depot")
                    depots["truck_entry_exit_verified"] = True
                    manifest["depots"] = depots
                if args.cargo_snapshots:
                    if set(cargo_snapshots) != {"empty", "full"} or any(entry["vehicle"] != service["truck"] for entry in cargo_snapshots.values()):
                        raise RuntimeError("Both actual cargo states of the service truck were not saved")
                    manifest["cargo_snapshots"] = cargo_snapshots
            (output / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n")
            send("quit")
            process.wait(timeout=15)
        except (RuntimeError, TimeoutError):
            if process.poll() is None:
                send("exec scripts/save_failed.scr")
                failed = output / "save/failed-fixture.sav"
                until = time.monotonic() + 15
                while time.monotonic() < until and process.poll() is None:
                    if failed.is_file() and failed.stat().st_size > 100:
                        break
                    time.sleep(0.1)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print(f"Industry construction fixture: {output}\nManifest: {json.dumps(manifest, sort_keys=True)}")


if __name__ == "__main__":
    main()

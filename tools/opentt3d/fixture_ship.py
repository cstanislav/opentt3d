#!/usr/bin/env python3
"""Build and observe an ordinary canal/dock ship fleet through public NoAI commands."""
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
    parser.add_argument("--climate", choices=("temperate","arctic","tropic","toyland"), default="temperate")
    parser.add_argument("--first-engine", type=int, choices=range(204,215), default=204)
    parser.add_argument("--last-engine", type=int, choices=range(204,215), default=214)
    parser.add_argument("--depot-axis", type=int, choices=range(2), default=0)
    parser.add_argument("--depot-service", action="store_true", help="Add an ordinary recurring depot-service order after the two dock calls")
    parser.add_argument("--depot-hold-ticks", type=int, choices=range(257), default=0, help="Use a normal depot-stop order and public AI restart after this many ticks; requires --depot-service")
    parser.add_argument("--all-dock-directions", action="store_true", help="Add two ordinary docks on the other banks for all-direction artwork review")
    parser.add_argument("--dock-hold", action="store_true", help="Keep the observed final full-load dock order for a paused actual mooring review")
    parser.add_argument("--buoy-waypoint", action="store_true", help="Build an original buoy and require the ships to navigate its ordinary waypoint order")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists() or args.first_engine > args.last_engine:
        parser.error("Use a built executable, a new output directory and an increasing engine range")
    if args.depot_hold_ticks and not args.depot_service:
        parser.error("--depot-hold-ticks requires --depot-service")
    if args.dock_hold and args.depot_service:
        parser.error("Choose a held dock review or a recurring depot-service route")
    if args.dock_hold and args.buoy_waypoint:
        parser.error("A held dock cannot complete the subsequent buoy waypoint order")
    root = Path(__file__).resolve().parents[2]
    graphics = json.loads((root / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "ship", output / "ai/ship-catalogue")
    scripts = output / "scripts"
    scripts.mkdir()
    (output / "openttd.cfg").write_text(f"""[misc]
language = english.lng
[gui]
autosave_interval = 0
[game_creation]
map_x = 7
map_y = 7
starting_year = 2050
generation_seed = 314159
landscape = {args.climate}
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
[construction]
terraform_per_64k_frames = 1000000
terraform_frame_burst = 8192
clear_tree_per_64k_frames = 1000000
clear_tree_frame_burst = 8192
[vehicle]
never_expire_vehicles = true
[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
""")
    (scripts / "game_start.scr").write_text(f'unpause\nstart_ai "OpenTT3D Ship Catalogue" "review_first={args.first_engine},review_last={args.last_engine},depot_axis={args.depot_axis},depot_service={int(args.depot_service)},depot_hold_ticks={args.depot_hold_ticks},all_docks={int(args.all_dock_directions)},dock_hold={int(args.dock_hold)},buoy_waypoint={int(args.buoy_waypoint)}"\n')
    (scripts / "save_fixture.scr").write_text("pause\nsave ship-catalogue\n")
    (scripts / "save_failed.scr").write_text("pause\nsave failed-fixture\n")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1",0))
        port = probe.getsockname()[1]
    command = [str(executable),"-D",f"127.0.0.1:{port}","-c",str(output / "openttd.cfg"),"-x","-X",
               "-s","null","-m","null","-I",graphics["name"],"-S","NoSound","-M","NoMusic",
               "-d","script=4,console=1","-G","314159","-t","2050","-g"]
    with (output / "run.log").open("w") as log:
        process = subprocess.Popen(command,cwd=build,env=dict(os.environ,OPENTT3D_RENDERER="0"),
                                   stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
        try:
            deadline = time.monotonic()+args.timeout
            manifest = None
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if process.poll() is not None or "SHIP_CATALOGUE_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Ship fixture failed; inspect {output / 'run.log'}")
                ready = re.search(r"SHIP_CATALOGUE_READY (\{[^\n]+\})",text)
                if ready:
                    manifest = json.loads(ready[1])
                    if not manifest["vehicles"] or any(not args.first_engine <= vehicle["engine"] <= args.last_engine or vehicle["peak_speed"] <= 0 or vehicle["docks_visited"] != 3 for vehicle in manifest["vehicles"]):
                        raise RuntimeError("Ship fixture did not verify the selected fleet at both docks")
                    if args.buoy_waypoint and (manifest.get("buoy",-1) < 0 or any(not vehicle.get("buoy_visited") for vehicle in manifest["vehicles"])):
                        raise RuntimeError("Ship fixture did not observe navigation through the actual buoy tile")
                    process.stdin.write("exec scripts/save_fixture.scr\n"); process.stdin.flush()
                    break
                time.sleep(0.2)
            if manifest is None:
                raise TimeoutError("Ship fixture readiness timed out")
            result = output / "save/ship-catalogue.sav"
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if "Saving map failed" in text or process.poll() is not None:
                    raise RuntimeError("Ship fixture save failed")
                if result.is_file() and result.stat().st_size > 100 and "Map successfully saved" in text:
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError("Ship fixture save timed out")
            manifest.update(climate=args.climate,starting_year=2050,save="save/ship-catalogue.sav")
            (output / "fixture.json").write_text(json.dumps(manifest,indent=2)+"\n")
            process.stdin.write("quit\n"); process.stdin.flush()
            process.wait(timeout=15)
        except (RuntimeError,TimeoutError):
            if process.poll() is None:
                process.stdin.write("exec scripts/save_failed.scr\n"); process.stdin.flush()
                until = time.monotonic()+15
                while time.monotonic() < until and not (output / "save/failed-fixture.sav").is_file() and process.poll() is None:
                    time.sleep(0.2)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
    print(f"Ship catalogue fixture: {output}")
    print(json.dumps(manifest,sort_keys=True))


if __name__ == "__main__":
    main()

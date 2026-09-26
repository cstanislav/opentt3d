#!/usr/bin/env python3
"""Create a climate-specific road-family review world using public NoAI commands."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--climate", choices=("temperate","arctic","tropic","toyland"), default="temperate")
    parser.add_argument("--first-engine", type=int, choices=range(116,204), default=116)
    parser.add_argument("--last-engine", type=int, choices=range(116,204), default=203)
    parser.add_argument("--tram-depots", action="store_true", help="Enable a fixture-only tram test vehicle and build all four original tram-depot exits")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists() or args.first_engine > args.last_engine:
        parser.error("Use a built executable, a new output directory and an increasing engine range")
    root = Path(__file__).resolve().parents[2]
    graphics = json.loads((root / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "road", output / "ai/road-catalogue")
    scripts = output / "scripts"
    scripts.mkdir()
    newgrf_setting = ""
    if args.tram_depots:
        # No vanilla engine enables the original tram infrastructure. This tiny
        # test-only NewGRF changes engine116's tram flag and climate availability;
        # it supplies no graphics and leaves every original depot sprite intact.
        records = [b"\x08\x08O3TRTram depot fixture\0Test-only original bus116 on tram tracks; no sprite replacements.\0",
                   bytes((0,1,2,1,0,0x1c,1,0x06,15))]
        def pseudo(payload):
            return struct.pack("<HB",len(payload),0xff)+payload
        grf = pseudo(struct.pack("<I",len(records)))+b"".join(map(pseudo,records))+b"\0\0"
        (output / "newgrf").mkdir()
        (output / "newgrf/tram-fixture.grf").write_bytes(grf)
        newgrf_setting = "[newgrf]\ntram-fixture.grf =\n"
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
terraform_frame_burst = 4096
[vehicle]
never_expire_vehicles = true
[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
{newgrf_setting}
""")
    (scripts / "game_start.scr").write_text(f'unpause\nstart_ai "OpenTT3D Road Catalogue" "review_first={args.first_engine},review_last={args.last_engine},review_tram={int(args.tram_depots)}"\n')
    (scripts / "save_fixture.scr").write_text("pause\nsave road-catalogue\n")
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
                if process.poll() is not None or "ROAD_CATALOGUE_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Road fixture failed; inspect {output / 'run.log'}")
                ready = re.search(r"ROAD_CATALOGUE_READY (\{[^\n]+\})",text)
                if ready:
                    manifest = json.loads(ready[1])
                    if not manifest["vehicles"] or any(not args.first_engine <= vehicle["engine"] <= args.last_engine or vehicle["peak_speed"] <= 0 for vehicle in manifest["vehicles"]):
                        raise RuntimeError("Road fixture did not verify the selected moving vehicles")
                    if args.tram_depots and manifest.get("depot_directions") != [0,1,2,3]:
                        raise RuntimeError("The four original tram-depot exits were not built and observed")
                    process.stdin.write("exec scripts/save_fixture.scr\n")
                    process.stdin.flush()
                    break
                time.sleep(0.2)
            if manifest is None:
                raise TimeoutError("Road fixture readiness timed out")
            result = output / "save/road-catalogue.sav"
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if "Saving map failed" in text or process.poll() is not None:
                    raise RuntimeError("Road fixture save failed")
                if result.is_file() and result.stat().st_size > 100 and "Map successfully saved" in text:
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError("Road fixture save timed out")
            manifest.update(climate=args.climate,starting_year=2050,save="save/road-catalogue.sav")
            if args.tram_depots:
                manifest["fixture_newgrf"] = {"path":"newgrf/tram-fixture.grf", "engine":116,
                                             "changes":"tram flag and all-climate availability only; no graphics replacements"}
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
    print(f"Road catalogue fixture: {output}")
    print(json.dumps(manifest,sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Operate a climate/railtype-specific wagon consist through public NoAI commands."""
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
    parser.add_argument("--climate", choices=("temperate", "arctic", "tropic", "toyland"), default="temperate")
    parser.add_argument("--rail-type", type=int, choices=range(4), default=1)
    parser.add_argument("--locomotive", type=int, choices=range(116), help="Require one available original locomotive of the selected railtype")
    parser.add_argument("--first-engine", type=int, choices=range(116), default=27)
    parser.add_argument("--last-engine", type=int, choices=range(116), default=53)
    parser.add_argument("--hold", action="store_true", help="Stop the verified returning consist through a normal public command")
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists() or args.first_engine > args.last_engine:
        parser.error("Use a built executable, new output directory and increasing engine range")
    root = Path(__file__).resolve().parents[2]
    graphics = json.loads((root / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "train", output / "ai/train-catalogue")
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
    engine = args.locomotive if args.locomotive is not None else -1
    (scripts / "game_start.scr").write_text(f'unpause\nstart_ai "OpenTT3D Train Catalogue" "review_rail_type={args.rail_type},review_engine={engine},review_first={args.first_engine},review_last={args.last_engine},review_hold={int(args.hold)}"\n')
    (scripts / "save_fixture.scr").write_text("pause\nsave train-catalogue\n")
    (scripts / "save_failed.scr").write_text("pause\nsave failed-fixture\n")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [str(executable), "-D", f"127.0.0.1:{port}", "-c", str(output / "openttd.cfg"), "-x", "-X",
               "-s", "null", "-m", "null", "-I", graphics["name"], "-S", "NoSound", "-M", "NoMusic",
               "-d", "script=4,console=1", "-G", "314159", "-t", "2050", "-g"]
    with (output / "run.log").open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=dict(os.environ, OPENTT3D_RENDERER="0"),
                                   stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + args.timeout
            manifest = None
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if process.poll() is not None or "TRAIN_CATALOGUE_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Train fixture failed; inspect {output / 'run.log'}")
                ready = re.search(r"TRAIN_CATALOGUE_READY (\{[^\n]+\})", text)
                if ready:
                    manifest = json.loads(ready[1])
                    if (not manifest["wagons"] or manifest["rail_type"] != args.rail_type or not manifest["returned"] or
                        manifest["peak_speed"] <= 0 or manifest["held"] != args.hold or
                        any(not args.first_engine <= wagon["engine"] <= args.last_engine for wagon in manifest["wagons"]) or
                        (args.locomotive is not None and manifest["locomotive"] != args.locomotive)):
                        raise RuntimeError("Train fixture did not verify its selected operating consist")
                    process.stdin.write("exec scripts/save_fixture.scr\n")
                    process.stdin.flush()
                    break
                time.sleep(0.2)
            if manifest is None:
                raise TimeoutError("Train fixture readiness timed out")
            result = output / "save/train-catalogue.sav"
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if "Saving map failed" in text or process.poll() is not None:
                    raise RuntimeError("Train fixture save failed")
                if result.is_file() and result.stat().st_size > 100 and "Map successfully saved" in text:
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError("Train fixture save timed out")
            manifest.update(climate=args.climate, starting_year=2050, save="save/train-catalogue.sav")
            (output / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n")
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.wait(timeout=15)
        except (RuntimeError, TimeoutError):
            if process.poll() is None:
                process.stdin.write("exec scripts/save_failed.scr\n")
                process.stdin.flush()
                until = time.monotonic() + 15
                while time.monotonic() < until and not (output / "save/failed-fixture.sav").is_file() and process.poll() is None:
                    time.sleep(0.2)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print(f"Train catalogue fixture: {output}\n{json.dumps(manifest, sort_keys=True)}")


if __name__ == "__main__":
    main()

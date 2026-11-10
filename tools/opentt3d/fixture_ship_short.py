#!/usr/bin/env python3
"""Build a narrow canal and a short bridge, then operate one ship beneath it."""
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
    parser.add_argument("--engine", type=int, choices=range(204,215), default=204)
    parser.add_argument("--canal-width", type=int, choices=(2,3), required=True)
    parser.add_argument("--bridge-type", type=int, choices=range(13), required=True)
    parser.add_argument("--bridge-hold", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists():
        parser.error("Use a built executable and a new output directory")
    root = Path(__file__).resolve().parents[2]
    graphics = json.loads((root / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "ship_short", output / "ai/ship-short")
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
    (scripts / "game_start.scr").write_text(
        f'unpause\nstart_ai "OpenTT3D Short Bridge Ship" '
        f'"review_engine={args.engine},canal_width={args.canal_width},bridge_type={args.bridge_type},bridge_hold={int(args.bridge_hold)}"\n')
    (scripts / "save_fixture.scr").write_text("pause\nsave short-bridge\n")
    (scripts / "save_failed.scr").write_text("pause\nsave short-bridge-failed\n")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [str(executable), "-D", f"127.0.0.1:{port}", "-c", str(output / "openttd.cfg"), "-x", "-X",
               "-s", "null", "-m", "null", "-I", graphics["name"], "-S", "NoSound", "-M", "NoMusic",
               "-d", "script=4,console=1", "-G", "314159", "-t", "2050", "-g"]
    with (output / "run.log").open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=dict(os.environ, OPENTT3D_RENDERER="0", OPENTT3D_BACKGROUND="1"),
                                   stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + args.timeout
            manifest = None
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if process.poll() is not None or "SHIP_SHORT_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Short bridge fixture failed; inspect {output / 'run.log'}")
                ready = re.search(r"SHIP_SHORT_READY (\{[^\n]+\})", text)
                if ready:
                    manifest = json.loads(ready[1])
                    if manifest.get("canal_width") != args.canal_width or manifest.get("bridge_type") != args.bridge_type:
                        raise RuntimeError("Short bridge fixture built different geometry")
                    if manifest.get("docks_visited") != 3 or not manifest.get("bridge_under_span") or manifest.get("peak_speed", 0) <= 0:
                        raise RuntimeError("Short bridge ship did not visit both docks and pass under the span")
                    if args.bridge_hold and not manifest.get("bridge_held"):
                        raise RuntimeError("Short bridge ship was not held under the span")
                    process.stdin.write("exec scripts/save_fixture.scr\n"); process.stdin.flush()
                    break
                time.sleep(0.2)
            if manifest is None:
                raise TimeoutError("Short bridge readiness timed out")
            result = output / "save/short-bridge.sav"
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if "Saving map failed" in text or process.poll() is not None:
                    raise RuntimeError("Short bridge save failed")
                if result.is_file() and result.stat().st_size > 100 and "Map successfully saved" in text:
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError("Short bridge save timed out")
            manifest.update(climate=args.climate, save="save/short-bridge.sav")
            (output / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n")
            process.stdin.write("quit\n"); process.stdin.flush()
            process.wait(timeout=15)
        except (RuntimeError, TimeoutError):
            if process.poll() is None:
                process.stdin.write("exec scripts/save_failed.scr\n"); process.stdin.flush()
                until = time.monotonic() + 15
                while time.monotonic() < until and not (output / "save/short-bridge-failed.sav").is_file() and process.poll() is None:
                    time.sleep(0.2)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
    print(f"Short bridge fixture: {output}")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()

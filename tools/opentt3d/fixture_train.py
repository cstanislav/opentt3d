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
    parser.add_argument("--low-effect-id", action="store_true", help="Build and sell a spare locomotive to leave an ordinary free pool slot before the operating train, exposing original pre-tick effect states")
    parser.add_argument("--smoke-amount", type=int, choices=range(3), help="Use the original no/reduced/full vehicle smoke setting for this new fixture")
    parser.add_argument("--departing", action="store_true", help="Stop and restart the verified returning train through public commands, then save its ordinary acceleration for exhaust review")
    parser.add_argument("--clearance-route", action="store_true", help="Operate the consist across a real bridge with ramps and a tunnel built through a raised hill")
    parser.add_argument("--curve-route", action="store_true", help="Add a four-corner detour between the bridge and tunnel for real heading/rail-join observations")
    parser.add_argument("--cargo-source", type=int, choices=range(37), help="Fund this original producer and verify real cargo service with a single selected wagon")
    parser.add_argument("--cargo-destination", type=int, choices=range(37), help="Original accepting industry for --cargo-source")
    parser.add_argument("--cargo-town", action="store_true", help="Fund an ordinary town by the delivery station for town-accepted cargo")
    parser.add_argument("--cargo-feeder", type=int, choices=range(37), help="Supply the processing industry by a real truck from this original input producer")
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists() or args.first_engine > args.last_engine:
        parser.error("Use a built executable, new output directory and increasing engine range")
    if args.cargo_town and args.cargo_destination is not None:
        parser.error("Select one cargo destination: a funded town or industry")
    if (args.cargo_source is None) != (args.cargo_destination is None and not args.cargo_town):
        parser.error("Cargo review requires a producer and an accepting industry or town")
    if args.cargo_feeder is not None and (args.cargo_source is None or args.cargo_feeder in (args.cargo_source,args.cargo_destination)):
        parser.error("A cargo feeder needs a distinct input producer and processing source")
    if args.curve_route and args.cargo_feeder is not None:
        parser.error("The curve detour occupies the optional feeder industry's review site")
    if args.cargo_source is not None and (args.first_engine != args.last_engine or args.cargo_source == args.cargo_destination):
        parser.error("Cargo review needs one wagon engine and distinct industry types")
    if args.low_effect_id and args.cargo_source is not None:
        parser.error("--low-effect-id requires a movement-only train fixture")
    if args.departing and (args.hold or args.cargo_source is not None):
        parser.error("--departing requires a movement-only fixture without --hold")
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
raw_industry_construction = 1
terraform_per_64k_frames = 1000000
terraform_frame_burst = 4096
[economy]
found_town = 2
[vehicle]
never_expire_vehicles = true
[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
""")
    if args.smoke_amount is not None:
        config = output / "openttd.cfg"
        config.write_text(config.read_text().replace("[vehicle]\n", f"[vehicle]\nsmoke_amount = {args.smoke_amount}\n"))
    engine = args.locomotive if args.locomotive is not None else -1
    source = args.cargo_source if args.cargo_source is not None else -1
    destination = -1 if args.cargo_town else args.cargo_destination if args.cargo_destination is not None else 1
    feeder = args.cargo_feeder if args.cargo_feeder is not None else -1
    (scripts / "game_start.scr").write_text(f'unpause\nstart_ai "OpenTT3D Train Catalogue" "review_rail_type={args.rail_type},review_engine={engine},review_first={args.first_engine},review_last={args.last_engine},review_hold={int(args.hold)},review_low_effect_id={int(args.low_effect_id)},review_departing={int(args.departing)},review_clearance={int(args.clearance_route)},review_curves={int(args.curve_route)},review_source={source},review_destination={destination},review_feeder={feeder}"\n')
    (scripts / "save_fixture.scr").write_text("pause\nsave train-catalogue\n")
    (scripts / "save_failed.scr").write_text("pause\nsave failed-fixture\n")
    for state in ("empty", "full"):
        (scripts / f"save_cargo_{state}.scr").write_text(f"pause\nsave train-cargo-{state}\n")
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
            cargo_snapshots = {}
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if process.poll() is not None or "TRAIN_CATALOGUE_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Train fixture failed; inspect {output / 'run.log'}")
                if args.cargo_source is not None:
                    for match in re.finditer(r"TRAIN_CARGO_SNAPSHOT (\{[^\n]+\})", text):
                        entry = json.loads(match[1])
                        state = entry["state"]
                        if state in cargo_snapshots:
                            continue
                        if (state not in ("empty", "full") or entry["capacity"] <= 0 or
                            entry["amount"] != (0 if state == "empty" else entry["capacity"]) or entry["engine"] != args.first_engine):
                            raise RuntimeError("Train snapshot did not observe a genuine selected empty/full wagon")
                        count = (output / "run.log").read_text().count("Map successfully saved")
                        process.stdin.write(f"exec scripts/save_cargo_{state}.scr\n")
                        process.stdin.flush()
                        saved = output / f"save/train-cargo-{state}.sav"
                        while time.monotonic() < deadline:
                            current = (output / "run.log").read_text()
                            if process.poll() is not None or "Saving map failed" in current:
                                raise RuntimeError("Train cargo snapshot save failed")
                            if saved.is_file() and saved.stat().st_size > 100 and current.count("Map successfully saved") > count:
                                break
                            time.sleep(0.1)
                        else:
                            raise TimeoutError("Train cargo snapshot save timed out")
                        entry["save"] = str(saved.relative_to(output))
                        cargo_snapshots[state] = entry
                        process.stdin.write("unpause\n")
                        process.stdin.flush()
                ready = re.search(r"TRAIN_CATALOGUE_READY (\{[^\n]+\})", text)
                if ready:
                    manifest = json.loads(ready[1])
                    if (not manifest["wagons"] or manifest["rail_type"] != args.rail_type or not manifest["returned"] or
                        manifest["peak_speed"] <= 0 or manifest["held"] != args.hold or
                        any(not args.first_engine <= wagon["engine"] <= args.last_engine for wagon in manifest["wagons"]) or
                        (args.locomotive is not None and manifest["locomotive"] != args.locomotive)):
                        raise RuntimeError("Train fixture did not verify its selected operating consist")
                    if args.low_effect_id and not 0 <= manifest.get("released_pool_id",-1) < manifest["train"]:
                        raise RuntimeError("The spare locomotive did not release an original pool slot before the operating train")
                    if args.smoke_amount is not None and manifest.get("smoke_amount") != args.smoke_amount:
                        raise RuntimeError("The fixture did not retain the requested original vehicle smoke setting")
                    if args.departing and manifest.get("departure_speed",0) < 16:
                        raise RuntimeError("The returning train did not resume ordinary acceleration")
                    if args.curve_route and (not manifest.get("curve_route") or not manifest.get("curve_seen") or
                        (args.cargo_source is not None and manifest.get("curve_cargo_states") != 3)):
                        raise RuntimeError("Train fixture did not traverse the actual curve detour in its required cargo states")
                    if args.clearance_route and (not manifest.get("clearance_route") or not manifest.get("bridge_seen") or not manifest.get("tunnel_seen") or
                                                 manifest.get("tunnel_first", -1) < 0 or manifest.get("tunnel_last", -1) <= manifest["tunnel_first"]):
                        raise RuntimeError("Train fixture did not verify its original bridge and tunnel route")
                    if args.cargo_source is not None:
                        if (not manifest.get("full") or not manifest.get("delivered") or manifest["acceptance"] < 8 or
                            manifest["source_type"] != args.cargo_source or manifest["destination_type"] != destination or
                            set(cargo_snapshots) != {"empty", "full"} or
                            any(entry["vehicle"] != manifest["wagons"][0]["vehicle"] for entry in cargo_snapshots.values())):
                            raise RuntimeError("Train fixture did not complete original cargo production, full load, accepted delivery and both saved states")
                        if args.cargo_feeder is not None and (manifest.get("feeder_type") != args.cargo_feeder or not manifest.get("feeder_delivered")):
                            raise RuntimeError("The processor did not receive an observed real input-cargo delivery")
                        if args.clearance_route and (manifest.get("bridge_cargo_states") != 3 or manifest.get("tunnel_cargo_states") != 3):
                            raise RuntimeError("The cargo consist did not traverse both the bridge and tunnel with full and empty capacity")
                        manifest["cargo_snapshots"] = cargo_snapshots
                    save_count = (output / "run.log").read_text().count("Map successfully saved")
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
                if result.is_file() and result.stat().st_size > 100 and text.count("Map successfully saved") > save_count:
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

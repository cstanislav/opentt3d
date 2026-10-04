#!/usr/bin/env python3
"""Survey natural original river selectors on an acknowledged save, never force them."""
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
from fixture_locks import verify_save


def survey_tiles(log, token):
    """Loaded AIs may log concurrently; correlate only the explicitly started survey."""
    if type(token) is not int or not 1 <= token <= 0x7fffffff:
        raise ValueError("Require the exact positive public survey correlation token")
    rows = [json.loads(value) for value in re.findall(r"RIVER_SURVEY_TILE (\{[^\n]+\})", log)]
    return [row for row in rows if type(row.get("survey_token")) is int and row["survey_token"] == token]


def validate_survey(row, tiles):
    if not isinstance(row, dict) or row.get("read_only_tile_queries") is not True:
        raise ValueError("Require actual read-only original river queries")
    width, height, count = (row.get(key) for key in ("map_width", "map_height", "river_tiles"))
    if any(type(value) is not int for value in (width, height, count)) or min(width, height) < 16 or count < 0:
        raise ValueError("Missing original river map dimensions/count")
    if not isinstance(tiles, list) or count != len(tiles):
        raise ValueError("Original river observation count differs")
    found = set()
    terrain_queries = row.get("public_terrain_type_queries", False)
    if type(terrain_queries) is not bool:
        raise ValueError("Terrain-type provenance requires an explicit boolean")
    token = row.get("survey_token")
    if token is not None and (type(token) is not int or not 1 <= token <= 0x7fffffff):
        raise ValueError("Survey acknowledgement needs its original public command token")
    for tile in tiles:
        if not isinstance(tile, dict) or any(type(tile.get(key)) is not int for key in ("tile", "x", "y", "slope", "min_height_levels")):
            raise ValueError("River tile metadata must remain exact integers")
        if (not 0 <= tile["x"] < width or not 0 <= tile["y"] < height or
                tile["tile"] != tile["x"] + tile["y"] * width or tile["tile"] in found):
            raise ValueError("Original river tile registration or uniqueness differs")
        if tile["slope"] not in (0, 12, 6, 3, 9) or tile["min_height_levels"] < 0:
            raise ValueError("Original river slope/height requires source review")
        if terrain_queries:
            terrain = tile.get("public_terrain_type")
            if type(terrain) is not int or terrain not in (0, 1, 2, 3):
                raise ValueError("Require an actual public AITile terrain-type query for every river tile")
        elif "public_terrain_type" in tile:
            raise ValueError("A terrain-type value without acknowledged query provenance is not accepted")
        if token is not None and (type(tile.get("survey_token")) is not int or tile["survey_token"] != token):
            raise ValueError("Interleaved loaded-AI observations cannot acknowledge another survey")
        found.add(tile["tile"])
    # A successful survey is not a promise that every slope, height or bank exists.
    return dict(row, tiles=tiles, observed_slopes=sorted({tile["slope"] for tile in tiles}),
                 observed_min_height_levels=sorted({tile["min_height_levels"] for tile in tiles}),
                public_terrain_type_queries=terrain_queries,
                observed_public_terrain_types=sorted({tile["public_terrain_type"] for tile in tiles}) if terrain_queries else [],
                terrain_type_code_domain="Public AITile enum: 0 normal, 1 desert, 2 rainforest, 3 snow; not raw NewGRF variable 0x81 (snow=4).",
                complete_terrain_type_or_snowline_coverage_verified=False,
                complete_river_family_verified=False, geometry_or_quality_approved=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--climate", choices=("temperate", "arctic", "tropic", "toyland"), default="temperate")
    parser.add_argument("--seed", type=int, default=271828)
    parser.add_argument("--savegame", type=Path, help="Requery an existing original world without regenerating its terrain")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists():
        parser.error("Use a built executable and a new output directory; retain failed surveys")
    if args.timeout < 1 or not 0 <= args.seed <= 0xffffffff:
        parser.error("Use a positive timeout and an original unsigned map-generation seed")
    input_save = args.savegame.resolve() if args.savegame is not None else None
    if input_save is not None:
        input_save_sha256 = verify_save(input_save)
    graphics = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "rivers", output / "ai/river-survey")
    if (build / "lang").is_dir():
        (output / "lang").symlink_to(build / "lang", target_is_directory=True)
    fetch(output / "baseset", seed=build / "baseset" / graphics["filename"])
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
custom_town_number = 1
amount_of_rivers = 3
[difficulty]
terrain_type = 2
quantity_sea_lakes = 1
number_towns = 4
industry_density = 0
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
               "-d", "script=4,console=1,net=3"]
    command.extend(["-g", str(input_save)] if input_save is not None else ["-G", str(args.seed), "-t", "1950", "-g"])
    logfile = output / "run.log"
    token = int.from_bytes(hashlib.sha256(str(output).encode()).digest()[:4], "big") & 0x7fffffff or 1
    acknowledgements = []
    with logfile.open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=dict(os.environ, OPENTT3D_RENDERER="0", OPENTT3D_BACKGROUND="1"),
                                   stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
        deadline = time.monotonic() + args.timeout

        def observe(pattern, start=0, timeout=None, allow_failed=False):
            until = deadline if timeout is None else min(deadline, time.monotonic() + timeout)
            while time.monotonic() < until:
                text = logfile.read_text()
                if process.poll() is not None or (not allow_failed and "script died unexpectedly" in text):
                    raise RuntimeError(f"Original river survey failed; inspect {logfile}")
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
            ready = send(f'start_ai "OpenTT3D Original River Survey" "survey_token={token}"',
                         rf'RIVER_SURVEY_READY (\{{[^\n]*"survey_token":{token},[^\n]+\}})')
            tiles = survey_tiles(logfile.read_text(), token)
            manifest = validate_survey(json.loads(ready[1]), tiles)
            send("pause", r"Game (?:paused|is already paused)")
            send("save river-survey", r"Map successfully saved to 'river-survey\.sav'\.", timeout=30)
            save = output / "save/river-survey.sav"
            manifest.update(climate=args.climate, seed=args.seed, save="save/river-survey.sav", save_sha256=verify_save(save),
                source="Original public AITile.IsRiverTile/GetSlope/GetMinHeight/GetTerrainType queries on a normally generated or reloaded original map.",
                source_height_units="Original map height levels; each level is eight source-height units, not doubled rendered terrain.",
                simulation_mutations="Original start_ai/pause/save commands and ordinary simulation only; no construction, terraform or forced selectors/RNG.",
                graphics_or_bank_absence_verified=False, ship_traversal_verified=False, command=command)
            if input_save is not None:
                manifest.update(input_save=str(input_save), input_save_sha256=input_save_sha256,
                    loaded_original_world_not_regenerated=True,
                    climate_provenance="Requested survey climate is recorded; the reloaded save retains its own original climate and seed.")
            (output / "fixture.json").write_text(json.dumps(manifest, indent=2) + "\n")
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.wait(timeout=15)
        except (RuntimeError, TimeoutError, ValueError):
            if process.poll() is None:
                # Retain the original generated world even when the survey fails.
                deadline = max(deadline, time.monotonic() + 30)
                send("pause", r"Game (?:paused|is already paused)", timeout=10, allow_failed=True)
                send("save failed-river-survey", r"Map successfully saved to 'failed-river-survey\.sav'\.", timeout=20, allow_failed=True)
                verify_save(output / "save/failed-river-survey.sav")
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print(json.dumps({"savegame": str(save), "river_tiles": manifest["river_tiles"],
                      "observed_slopes": manifest["observed_slopes"], "approved": False}))


if __name__ == "__main__":
    main()

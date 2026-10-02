#!/usr/bin/env python3
"""Audit the original small explosion from an explicit single-tile clear-area command.

Use smoke.py --clear-tile X Y --trace-effects. The command runs on a draw tick after
startup warm-up, so the first capture must retain progress0; all48 phases are required.
The oracle only reads logs/source. It never creates effects or consumes simulation RNG.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from bulldozer_motion import TRACE


ROOT = Path(__file__).resolve().parents[2]
SOURCES = tuple(ROOT / name for name in ("src/effectvehicle.cpp", "src/landscape.cpp"))
COMMAND = re.compile(r"original clear-area command tile (\d+),(\d+) centre (\d+),(\d+) ground (\d+) paused ([01])")


def audit(text, effect_source, landscape_source, expect_paused=False):
    tick = effect_source.split("static void ExplosionSmallInit(",1)[1].split("static void BulldozerInit(",1)[0]
    required = ("Set(SPR_EXPLOSION_SMALL_0)", "v->progress = 0;", "v->progress++;", "(v->progress & 3) == 0",
                "IncrementSprite(v, SPR_EXPLOSION_SMALL_B)", "delete v;")
    if not all(part in tick for part in required) or any(part in tick for part in ("v->x_pos", "v->y_pos", "v->z_pos")):
        raise ValueError("Original small-explosion timing or stationary placement changed; review the oracle")
    clear = landscape_source.split("CmdClearArea(",1)[1].split("TileIndex _cur_tileloop_tile;",1)[0]
    above = effect_source.split("EffectVehicle *CreateEffectVehicleAbove(",1)[1].split("EffectVehicle *CreateEffectVehicleRel(",1)[0]
    if not all(part in clear for part in ("Command<CMD_LANDSCAPE_CLEAR>::Do(flags, t)", "_pause_mode.None()",
                                         "CreateEffectVehicleAbove(TileX(t) * TILE_SIZE + TILE_SIZE / 2, TileY(t) * TILE_SIZE + TILE_SIZE / 2, 2",
                                         "TileX(tile) == TileX(start_tile) && TileY(tile) == TileY(start_tile) ? EV_EXPLOSION_SMALL : EV_EXPLOSION_LARGE")) or "GetSlopePixelZ(safe_x, safe_y) + z" not in above:
        raise ValueError("Original single-tile command, altitude or paused suppression changed; review the oracle")
    commands = list(COMMAND.finditer(text))
    if len(commands) != 1:
        raise ValueError("Require one successfully observed original clear-area command")
    tx,ty,x,y,ground,paused = map(int,commands[0].groups())
    if (x,y) != (tx*16+8,ty*16+8) or bool(paused) != expect_paused:
        raise ValueError("Clear-area command lost tile-centre registration or requested pause state")
    current, rows, observations = {}, [], {}
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,px,py,z = map(int,values[:11])
        if kind != 7:
            continue
        if (px,py) != (x,y):
            previous = current.get(vehicle)
            if previous is not None and (frame == previous["last_frame"] or (frame == previous["last_frame"]+1 and progress >= previous["last_progress"])):
                raise ValueError("Continuously captured demolition explosion moved from its tile centre")
            continue
        if match.start() < commands[0].end() or expect_paused:
            raise ValueError("Small explosion preceded its clear-area command or violated paused suppression")
        if not 0 <= progress < 48 or sprite != 3725+progress//4 or not 0 <= climate < 4 or state != 0 or substate != 0:
            raise ValueError("Small explosion lost its original12-frame/48-phase lifetime or animation state")
        origin = tuple(map(float,values[11:14]))
        if z != ground+2 or origin != (x,y,2*ground+2) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Small explosion lost original two-unit local altitude, opacity or unclickable ownership")
        sample, observation = (frame,vehicle), (progress,climate)
        if sample in observations:
            if observations[sample] != observation:
                raise ValueError("One captured frame contains conflicting explosion states")
            continue
        observations[sample] = observation
        row = current.get(vehicle)
        boundary = None
        if row is None:
            boundary = "first captured observation"
        elif frame < row["last_frame"]:
            raise ValueError("Explosion trace is not in captured-frame order")
        elif progress < row["last_progress"]:
            boundary = "original pool ID reused after lifetime reset"
        elif frame > row["last_frame"]+1:
            boundary = "uncaptured frame gap; lifetime continuity is unproven"
        elif climate != row["climate"]:
            raise ValueError("Continuously captured explosion changed climate")
        if boundary is not None:
            row = {"vehicle":vehicle,"climate":climate,"first_frame":frame,"last_frame":frame,
                   "first_progress":progress,"last_progress":progress,"phases":set(),"sprites":set(),
                   "longest_phase_run":1,"current_phase_run":1,"phase_gaps":0,"boundary":boundary}
            current[vehicle] = row
            rows.append(row)
        else:
            delta = progress-row["last_progress"]
            if delta == 1:
                row["current_phase_run"] += 1
            elif delta > 1:
                row["phase_gaps"] += 1
                row["current_phase_run"] = 1
        row["last_frame"], row["last_progress"] = frame, progress
        row["longest_phase_run"] = max(row["longest_phase_run"],row["current_phase_run"])
        row["phases"].add(progress)
        row["sprites"].add(sprite)
    if not observations and not expect_paused:
        raise ValueError("No original small voxel-explosion records at the cleared tile")
    for row in rows:
        row["complete_presented_lifetime"] = row["phases"] == set(range(48)) and row["longest_phase_run"] == 48
        row["phases"], row["sprites"] = sorted(row["phases"]), sorted(row["sprites"])
        del row["current_phase_run"]
    return {"samples":len(observations),"source_frames":12,"original_progress_phases":48,"first_presented_progress":0,
            "cleared_tile":[tx,ty],"raw_anchor":[x,y,ground+2],"rendered_origin":[x,y,2*ground+2],"paused_suppression":expect_paused,
            "observed_source_sprites":sorted({s for row in rows for s in row["sprites"]}),
            "complete_presented_lifetimes":sum(row["complete_presented_lifetime"] for row in rows),"lifetimes":rows,
            "scope":"Original single-tile clear-area command: ordered48-phase lifetime from progress0, stationary tile-centre XYZ, unchanged two-unit local altitude, doubled terrain datum, opacity1 and unclickable ownership. Other emitters, RNG-selected spawn frequency and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--require-complete",action="store_true")
    mode.add_argument("--expect-paused",action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log, sources = args.log.read_bytes(), [path.read_bytes() for path in SOURCES]
    report = audit(log.decode(),*(source.decode() for source in sources),args.expect_paused)
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),
                  original_source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(source).hexdigest() for path,source in zip(SOURCES,sources)})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "lifetimes"}))
    if args.require_complete and not report["complete_presented_lifetimes"]:
        raise SystemExit("No complete ordered demolition-explosion lifetime observed; partial evidence retained")


if __name__ == "__main__":
    main()

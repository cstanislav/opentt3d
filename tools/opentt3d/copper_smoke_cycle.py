#!/usr/bin/env python3
"""Audit original copper-mine smoke from a fixed-view --trace-effects log.

The five smoke sprites are also used by crash and aircraft-breakdown effects;
this oracle covers only actual copper-mine puffs at their original ground-relative
anchor. It observes upstream states without creating effects or consuming RNG.
"""
import argparse
import hashlib
import json
from pathlib import Path

from bulldozer_motion import TRACE


ROOT = Path(__file__).resolve().parents[2]
SOURCES = (ROOT / "src/effectvehicle.cpp", ROOT / "src/industry_cmd.cpp", ROOT / "src/openttd.cpp")


def audit(text, effect_source, industry_source, game_source):
    tick = effect_source.split("static void SmokeInit(",1)[1].split("static void ExplosionLargeInit(",1)[0]
    required = ("Set(SPR_SMOKE_0)", "v->progress = 12;", "v->progress++;", "(v->progress & 3) == 0",
                "v->z_pos++;", "(v->progress & 0xF) == 4", "IncrementSprite(v, SPR_SMOKE_4)", "delete v;")
    create = "CreateEffectVehicleAbove(TileX(tile) * TILE_SIZE + 6, TileY(tile) * TILE_SIZE + 6, 43, EV_COPPER_MINE_SMOKE)"
    above = effect_source.split("EffectVehicle *CreateEffectVehicleAbove(",1)[1].split("EffectVehicle *CreateEffectVehicleRel(",1)[0]
    loop = game_source.split("void StateGameLoop()",1)[1].split("void GameLoop()",1)[0]
    if not all(part in tick for part in required) or create not in industry_source or "GetSlopePixelZ(safe_x, safe_y) + z" not in above:
        raise ValueError("Original copper-mine smoke timing, anchor or ground-relative spawn changed; review the oracle")
    if "RunTileLoop();\n\t\tCallVehicleTicks();" not in loop:
        raise ValueError("Original industry-before-vehicle tick order changed; review the oracle")

    current, rows, observations = {}, [], {}
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,x,y,z = map(int,values[:11])
        if kind != 11:
            continue
        if not 12 <= progress < 84 or sprite != 2040+(progress-4)//16 or climate != 2:
            raise ValueError("Copper-mine smoke lost the original five-frame lifetime or tropical climate")
        rise = progress//4-3
        origin = tuple(map(float,values[11:14]))
        if x%16 != 6 or y%16 != 6 or origin != (x,y,2*z-43-rise) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Copper-mine smoke lost original anchor, rise, local altitude, opacity or unclickable ownership")
        anchor = (x,y,z-rise)
        sample, observation = (frame,vehicle), (progress,anchor)
        if sample in observations:
            if observations[sample] != observation:
                raise ValueError("One captured frame contains conflicting copper-smoke states")
            continue
        observations[sample] = observation
        row = current.get(vehicle)
        boundary = None
        if row is None:
            boundary = "first captured observation"
        elif frame < row["last_frame"]:
            raise ValueError("Copper-smoke trace is not in captured-frame order")
        elif progress < row["last_progress"]:
            boundary = "original pool ID reused after lifetime reset"
        elif anchor != row["anchor"]:
            if frame <= row["last_frame"]+1:
                raise ValueError("Continuously captured copper smoke moved from its original rise anchor")
            boundary = "anchor changed across an uncaptured gap; lifetime boundary is ambiguous"
        if boundary is not None:
            row = {"vehicle":vehicle,"anchor":anchor,"first_frame":frame,"last_frame":frame,
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
        row["last_frame"] = frame
        row["last_progress"] = progress
        row["longest_phase_run"] = max(row["longest_phase_run"],row["current_phase_run"])
        row["phases"].add(progress)
        row["sprites"].add(sprite)
    if not observations:
        raise ValueError("No original voxel copper-mine smoke trace records were found")
    for row in rows:
        # Industry tile processing precedes the original vehicle tick loop. The
        # newly created puff therefore first presents13, regardless of pool ID.
        row["complete_presented_lifetime"] = set(range(13,84)) <= row["phases"] and row["longest_phase_run"] >= 71
        row["phases"], row["sprites"] = sorted(row["phases"]), sorted(row["sprites"])
        del row["current_phase_run"]
    return {"samples":len(observations),"source_frames":5,"original_progress_phases":72,"first_presented_progress":13,
            "observed_source_sprites":sorted({s for row in rows for s in row["sprites"]}),
            "complete_presented_lifetimes":sum(row["complete_presented_lifetime"] for row in rows),"lifetimes":rows,
            "scope":"Captured tropical copper-mine smoke: ordered original sprite/progress lifetime, stationary XY, four-tick rise and43-unit local spawn altitude. Crash and aircraft emitters, hidden puffs, deletion and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--require-complete",action="store_true",help="Require an ordered71-phase presented lifetime from one puff")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log, sources = args.log.read_bytes(), [path.read_bytes() for path in SOURCES]
    report = audit(log.decode(),*(source.decode() for source in sources))
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),
                  original_source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(source).hexdigest() for path,source in zip(SOURCES,sources)})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "lifetimes"}))
    if args.require_complete and not report["complete_presented_lifetimes"]:
        raise SystemExit("No complete ordered copper-smoke lifetime observed; partial evidence retained")


if __name__ == "__main__":
    main()

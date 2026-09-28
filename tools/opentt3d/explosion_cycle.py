#!/usr/bin/env python3
"""Observe original large train-crash explosions in a flat-track --trace-effects log.

The ordinary opposing-train fixture allocates effects after both locomotives in
the original pool. Its explosions first present progress1 and keep63 ordered
phases across16 source sprites. This audit never creates effects or consumes RNG.
"""
import argparse
import hashlib
import json
from pathlib import Path

from bulldozer_motion import TRACE


ROOT = Path(__file__).resolve().parents[2]
SOURCES = tuple(ROOT / name for name in ("src/effectvehicle.cpp", "src/train_cmd.cpp", "src/vehicle.cpp", "src/core/pool_type.hpp"))


def audit(text, effect_source, train_source, vehicle_source, pool_source, emitters):
    tick = effect_source.split("static void ExplosionLargeInit(",1)[1].split("static void BreakdownSmokeInit(",1)[0]
    required = ("Set(SPR_EXPLOSION_LARGE_0)", "v->progress = 0;", "v->progress++;", "(v->progress & 3) == 0",
                "IncrementSprite(v, SPR_EXPLOSION_LARGE_F)", "delete v;")
    crash = train_source.split("static bool HandleCrashedTrain(",1)[1].split("/** Maximum speeds",1)[0]
    if not all(part in tick for part in required) or any(part in tick for part in ("v->x_pos", "v->y_pos", "v->z_pos")):
        raise ValueError("Original large-explosion timing or stationary placement changed; review the oracle")
    if "state == 4" not in crash or "CreateEffectVehicleRel(v, 4, 4, 8, EV_EXPLOSION_LARGE)" not in crash:
        raise ValueError("Original train crash emission or eight-unit altitude changed; review the oracle")
    loop = vehicle_source.split("void CallVehicleTicks()",1)[1].split("switch (v->type)",1)[0]
    iterator = pool_source.split("struct PoolIterator {",1)[1].split("struct IterateWrapper {",1)[0]
    if not emitters or min(emitters)<0 or not all(part in loop for part in ("for (Vehicle *v : Vehicle::Iterate())", "!v->Tick()")) or not all(part in iterator for part in ("this->index++; this->ValidateIndex();", "this->index < T::GetPoolSize()")):
        raise ValueError("Original ascending vehicle/effect tick order or fixture emitters changed; review the oracle")

    current, rows, observations = {}, [], {}
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,x,y,z = map(int,values[:11])
        if kind != 5:
            continue
        if not 0 <= progress < 64 or sprite != 3709+progress//4 or not 0 <= climate < 4 or state != 0 or substate != 0:
            raise ValueError("Large explosion lost its original16-frame lifetime or animation state")
        if vehicle <= max(emitters):
            raise ValueError("This fixture requires explosion pool IDs after every emitting locomotive")
        origin = tuple(map(float,values[11:14]))
        if origin != (x,y,2*z-8) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Flat-track explosion lost original local altitude, opacity or unclickable ownership")
        anchor = (x,y,z)
        sample, observation = (frame,vehicle), (progress,anchor,climate)
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
        elif anchor != row["anchor"] or climate != row["climate"]:
            raise ValueError("Continuously captured explosion moved from its original stationary anchor")
        if boundary is not None:
            row = {"vehicle":vehicle,"anchor":anchor,"climate":climate,"first_frame":frame,"last_frame":frame,
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
    if not observations:
        raise ValueError("No original large voxel-explosion trace records were found")
    for row in rows:
        row["complete_presented_lifetime"] = set(range(1,64)) <= row["phases"] and row["longest_phase_run"] >= 63
        row["phases"], row["sprites"] = sorted(row["phases"]), sorted(row["sprites"])
        del row["current_phase_run"]
    return {"samples":len(observations),"source_frames":16,"original_progress_phases":64,"first_presented_progress":1,
            "emitting_locomotives":sorted(set(emitters)),"observed_source_sprites":sorted({s for row in rows for s in row["sprites"]}),
            "complete_presented_lifetimes":sum(row["complete_presented_lifetime"] for row in rows),"lifetimes":rows,
            "scope":"Captured flat-track train-crash large explosions: ordered original sprite/progress lifetime, stationary XYZ and eight-unit local spawn altitude. Lower-ID effects, other emitters, hidden states, deletion and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--emitters",type=int,nargs="+",required=True,help="Every emitting locomotive pool ID in the ordinary flat-track fixture")
    parser.add_argument("--require-complete",action="store_true",help="Require an ordered63-phase presented lifetime from one effect")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log, sources = args.log.read_bytes(), [path.read_bytes() for path in SOURCES]
    report = audit(log.decode(),*(source.decode() for source in sources),args.emitters)
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),
                  original_source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(source).hexdigest() for path,source in zip(SOURCES,sources)})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "lifetimes"}))
    if args.require_complete and not report["complete_presented_lifetimes"]:
        raise SystemExit("No complete ordered explosion lifetime observed; partial evidence retained")


if __name__ == "__main__":
    main()

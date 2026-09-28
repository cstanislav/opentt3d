#!/usr/bin/env python3
"""Audit original electric-train spark lifetimes from a flat-track native trace.

Original progress starts at1 and wraps0..2 as six source sprites advance. Sparks
stay at their original spawned XYZ. Their final two source sprites are identical
artwork but remain distinct original animation states. This read-only audit never
creates or ticks effects and never consumes simulation RNG.
"""
import argparse
import hashlib
import json
from pathlib import Path

from bulldozer_motion import TRACE
from steam_cycle import ROOT, SOURCES


def audit(text, effect_source, vehicle_source, pool_source, emitter):
    source = effect_source.split("static void ElectricSparkInit(",1)[1].split("static void SmokeInit(",1)[0]
    required = ("Set(SPR_ELECTRIC_SPARK_0)", "v->progress = 1;", "if (v->progress < 2)",
                "v->progress++;", "v->progress = 0;", "IncrementSprite(v, SPR_ELECTRIC_SPARK_5)", "delete v;")
    if not all(part in source for part in required) or "v->z_pos" in source or "CreateEffectVehicleRel(v, x, y, 10, evt)" not in vehicle_source:
        raise ValueError("Original electric spark progress, stationary placement or spawn offset changed; review the oracle")
    loop = vehicle_source.split("void CallVehicleTicks()",1)[1].split("switch (v->type)",1)[0]
    iterator = pool_source.split("struct PoolIterator {",1)[1].split("struct IterateWrapper {",1)[0]
    if emitter < 0 or not all(part in loop for part in ("for (Vehicle *v : Vehicle::Iterate())", "!v->Tick()")) or not all(part in iterator for part in ("this->index++; this->ValidateIndex();", "this->index < T::GetPoolSize()")):
        raise ValueError("Original ascending vehicle/effect tick order changed; review the oracle")

    current, rows, observations, climates = {}, [], {}, set()
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,x,y,z = map(int,values[:11])
        if kind != 3:
            continue
        phase = (sprite-3084)*3+progress
        if not 3084 <= sprite <= 3089 or not 0 <= progress < 3 or not 1 <= phase < 18 or climate >= 4:
            raise ValueError("Electric spark sprite or progress differs from the original six-frame lifetime")
        origin = tuple(map(float,values[11:14]))
        if origin != (x,y,2*z-10) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Flat-track electric spark lost original local altitude, opacity or unclickable ownership")
        if vehicle == emitter:
            raise ValueError("The emitting locomotive cannot also be an effect pool item")
        first_presented = 1+int(vehicle > emitter)
        anchor = (x,y,z)
        sample, observation = (frame,vehicle), (climate,phase,anchor)
        if sample in observations:
            if observations[sample] != observation:
                raise ValueError("One captured frame contains conflicting spark states")
            continue
        observations[sample] = observation
        row = current.get(vehicle)
        boundary = None
        if row is None:
            boundary = "first captured observation"
        elif frame < row["last_frame"]:
            raise ValueError("Electric spark trace is not in captured-frame order")
        elif phase < row["last_phase"]:
            boundary = "original pool ID reused after lifetime reset"
        elif anchor != row["anchor"] or climate != row["climate"]:
            if frame <= row["last_frame"]+1:
                raise ValueError("Continuously captured spark moved from its original stationary anchor")
            boundary = "anchor changed across an uncaptured gap; lifetime boundary is ambiguous"
        if boundary is not None:
            row = {"vehicle":vehicle,"anchor":anchor,"climate":climate,"first_frame":frame,"last_frame":frame,
                   "first_phase":phase,"last_phase":phase,"phases":set(),"sprites":set(),
                   "longest_phase_run":1,"current_phase_run":1,"phase_gaps":0,"boundary":boundary,
                   "first_presented_phase":first_presented}
            current[vehicle] = row
            rows.append(row)
        else:
            delta = phase-row["last_phase"]
            if delta == 1:
                row["current_phase_run"] += 1
            elif delta > 1:
                row["phase_gaps"] += 1
                row["current_phase_run"] = 1
        row["last_frame"] = frame
        row["last_phase"] = phase
        row["longest_phase_run"] = max(row["longest_phase_run"],row["current_phase_run"])
        row["phases"].add(phase)
        row["sprites"].add(sprite)
        climates.add(climate)
    if not observations:
        raise ValueError("No original voxel electric spark trace records were found")
    for row in rows:
        expected = set(range(row["first_presented_phase"],18))
        row["complete_presented_lifetime"] = expected <= row["phases"] and row["longest_phase_run"] >= len(expected)
        row["phases"], row["sprites"] = sorted(row["phases"]), sorted(row["sprites"])
        del row["current_phase_run"]
    return {"samples":len(observations),"source_frames":6,"original_lifetime_phases":17,
            "emitter_vehicle":emitter,"first_presented_phase":sorted({row["first_presented_phase"] for row in rows}),
            "observed_climates":sorted(climates),"observed_source_sprites":sorted({s for row in rows for s in row["sprites"]}),
            "complete_presented_lifetimes":sum(row["complete_presented_lifetime"] for row in rows),"lifetimes":rows,
            "scope":"Captured flat-track electric sparks: original ordered sprite/progress lifetime, stationary XYZ and ten-unit spawn altitude. Hidden sparks, deletion, spawning probability and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--emitter",type=int,required=True,help="Pool ID of the sole electric locomotive in this flat-track fixture")
    parser.add_argument("--require-complete",action="store_true",help="Require an ordered complete presented lifetime, including both source-identical final sprites")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log, sources = args.log.read_bytes(), [path.read_bytes() for path in SOURCES]
    report = audit(log.decode(),*(source.decode() for source in sources),emitter=args.emitter)
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),
                  original_source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(source).hexdigest() for path,source in zip(SOURCES,sources)})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "lifetimes"}))
    if args.require_complete and not report["complete_presented_lifetimes"]:
        raise SystemExit("No complete ordered electric spark lifetime observed; partial evidence retained")


if __name__ == "__main__":
    main()

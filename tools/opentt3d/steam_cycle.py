#!/usr/bin/env python3
"""Audit captured original train steam from a fixed-view --trace-effects log.

The flat-track fixture uses the original ten-unit exhaust offset. Each puff stays
at its spawned XY and rises once per eight progress ticks while its five sprites
expand and dissipate. This read-only audit never creates or ticks an effect.
Hidden puffs, deletion and presentation between captured frames remain unverified.
"""
import argparse
import hashlib
import json
from pathlib import Path

from bulldozer_motion import TRACE


ROOT = Path(__file__).resolve().parents[2]
SOURCES = (ROOT / "src/effectvehicle.cpp", ROOT / "src/vehicle.cpp", ROOT / "src/core/pool_type.hpp")


def audit(text, effect_source, vehicle_source, pool_source, emitter=None):
    source = effect_source.split("static void SteamSmokeInit(",1)[1].split("static void DieselSmokeInit(",1)[0]
    required = ("Set(SPR_STEAM_SMOKE_0)", "v->progress = 12;", "v->progress++;",
                "(v->progress & 7) == 0", "v->z_pos++;", "(v->progress & 0xF) == 4",
                "IncrementSprite(v, SPR_STEAM_SMOKE_4)", "delete v;")
    if not all(part in source for part in required) or "CreateEffectVehicleRel(v, x, y, 10, evt)" not in vehicle_source:
        raise ValueError("Original steam progress, rise or spawn offset changed; review the oracle")
    if emitter is not None:
        # This fixture identifies the one actual locomotive that spawns steam.
        # A newly allocated effect after it in the ascending pool ticks before
        # the same simulation step ends, so progress12 is not presented there.
        loop = vehicle_source.split("void CallVehicleTicks()",1)[1].split("switch (v->type)",1)[0]
        iterator = pool_source.split("struct PoolIterator {",1)[1].split("struct IterateWrapper {",1)[0]
        if emitter < 0 or not all(part in loop for part in ("for (Vehicle *v : Vehicle::Iterate())", "!v->Tick()")) or not all(part in iterator for part in ("this->index++; this->ValidateIndex();", "this->index < T::GetPoolSize()")):
            raise ValueError("Original ascending vehicle/effect tick order changed; review the oracle")

    current, rows, observations, climates = {}, [], {}, set()
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,x,y,z = map(int,values[:11])
        if kind != 1:
            continue
        if not 12 <= progress < 84 or sprite != 3079+(progress-4)//16 or climate >= 4:
            raise ValueError("Steam sprite or progress differs from the original five-frame lifetime")
        rise = progress//8-1
        origin = tuple(map(float,values[11:14]))
        if origin != (x,y,2*z-10-rise) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Flat-track steam lost original rise, local altitude, opacity or unclickable ownership")
        anchor = (x,y,z-rise)
        if vehicle == emitter:
            raise ValueError("The emitting locomotive cannot also be an effect pool item")
        first_presented = 13 if emitter is not None and vehicle > emitter else 12
        sample, observation = (frame,vehicle), (climate,progress,anchor)
        if sample in observations:
            if observations[sample] != observation:
                raise ValueError("One captured frame contains conflicting steam states")
            continue
        observations[sample] = observation
        row = current.get(vehicle)
        boundary = None
        if row is None:
            boundary = "first captured observation"
        elif frame < row["last_frame"]:
            raise ValueError("Steam trace is not in captured-frame order")
        elif progress < row["last_progress"]:
            boundary = "original pool ID reused after progress reset"
        elif anchor != row["anchor"] or climate != row["climate"]:
            if frame <= row["last_frame"]+1:
                raise ValueError("Continuously captured steam moved horizontally or changed its rise anchor")
            # A pool ID may be deleted and reused outside this fixed viewport.
            # Do not join such observations into an invented complete lifetime.
            boundary = "anchor changed across an uncaptured gap; lifetime boundary is ambiguous"
        if boundary is not None:
            row = {"vehicle":vehicle,"anchor":anchor,"climate":climate,"first_frame":frame,"last_frame":frame,
                   "first_progress":progress,"last_progress":progress,"phases":set(),"sprites":set(),
                   "longest_phase_run":1,"current_phase_run":1,"phase_gaps":0,"boundary":boundary,
                   "first_presented_progress":first_presented}
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
        climates.add(climate)
    if not observations:
        raise ValueError("No original voxel steam trace records were found")
    for row in rows:
        expected = set(range(row["first_presented_progress"],84))
        row["complete_presented_lifetime"] = expected <= row["phases"] and row["longest_phase_run"] >= len(expected)
        row["phases"], row["sprites"] = sorted(row["phases"]), sorted(row["sprites"])
        del row["current_phase_run"]
    return {"samples":len(observations),"source_frames":5,"original_progress_phases":72,
            "emitter_vehicle":emitter,"first_presented_progress":sorted({row["first_presented_progress"] for row in rows}),
            "observed_climates":sorted(climates),"observed_source_sprites":sorted({s for row in rows for s in row["sprites"]}),
            "complete_presented_lifetimes":sum(row["complete_presented_lifetime"] for row in rows),"lifetimes":rows,
            "scope":"Captured flat-track steam progress, stationary XY, original rise and ten-unit spawn altitude. Hidden puffs, deletion and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--emitter",type=int,help="Pool ID of the sole steam locomotive in this flat-track fixture; account for its original same-tick effect update")
    parser.add_argument("--require-complete",action="store_true",help="Require at least one completely observed ordered original steam lifetime")
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
        raise SystemExit("No complete original steam lifetime observed; partial evidence retained")


if __name__ == "__main__":
    main()

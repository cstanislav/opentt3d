#!/usr/bin/env python3
"""Observe original small crash explosions without creating effects or drawing RNG.

Use the ordinary flat-track opposing-locomotive fixture with both large and small
voxel families in a diagnostic catalogue. Large-explosion anchors independently
locate the stopped locomotives; small effects must keep original random offsets.
"""
import argparse
import hashlib
import json
from pathlib import Path

from bulldozer_motion import TRACE
from explosion_cycle import audit as large_audit, ROOT, SOURCES


def audit(text, effect_source, train_source, vehicle_source, pool_source, emitters):
    tick = effect_source.split("static void ExplosionSmallInit(",1)[1].split("static void BulldozerInit(",1)[0]
    required = ("Set(SPR_EXPLOSION_SMALL_0)", "v->progress = 0;", "v->progress++;", "(v->progress & 3) == 0",
                "IncrementSprite(v, SPR_EXPLOSION_SMALL_B)", "delete v;")
    crash = train_source.split("static bool HandleCrashedTrain(",1)[1].split("/** Maximum speeds",1)[0]
    if not all(part in tick for part in required) or any(part in tick for part in ("v->x_pos", "v->y_pos", "v->z_pos")):
        raise ValueError("Original small-explosion timing or stationary placement changed; review the oracle")
    if not all(part in crash for part in ("state <= 200 && Chance16R(1, 7, r)", "r = Random();", "CreateEffectVehicleRel(u,",
                                         "GB(r,  8, 3) + 2", "GB(r, 16, 3) + 2", "GB(r,  0, 3) + 5", "EV_EXPLOSION_SMALL")):
        raise ValueError("Original random crash offsets or emission changed; review the oracle")
    # This also checks the source's ascending pool order and large-effect origin.
    large = large_audit(text,effect_source,train_source,vehicle_source,pool_source,emitters)
    anchors = sorted({(row["anchor"][0]-4,row["anchor"][1]-4,row["anchor"][2]-8,row["climate"]) for row in large["lifetimes"]})
    if len(anchors) != len(set(emitters)):
        raise ValueError("Need one distinct observed large-explosion anchor per stopped fixture locomotive")
    current, rows, observations = {}, [], {}
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,x,y,z = map(int,values[:11])
        if kind != 7:
            continue
        if not 0 <= progress < 48 or sprite != 3725+progress//4 or not 0 <= climate < 4 or state != 0 or substate != 0:
            raise ValueError("Small explosion lost its original12-frame lifetime or animation state")
        if vehicle <= max(emitters):
            raise ValueError("This fixture requires explosion pool IDs after every emitting locomotive")
        candidates = [a for a in anchors if a[3] == climate and 2 <= x-a[0] <= 9 and 2 <= y-a[1] <= 9 and 5 <= z-a[2] <= 12]
        origin = tuple(map(float,values[11:14]))
        if not candidates or not any(origin == (x,y,z+a[2]) for a in candidates) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Small explosion lost original random offsets, local altitude, opacity or unclickable ownership")
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
                   "longest_phase_run":1,"current_phase_run":1,"phase_gaps":0,"boundary":boundary,
                   "possible_spawn_offsets":[[x-a[0],y-a[1],z-a[2]] for a in candidates]}
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
        raise ValueError("No original small voxel-explosion trace records were found")
    for row in rows:
        row["complete_presented_lifetime"] = set(range(1,48)) <= row["phases"] and row["longest_phase_run"] >= 47
        row["phases"], row["sprites"] = sorted(row["phases"]), sorted(row["sprites"])
        del row["current_phase_run"]
    return {"samples":len(observations),"source_frames":12,"original_progress_phases":48,"first_presented_progress":1,
            "emitting_locomotives":sorted(set(emitters)),"observed_locomotive_anchors":anchors,
            "observed_source_sprites":sorted({s for row in rows for s in row["sprites"]}),
            "complete_presented_lifetimes":sum(row["complete_presented_lifetime"] for row in rows),"lifetimes":rows,
            "scope":"Captured flat-track single-locomotive crash effects: ordered47-phase presented lifetime, stationary XYZ, original XY offsets2…9 and local altitude5…12 relative to observed large-explosion emitter anchors. Exact random draws, spawn frequency, other emitters, lower-ID effects, hidden states and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--emitters",type=int,nargs="+",required=True,help="Every single-locomotive pool ID in the flat-track fixture")
    parser.add_argument("--require-complete",action="store_true",help="Require an ordered47-phase presented lifetime from one effect")
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
        raise SystemExit("No complete ordered small-explosion lifetime observed; partial evidence retained")


if __name__ == "__main__":
    main()

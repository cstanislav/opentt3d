#!/usr/bin/env python3
"""Read original train-breakdown smoke countdowns and their captured stopped emitter.

An ordinary --vehicle-breakdowns 2 --wait-breakdown train fixture supplies the save.
This oracle never creates effects, assigns breakdown state, ticks vehicles or draws RNG.
Progress is an upstream eight-bit counter: wrapping255→0 is not pool-ID reuse.
Complete lifetimes require every countdown phase through1 from the original spawn.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from bulldozer_motion import NUMBER, TRACE


ROOT = Path(__file__).resolve().parents[2]
SOURCES = (ROOT / "src/effectvehicle.cpp", ROOT / "src/vehicle.cpp")
EMITTER = re.compile(rf"breakdown train frame (\d+) vehicle (\d+) engine (\d+) delay (\d+) raw (-?\d+),(-?\d+),(-?\d+) origin ({NUMBER}),({NUMBER}),({NUMBER})")


def audit(text, effect_source, vehicle_source, emitter, engine=None, expect_none=False):
    tick = effect_source.split("static void BreakdownSmokeInit(",1)[1].split("static void ExplosionSmallInit(",1)[0]
    required = ("Set(SPR_BREAKDOWN_SMOKE_0)", "v->progress = 0;", "v->progress++;", "(v->progress & 7) == 0",
                "IncrementSprite(v, SPR_BREAKDOWN_SMOKE_3)", "v->animation_state--;", "v->animation_state == 0", "delete v;")
    spawn = vehicle_source.split("bool Vehicle::HandleBreakdown()",1)[1].split("Update economy age",1)[0]
    relative = effect_source.split("EffectVehicle *CreateEffectVehicleRel(",1)[1].split("bool EffectVehicle::Tick()",1)[0]
    if (not all(part in tick for part in required) or
            "CreateEffectVehicleRel(this, 4, 4, 5, EV_BREAKDOWN_SMOKE)" not in spawn or
            "u->animation_state = this->breakdown_delay * 2;" not in spawn or "this->cur_speed = 0;" not in spawn or
            "if (--this->breakdown_delay == 0)" not in spawn or "this->breakdown_ctr = 0;" not in spawn or
            "v->breakdown_delay  = GB(r, 24, 7) + 0x80;" not in vehicle_source or
            "v->x_pos + x, v->y_pos + y, v->z_pos + z" not in relative):
        raise ValueError("Original breakdown smoke timing, countdown, stopped emitter or relative spawn changed; review the oracle")
    emitters = {}
    for match in EMITTER.finditer(text):
        values = match.groups()
        frame,vehicle,selected,delay,x,y,z = map(int,values[:7])
        if vehicle != emitter:
            continue
        origin = tuple(map(float,values[7:10]))
        if delay <= 0 or (engine is not None and selected != engine) or origin[2] != 2*z:
            raise ValueError("Original flat-track breakdown emitter lost its engine, delay or doubled terrain datum")
        sample = (selected,delay,x,y,z,origin)
        if frame in emitters and emitters[frame] != sample:
            raise ValueError("One captured frame contains conflicting original breakdown emitters")
        emitters[frame] = sample

    current, rows, observations = {}, [], {}
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,remaining,substate,progress,x,y,z = map(int,values[:11])
        if kind != 6:
            continue
        if expect_none:
            raise ValueError("Expected absence contains original breakdown smoke")
        if not 1 <= remaining <= 510 or not 0 <= progress <= 255 or substate != 0 or climate not in range(4) or sprite != 3737+(progress//8)%4:
            raise ValueError("Breakdown smoke lost its original four-state/eight-tick sprite cycle or countdown")
        origin = tuple(map(float,values[11:14]))
        anchor = (x,y,z)
        if origin != (x,y,2*z-5) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Breakdown smoke lost original stationary emitter offsets, five-unit altitude, opacity or unclickable ownership")
        key, observation = (frame,vehicle), (remaining,progress,sprite,climate,anchor,origin)
        if key in observations:
            if observations[key] != observation:
                raise ValueError("One captured frame contains conflicting original breakdown smoke")
            continue
        observations[key] = observation
        row = current.get(vehicle)
        boundary = None
        if row is None:
            boundary = "first captured observation"
        elif frame < row["last_frame"]:
            raise ValueError("Breakdown smoke trace is not in captured-frame order")
        elif remaining > row["last_remaining"]:
            boundary = "original pool ID reused after countdown reset"
        elif frame > row["last_frame"]+1:
            boundary = "uncaptured frame gap; complete lifetime cannot be spliced"
        elif anchor != row["anchor"] or climate != row["climate"]:
            raise ValueError("Continuously captured breakdown smoke moved from its original stationary anchor/climate")
        if frame in emitters:
            _,delay,tx,ty,tz,_ = emitters[frame]
            if anchor != (tx+4,ty+4,tz+5):
                raise ValueError("Breakdown smoke lost original stopped-emitter spawn offsets")
        elif boundary is not None:
            raise ValueError("Breakdown smoke lacks its originally captured stopped train emitter at the lifetime boundary")
        # Smoke has its own original countdown. The train can recover just before
        # its final puff ticks; requiring a still-broken parent for those frames
        # rejects valid upstream behavior. Retain the independently captured spawn
        # anchor, never move it with the recovered parent or splice a capture gap.
        if boundary is not None:
            first = 0 if vehicle < emitter else 1
            duration = remaining+first if progress == first else None
            if duration is not None and (duration not in range(256,511) or duration%2):
                duration = None
            row = {"vehicle":vehicle,"emitter":emitter,"climate":climate,"anchor":anchor,"first_frame":frame,"last_frame":frame,
                   "first_progress":progress,"last_progress":progress,"first_remaining":remaining,"last_remaining":remaining,
                   "first_presented_progress":first,"original_duration":duration,"countdown_phases":set(),"sprites":set(),
                   "spawn_emitter_frame":frame,"joint_emitter_samples":0,"anchored_without_stopped_emitter":0,
                   "phase_gaps":0,"current_phase_run":1,"longest_phase_run":1,"boundary":boundary}
            current[vehicle] = row
            rows.append(row)
        else:
            delta = row["last_remaining"]-remaining
            if (progress-row["last_progress"])%256 != delta%256:
                raise ValueError("Breakdown smoke countdown and original wrapped progress disagree")
            if delta == 1:
                row["current_phase_run"] += 1
            elif delta > 1:
                row["phase_gaps"] += 1
                row["current_phase_run"] = 1
        row["last_frame"], row["last_remaining"], row["last_progress"] = frame, remaining, progress
        row["longest_phase_run"] = max(row["longest_phase_run"],row["current_phase_run"])
        row["countdown_phases"].add(remaining)
        row["sprites"].add(sprite)
        row["joint_emitter_samples"] += frame in emitters
        row["anchored_without_stopped_emitter"] += frame not in emitters
    if not observations and not expect_none:
        raise ValueError("No original voxel train-breakdown smoke trace records were found")
    for row in rows:
        count = row["original_duration"]-row["first_presented_progress"] if row["original_duration"] is not None else 0
        row["complete_presented_lifetime"] = bool(count) and row["countdown_phases"] == set(range(1,count+1)) and row["longest_phase_run"] >= count
        row["countdown_phases"], row["sprites"] = sorted(row["countdown_phases"]), sorted(row["sprites"])
        del row["current_phase_run"]
    return {"samples":len(observations),"emitter_samples":len(emitters),"source_frames":4,"original_cycle_phases":32,
            "observed_source_sprites":sorted({sprite for row in rows for sprite in row["sprites"]}),
            "complete_presented_lifetimes":sum(row["complete_presented_lifetime"] for row in rows),"lifetimes":rows,"expected_absence":expect_none,
            "scope":"Captured flat-track original train breakdowns: every presented countdown phase, eight-bit progress wrap and four-source cycle. Each lifetime boundary requires the originally captured stopped-emitter XY+4/+4 and five-unit spawn altitude; the independently stationary puff can outlive its stopped parent. Captures preserve doubled terrain datum, opacity1 and zero picking without moving the anchored puff or splicing gaps. Random failure frequency, hidden effects, nonflat terrain, road/ship/aircraft contexts and between-frame presentation remain unverified.","final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--emitter",type=int,required=True)
    parser.add_argument("--engine",type=int)
    gate = parser.add_mutually_exclusive_group()
    gate.add_argument("--require-complete",action="store_true")
    gate.add_argument("--expect-none",action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log, sources = args.log.read_bytes(), [path.read_bytes() for path in SOURCES]
    report = audit(log.decode(),*(source.decode() for source in sources),args.emitter,args.engine,args.expect_none)
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),
                  original_source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(source).hexdigest() for path,source in zip(SOURCES,sources)})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "lifetimes"}))
    if args.require_complete and not report["complete_presented_lifetimes"]:
        raise SystemExit("No complete original breakdown-smoke countdown observed; partial evidence retained")


if __name__ == "__main__":
    main()

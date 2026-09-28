#!/usr/bin/env python3
"""Audit captured stationary power-plant smoke from a fixed-view --trace-effects log.

Observe the original eight sprite frames and eight countdown values, including
wraparound, at the original chimney anchor. This read-only check covers captured
flat power plants; hidden effects, destruction and between-frame motion remain
outside its scope. No effects are created and no simulation ticks run here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from bulldozer_motion import TRACE


ROOT = Path(__file__).resolve().parents[2]
SOURCES = (ROOT / "src/effectvehicle.cpp", ROOT / "src/industry_cmd.cpp", ROOT / "src/table/sprites.h")


def audit(text, effect_source, industry_source, sprite_source):
    tick = effect_source.split("static bool ChimneySmokeTick(",1)[1].split("static void SteamSmokeInit(",1)[0]
    create = industry_source.split("static void CreateChimneySmoke(",1)[1].split("static void MakeIndustryTileBigger(",1)[0]
    if not all(part in tick for part in ("v->progress > 0", "v->progress--;", "v->progress = 7;",
                                         "IncrementSprite(v, SPR_CHIMNEY_SMOKE_7)", "Set(SPR_CHIMNEY_SMOKE_0)")):
        raise ValueError("Original chimney countdown changed; review the oracle")
    if "CreateEffectVehicle(x + 15, y + 14, z + 59, EV_CHIMNEY_SMOKE)" not in create:
        raise ValueError("Original chimney anchor changed; review the oracle")
    sprites = [int(value) for frame,value in re.findall(r"SPR_CHIMNEY_SMOKE_(\d+) = (\d+);",sprite_source)]
    if sprites != list(range(3701,3709)):
        raise ValueError("Original chimney sprite range changed; review the oracle")

    records, samples, observations = {}, set(), {}
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,x,y,z = map(int,values[:11])
        if kind != 0:
            continue
        if sprite not in sprites or progress > 7 or climate >= 4:
            raise ValueError("Unknown original chimney sprite, countdown or climate")
        origin = tuple(map(float,values[11:14]))
        if x%16 != 15 or y%16 != 14 or origin != (x,y,2*z-59) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Chimney lost original anchor, local altitude, opacity or unclickable ownership")
        phase = (sprite-sprites[0])*8+(7-progress)
        sample = (frame,vehicle)
        observation = (climate,x,y,z,phase)
        if sample in observations:
            if observations[sample] != observation:
                raise ValueError("One captured frame contains conflicting chimney states")
            continue
        observations[sample] = observation
        row = records.setdefault(vehicle,{
            "vehicle":vehicle,"climate":climate,"anchor":(x,y,z),"first_frame":frame,"last_frame":frame,
            "phases":set(),"sprites":set(),"sequential_tick_steps":0,"phase_discontinuities":0,
            "last_phase":None,"current_phase_run":1,"longest_phase_run":1,
        })
        if row["anchor"] != (x,y,z) or row["climate"] != climate:
            raise ValueError("Stationary chimney moved or changed climate; separate reused IDs/lifetimes")
        if frame < row["last_frame"]:
            raise ValueError("Chimney trace is not in captured-frame order")
        if row["last_phase"] is not None:
            delta = (phase-row["last_phase"])%64
            if delta == 1:
                row["sequential_tick_steps"] += 1
                row["current_phase_run"] += 1
            elif delta != 0:
                # The renderer may miss ticks. Preserve this gap rather than
                # treating an unordered set of states as a complete cycle.
                row["phase_discontinuities"] += 1
                row["current_phase_run"] = 1
        row["last_phase"] = phase
        row["last_frame"] = frame
        row["longest_phase_run"] = max(row["longest_phase_run"],row["current_phase_run"])
        row["phases"].add(phase)
        row["sprites"].add(sprite)
        samples.add(sample)
    if not samples:
        raise ValueError("No original voxel chimney trace records were found")
    for row in records.values():
        row["all_original_phases_observed"] = row["phases"] == set(range(64))
        row["complete_ordered_cycle"] = row["longest_phase_run"] >= 65
        for key in ("phases","sprites"):
            row[key] = sorted(row[key])
        del row["current_phase_run"]
    return {"samples":len(samples),"stationary_chimneys":len(records),"original_source_frames":8,
            "original_progress_phases":64,"complete_ordered_cycles":sum(row["complete_ordered_cycle"] for row in records.values()),
            "all_original_phases_observed":all(row["all_original_phases_observed"] for row in records.values()),
            "chimneys":list(records.values()),"scope":"Captured stationary chimney sprite/countdown cycles and original flat-factory-relative placement. Hidden effects, destruction and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--require-complete",action="store_true",help="Require every captured chimney to show a full ordered original countdown cycle")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log = args.log.read_bytes()
    sources = [path.read_bytes() for path in SOURCES]
    report = audit(log.decode(),*(source.decode() for source in sources))
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),
                  original_source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(source).hexdigest() for path,source in zip(SOURCES,sources)})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "chimneys"}))
    if args.require_complete and report["complete_ordered_cycles"] != report["stationary_chimneys"]:
        raise SystemExit("A complete ordered cycle was not observed for every chimney; partial evidence retained")


if __name__ == "__main__":
    main()

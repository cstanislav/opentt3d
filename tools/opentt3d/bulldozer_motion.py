#!/usr/bin/env python3
"""Audit original roadworks motion from a fixed-view --trace-effects native log.

Compare original sprite selection and displacement, including reverse motion,
with the upstream movement table. This covers captured flat roadworks, not
hidden effects or motion between presented frames. No simulation ticks run here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


NUMBER = r"[-+\d.eE]+"
TRACE = re.compile(rf"voxel effect frame (\d+) vehicle (\d+) type (\d+) sprite (\d+) climate (\d+) animation (\d+),(\d+) progress (\d+) raw (-?\d+),(-?\d+),(-?\d+) origin ({NUMBER}),({NUMBER}),({NUMBER}) opacity ({NUMBER}) pick (\d+)")
SOURCE = Path(__file__).resolve().parents[2] / "src/effectvehicle.cpp"


def audit(text, source):
    table = source.split("_bulldozer_movement[] = {",1)[1].split("};",1)[0]
    movement = [tuple(map(int,row)) for row in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+)\s*\}",table)]
    table = source.split("_inc_by_dir[] = {",1)[1].split("};",1)[0]
    increments = [tuple(map(int,row)) for row in re.findall(r"\{\s*(-?\d+),\s*(-?\d+)\s*\}",table)]
    if len(movement) != 20 or len(increments) != 4:
        raise ValueError("The original roadworks movement table changed; review the oracle")
    expected = [(0,0,1416,0,0)]
    x = y = 0
    for state,(direction,image,duration) in enumerate(movement):
        for substate in range(1,duration+1):
            dx,dy = increments[direction]
            x += dx
            y += dy
            next_state = state+(substate == duration)
            if next_state < len(movement):
                expected.append((x,y,1416+image,next_state,0 if substate == duration else substate))
    lookup = {(state,substate):(step,x,y,sprite) for step,(x,y,sprite,state,substate) in enumerate(expected)}
    current, rows, samples, climates = {}, [], set(), set()
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,substate,progress,x,y,z = map(int,values[:11])
        if kind != 8:
            continue
        if (state,substate) not in lookup:
            raise ValueError("Unknown original roadworks animation state")
        step,dx,dy,selected = lookup[state,substate]
        if sprite != selected or progress//8 != step%32:
            raise ValueError("Roadworks sprite or progress differs from its original movement table")
        origin = tuple(map(float,values[11:14]))
        if origin != (x,y,2*z) or float(values[14]) != 1 or int(values[15]) != 0 or climate >= 4:
            raise ValueError("Flat roadworks lost original position, terrain datum, opacity or unclickable ownership")
        anchor = (x-dx,y-dy,z)
        previous = current.get(vehicle)
        if previous is None or step < previous["last_step"]:
            # The original pool can reuse an ID after an effect is deleted.
            previous = {"vehicle":vehicle,"anchor":anchor,"first_frame":frame,"last_frame":frame,
                        "steps":set(),"sprites":set(),"states":set(),"last_step":step}
            current[vehicle] = previous
            rows.append(previous)
        elif previous["anchor"] != anchor:
            raise ValueError("Captured roadworks displacement differs from its original movement table")
        previous["last_step"] = step
        previous["last_frame"] = frame
        previous["steps"].add(step)
        previous["sprites"].add(sprite)
        previous["states"].add(state)
        samples.add((frame,vehicle))
        climates.add(climate)
    if not samples:
        raise ValueError("No original voxel bulldozer trace records were found")
    for row in rows:
        row["complete_presented_path"] = row["steps"] == set(range(len(expected)))
        for key in ("steps","sprites","states"):
            row[key] = sorted(row[key])
    return {"samples":len(samples),"source_movement_states":len(movement),"presented_waypoints":len(expected),
            "observed_climates":sorted(climates),"complete_presented_lifecycles":sum(row["complete_presented_path"] for row in rows),
            "lifecycles":rows,"scope":"Originally presented displacement and sprite path on captured flat roadworks, including reverse motion. Hidden effects and between-frame presentation remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--require-complete",action="store_true",help="Fail unless at least one complete originally presented path was observed")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log, source = args.log.read_bytes(), SOURCE.read_bytes()
    report = audit(log.decode(),source.decode())
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),original_effect_source_sha256=hashlib.sha256(source).hexdigest())
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "lifecycles"}))
    if args.require_complete and report["complete_presented_lifecycles"] == 0:
        raise SystemExit("No complete originally presented path was observed; partial evidence retained")


if __name__ == "__main__":
    main()

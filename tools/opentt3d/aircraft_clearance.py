#!/usr/bin/env python3
"""Audit captured aircraft/airport voxel intersections from a driver=5 native log.

Tests full-resolution authored volumes at actual emitted world transforms,
including fractional smoothed headings. Only simultaneously captured airport
bodies are covered. Hidden depot states, uncaptured scenery, draw-time LODs and
motion between presented frames are outside this audit.
The report is evidence of intersections, never final artwork/clearance approval.
"""

import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re


EPSILON = 0.0001  # Exclude contact and float-transform rounding, in world units.
NUMBER = r"[-+\d.eE]+"
AIRPORT = re.compile(rf"clearance airport frame (\d+) tile (\d+) graphics (\d+) state (\d+) origin ({NUMBER}),({NUMBER}),({NUMBER})")
AIRCRAFT = re.compile(rf"clearance aircraft frame (\d+) vehicle (\d+) engine (\d+) state (\d+) raw (-?\d+),(-?\d+),(-?\d+) direction (\d+) pose ({NUMBER}),({NUMBER}),({NUMBER}),({NUMBER})")


def box_overlap(centre, half, cosine, sine, low, high, epsilon=EPSILON):
    """Strict separating-axis test: yawed voxel run versus an axis-aligned run.

    Return the minimum overlap on five unit axes, or zero for separated/contact
    boxes. This is an overlap margin, not an intersection volume or escape vector.
    """
    other = tuple((a+b)*0.5 for a,b in zip(low,high))
    radius = tuple((b-a)*0.5 for a,b in zip(low,high))
    dx,dy,dz = (b-a for a,b in zip(centre,other))
    c,s = abs(cosine),abs(sine)
    margins = (
        half[2]+radius[2]-abs(dz),
        c*half[0]+s*half[1]+radius[0]-abs(dx),
        s*half[0]+c*half[1]+radius[1]-abs(dy),
        half[0]+c*radius[0]+s*radius[1]-abs(dx*cosine+dy*sine),
        half[1]+s*radius[0]+c*radius[1]-abs(-dx*sine+dy*cosine),
    )
    margin = min(margins)
    return margin if margin > epsilon else 0.0


def boxes(model, origin=(0,0,0)):
    for x,y,z,length,_material in model["runs"]:
        low = tuple(origin[d]+model["origin"][d]+p*model["cell_size"][d] for d,p in enumerate((x,y,z)))
        high = tuple(origin[d]+model["origin"][d]+p*model["cell_size"][d] for d,p in enumerate((x+length,y+1,z+1)))
        yield low,high


def buckets(low, high):
    for x in range(math.floor(low[0]/2),math.floor(high[0]/2)+1):
        for y in range(math.floor(low[1]/2),math.floor(high[1]/2)+1):
            yield x,y


def parse_trace(text):
    aircraft,airports = defaultdict(dict),defaultdict(dict)
    for line in text.splitlines():
        match = AIRCRAFT.search(line)
        if match:
            values = match.groups()
            frame,vehicle,engine,state,x,y,z,direction = map(int,values[:8])
            pose = tuple(map(float,values[8:]))
            if not all(math.isfinite(p) for p in pose):
                raise ValueError("Nonfinite aircraft transform")
            record = {"vehicle":vehicle,"engine":engine,"state":state,"raw":[x,y,z],"direction":direction,"pose":pose}
            if vehicle in aircraft[frame] and aircraft[frame][vehicle] != record:
                raise ValueError("One presented frame contains inconsistent aircraft transforms")
            aircraft[frame][vehicle] = record
        match = AIRPORT.search(line)
        if match:
            frame,tile,graphics,state = map(int,match.groups()[:4])
            origin = tuple(map(float,match.groups()[4:]))
            if not all(math.isfinite(p) for p in origin):
                raise ValueError("Nonfinite airport transform")
            record = (graphics,state,origin)
            if tile in airports[frame] and airports[frame][tile] != record:
                raise ValueError("One presented frame contains inconsistent airport owners")
            airports[frame][tile] = record
    if not aircraft or not airports:
        raise ValueError("Expected both emitted aircraft and airport driver=5 traces")
    return aircraft,airports


def audit(catalogue, text):
    aircraft,airports = parse_trace(text)

    @lru_cache(maxsize=None)
    def airport_index(graphics, state, origin):
        name = catalogue["bindings"]["airport_tiles"][str(graphics)][str(state)]
        runs = list(boxes(catalogue["models"][name],origin))
        index = defaultdict(list)
        for number,(low,high) in enumerate(runs):
            for key in buckets(low,high):
                index[key].append(number)
        bounds = (tuple(min(a[d] for a,b in runs) for d in range(3)),tuple(max(b[d] for a,b in runs) for d in range(3)))
        return name,runs,index,bounds

    @lru_cache(maxsize=4096)
    def overlaps(engine, state, pose, captured):
        name = catalogue["bindings"]["vehicles"][str(engine)][str(state)]
        x,y,z,heading = pose
        cosine,sine = math.cos(heading),math.sin(heading)
        placed = []
        for low,high in boxes(catalogue["models"][name]):
            a,b,c = ((p+q)*0.5 for p,q in zip(low,high))
            centre = (x+a*cosine-b*sine,y+a*sine+b*cosine,z+c)
            half = tuple((q-p)*0.5 for p,q in zip(low,high))
            extents = (abs(cosine)*half[0]+abs(sine)*half[1],abs(sine)*half[0]+abs(cosine)*half[1],half[2])
            bound_low = tuple(p-q for p,q in zip(centre,extents))
            bound_high = tuple(p+q for p,q in zip(centre,extents))
            placed.append((centre,half,bound_low,bound_high))
        plane_low = tuple(min(low[d] for centre,half,low,high in placed) for d in range(3))
        plane_high = tuple(max(high[d] for centre,half,low,high in placed) for d in range(3))
        hits = []
        for tile,graphics,body_state,origin in captured:
            body,runs,index,(body_low,body_high) = airport_index(graphics,body_state,origin)
            if any(min(plane_high[d],body_high[d])-max(plane_low[d],body_low[d]) <= EPSILON for d in range(3)):
                continue
            found = None
            for centre,half,low,high in placed:
                if any(min(high[d],body_high[d])-max(low[d],body_low[d]) <= EPSILON for d in range(3)):
                    continue
                candidates = {number for key in buckets(low,high) for number in index.get(key,())}
                for number in sorted(candidates):
                    a,b = runs[number]
                    if min(high[2],b[2])-max(low[2],a[2]) <= EPSILON:
                        continue
                    margin = box_overlap(centre,half,cosine,sine,a,b)
                    if margin:
                        found = {"tile":tile,"graphics":graphics,"state":body_state,"model":body,"overlap_margin":margin,
                                 "aircraft_run_centre":centre,"aircraft_run_half_size":half,"airport_run_low":a,"airport_run_high":b}
                        break
                if found:
                    break
            if found:
                hits.append(found)
        return hits

    samples = []
    missing_frames = []
    for frame,planes in sorted(aircraft.items()):
        captured = tuple((tile,*record) for tile,record in sorted(airports.get(frame,{}).items()))
        if not captured:
            missing_frames.append(frame)
            continue
        for plane in planes.values():
            hits = overlaps(plane["engine"],plane["state"],plane["pose"],captured)
            samples.append({"frame":frame,**plane,"intersections":hits})
    return {"captured_aircraft_samples":sum(len(p) for p in aircraft.values()),"evaluated_samples":len(samples),
            "aircraft_frames_without_captured_airports":missing_frames,"unique_pose_scene_queries":overlaps.cache_info().misses,
            "intersecting_samples":sum(bool(s["intersections"]) for s in samples),"samples":samples,"rounding_tolerance_world_units":EPSILON,
            "scope":"Full-resolution authored volumes at actual emitted transforms against simultaneously captured airport bodies. Hidden/uncaptured geometry, draw-time LODs and between-frame trajectories remain unverified.",
            "final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--catalogue",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    log,catalogue = args.log.read_bytes(),args.catalogue.read_bytes()
    report = audit(json.loads(catalogue),log.decode())
    report.update({"log":str(args.log),"log_sha256":hashlib.sha256(log).hexdigest(),
                   "catalogue":str(args.catalogue),"catalogue_sha256":hashlib.sha256(catalogue).hexdigest()})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "samples"}))


if __name__ == "__main__":
    main()

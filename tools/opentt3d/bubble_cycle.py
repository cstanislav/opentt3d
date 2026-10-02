#!/usr/bin/env python3
"""Read original bubble forming/floating/burst/absorption paths from captured logs.

The ordinary Toyland generator/catcher fixture supplies effects. This oracle only
reads source tables and observations: it never creates/ticks effects, changes the
map, selects a random path, consumes simulation RNG or splices partial lifetimes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from bulldozer_motion import NUMBER, TRACE


ROOT = Path(__file__).resolve().parents[2]
SOURCES = tuple(ROOT / name for name in ("src/effectvehicle.cpp", "src/industry_cmd.cpp", "src/openttd.cpp", "src/vehicle.cpp"))
MODE = re.compile(rf"bubble mode frame (\d+) vehicle (\d+) mode (\d+) ground ({NUMBER})")
TABLE_NAMES = ("float_sw", "float_ne", "float_se", "float_nw", "burst", "absorb")


def source_tables(effect, industry, game, vehicle):
    tables = []
    for name in TABLE_NAMES:
        body = effect.split(f"_bubble_{name}[] = {{",1)[1].split("};",1)[0]
        rows = []
        for movement,end in re.findall(r"MK\(([^)]+)\)|ME\(([^)]+)\)",body):
            rows.append(tuple(int(value.strip(),0) for value in movement.split(",")) if movement else (int(end),4,0,0))
        tables.append(rows)
    original_float = [(0,0,1,0),(1,0,1,1),(0,0,1,0),(1,0,1,2),(1,4,0,0)]
    for mode,(axis,step) in enumerate(((0,1),(0,-1),(1,1),(1,-1))):
        expected = [tuple((step if index == axis else 0) if index < 2 and row[0] else value for index,value in enumerate(row)) if row[1] != 4 else row for row in original_float]
        if tables[mode] != expected:
            raise ValueError("Original bubble floating table changed; review the oracle")
    absorb = [(0,0,1,i) for i in [0,1,0,2]*15+[0,1]]
    absorb += [(2,1,3,0),(1,1,3,1),(2,1,3,0),(1,1,3,2),(2,1,3,0),(1,1,3,1),(2,1,3,0),(1,0,1,2)]
    absorb += [(0,0,1,i) if i in (0,) else (1,0,1,i) for i in [0,1,0,2,0,1,0,2]]
    absorb += [(2,4,0,0)]+[(0,0,0,i) for i in range(10,15)]+[(0,4,0,0)]
    if tables[4] != [(0,0,1,i) for i in (2,7,8,9)]+[(0,4,0,0)] or tables[5] != absorb:
        raise ValueError("Original bubble burst or absorption table changed; review the oracle")
    order = effect.split("* const _bubble_movement[] = {",1)[1].split("};",1)[0]
    if re.findall(r"_bubble_(\w+)",order) != list(TABLE_NAMES):
        raise ValueError("Original bubble movement-table mode order changed; review the oracle")
    init = effect.split("static void BubbleInit(",1)[1].split("struct BubbleMovement",1)[0]
    tick = effect.split("static bool BubbleTick(",1)[1].split("struct EffectProcs",1)[0]
    needed = ("v->progress++;", "(v->progress & 3) != 0", "v->spritenum == 0", "sprite < SPR_BUBBLE_GENERATE_3",
              "v->animation_substate != 0", "v->spritenum = GB(Random(), 0, 2) + 1;", "v->spritenum = 6;",
              "anim_state = v->animation_state + 1;", "b->y == 4 && b->x == 0", "delete v;",
              "b->y == 4 && b->x == 1", "v->z_pos > 180 || Chance16I(1, 96, Random())", "v->spritenum = 5;",
              "b->y == 4 && b->x == 2", "anim_state++;", "GetIndustryGfx(tile) == GFX_BUBBLE_CATCHER",
              "v->animation_state = anim_state;", "v->x_pos += b->x;", "v->y_pos += b->y;", "v->z_pos += b->z;",
              "Set(SPR_BUBBLE_0 + b->image)", "v->UpdatePositionAndViewport();")
    spawn = industry.split("static void TileLoopIndustry_BubbleGenerator(",1)[1].split("static void TileLoop_Industry(",1)[0]
    spawn_table = [[int(n) for n in re.findall(r"-?\d+",row)] for row in re.findall(r"\{([^{}]+)\}",spawn.split("_bubble_spawn_location[3][4] = {",1)[1].split("};",1)[0])]
    above = effect.split("EffectVehicle *CreateEffectVehicleAbove(",1)[1].split("EffectVehicle *CreateEffectVehicleRel(",1)[0]
    normal_loop = game.split("AnimateAnimatedTiles();",1)[1].split("CallLandscapeTick();",1)[0]
    vehicle_loop = vehicle.split("void CallVehicleTicks()",1)[1].split("Backup<CompanyID> cur_company",1)[0]
    if (not all(part in init for part in ("Set(SPR_BUBBLE_GENERATE_0)", "v->spritenum = 0;", "v->progress = 0;")) or
            not all(part in tick for part in needed) or spawn_table != [[11,0,-4,-14],[-4,-10,-4,1],[49,59,60,65]] or
            "int dir = Random() & 3;" not in spawn or "EV_BUBBLE" not in spawn or "v->animation_substate = dir;" not in spawn or
            "GetSlopePixelZ(safe_x, safe_y) + z" not in above or "RunTileLoop();\n\t\tCallVehicleTicks();" not in normal_loop or
            "for (Vehicle *v : Vehicle::Iterate())" not in vehicle_loop or "if (!v->Tick())" not in vehicle_loop):
        raise ValueError("Original bubble timing, spawn, random branch or first-tick ordering changed; review the oracle")
    return tables, spawn_table


def successors(sample, progress, direction, tables):
    """Legal source-table edges, not running vehicle ticks or choosing RNG outcomes."""
    mode,state,sprite,x,y,z = sample
    if mode == 0:
        if progress < 12:
            return {(0,0,4751+progress//4,x,y,z)}
        choices = [(m,0) for m in range(1,5)] if direction else [(6,0)]
    else:
        next_state = state+1
        dx,dy,_,_ = tables[mode-1][next_state]
        if dy == 4:
            if dx == 0:
                return set()
            if dx == 1:
                choices = [(5,0)] if z > 180 else [(mode,0),(5,0)]
            else:
                choices = [(mode,next_state+1)]
        else:
            choices = [(mode,next_state)]
    result = set()
    for chosen,index in choices:
        dx,dy,dz,image = tables[chosen-1][index]
        result.add((chosen,index,4748+image,x+dx,y+dy,z+dz))
    return result


def audit(text, effect, industry, game, vehicle_source, expect_none=False):
    tables, spawn = source_tables(effect,industry,game,vehicle_source)
    modes = {}
    for match in MODE.finditer(text):
        frame,vehicle,mode = map(int,match.groups()[:3])
        value = (mode,float(match[4]))
        if (frame,vehicle) in modes and modes[frame,vehicle] != value:
            raise ValueError("One captured frame contains conflicting bubble modes")
        modes[frame,vehicle] = value
    current, rows, observations = {}, [], {}
    for match in TRACE.finditer(text):
        values = match.groups()
        frame,vehicle,kind,sprite,climate,state,direction,progress,x,y,z = map(int,values[:11])
        if kind != 9:
            continue
        if expect_none:
            raise ValueError("Expected absence contains original bubble effects")
        if (frame,vehicle) not in modes:
            raise ValueError("Captured bubble lacks its original movement-table mode")
        mode,ground = modes[frame,vehicle]
        if mode not in range(7) or direction not in range(4) or progress not in range(256) or climate not in range(4):
            raise ValueError("Bubble mode, original direction, progress or climate is invalid")
        origin = tuple(map(float,values[11:14]))
        if ground < 0 or origin != (x,y,z+ground) or float(values[14]) != 1 or int(values[15]) != 0:
            raise ValueError("Bubble lost original local altitude, doubled terrain datum, opacity or unclickable ownership")
        if mode == 0:
            valid = state == 0 and progress < 12 and sprite == 4751+progress//4
        else:
            valid = state < len(tables[mode-1]) and tables[mode-1][state][1] != 4
            valid = valid and sprite == 4748+tables[mode-1][state][3]
            if mode == 6:
                expected = 12+4*(state-(state>78))+progress%4
                valid = valid and direction == 0 and expected%256 == progress
            else:
                valid = valid and direction != 0 and state == (progress//4-3)%4
        if not valid or sprite == 4754:
            raise ValueError("Bubble lost its original forming/floating/rupture/absorption source state")
        sample = (mode,state,sprite,x,y,z)
        observation = (sample,climate,direction,progress,origin,ground)
        if (frame,vehicle) in observations:
            if observations[frame,vehicle] != observation:
                raise ValueError("One captured frame contains conflicting original bubble observations")
            continue
        observations[frame,vehicle] = observation
        row = current.get(vehicle)
        boundary = None
        if row is None:
            boundary = "first captured observation"
        elif frame < row["last_frame"]:
            raise ValueError("Bubble trace is not in captured-frame order")
        elif mode == 0 and (row["last_mode"] != 0 or progress < row["last_progress"]):
            boundary = "original pool ID reused at forming reset"
        elif frame > row["last_frame"]+1:
            boundary = "uncaptured frame gap; complete lifetime cannot be spliced"
        if boundary is not None:
            anchor = (x,y,z) if mode == 0 else None
            generator = None
            if anchor is not None:
                gx,gy = x-spawn[0][direction],y-spawn[1][direction]
                if gx%16 or gy%16 or z != ground+spawn[2][direction]:
                    raise ValueError("Forming bubble lost its original generator spawn offset or altitude")
                generator = (gx//16,gy//16)
            row = {"vehicle":vehicle,"climate":climate,"original_direction":direction,"anchor":anchor,"generator_tile":generator,
                   "first_frame":frame,"last_frame":frame,"first_mode":mode,"last_mode":mode,"first_progress":progress,"last_progress":progress,
                   "elapsed":progress if mode == 0 else 0,"phases":set(),"sprites":set(),"modes":set(),"phase_gaps":0,"current_phase_run":1,
                   "longest_phase_run":1,"last_state":state,"sample":sample,"boundary":boundary}
            current[vehicle] = row
            rows.append(row)
        else:
            if climate != row["climate"] or direction != row["original_direction"]:
                raise ValueError("Continuously captured bubble changed its original direction or climate")
            delta = (progress-row["last_progress"])%256
            candidates = {row["sample"]}
            for step in range(1,delta+1):
                p = (row["last_progress"]+step)%256
                if p%4 == 0:
                    candidates = {edge for previous in candidates for edge in successors(previous,p,direction,tables)}
            if sample not in candidates:
                raise ValueError("Captured bubble displacement or branch differs from its original movement tables")
            row["elapsed"] += delta
            if delta == 1:
                row["current_phase_run"] += 1
            elif delta > 1:
                row["phase_gaps"] += 1
                row["current_phase_run"] = 1
        row["last_frame"], row["last_progress"], row["last_mode"], row["last_state"], row["sample"] = frame,progress,mode,state,sample
        row["longest_phase_run"] = max(row["longest_phase_run"],row["current_phase_run"])
        row["phases"].add(row["elapsed"])
        row["sprites"].add(sprite)
        row["modes"].add(mode)
    if set(modes) != set(observations):
        raise ValueError("Bubble modes and actual voxel observations do not reconcile")
    if not observations and not expect_none:
        raise ValueError("No original voxel bubble trace records were found")
    for row in rows:
        terminal = (row["last_mode"] == 5 and row["last_state"] == 3) or (row["last_mode"] == 6 and row["last_state"] == 83)
        row["outcome"] = "absorbed" if row["last_mode"] == 6 else "burst" if row["last_mode"] == 5 else "unfinished"
        row["complete_presented_lifetime"] = (row["first_mode"] == 0 and row["first_progress"] == 1 and terminal and
                                              row["last_progress"]%4 == 3 and row["phases"] == set(range(1,row["elapsed"]+1)) and
                                              row["longest_phase_run"] == row["elapsed"])
        for key in ("phases","sprites","modes"):
            row[key] = sorted(row[key])
        del row["sample"], row["current_phase_run"]
    complete = [row for row in rows if row["complete_presented_lifetime"]]
    return {"samples":len(observations),"movement_tables":len(tables),"absorption_movement_entries":len(tables[5]),
            "unpresented_source_sprite":4754,"first_presented_progress":1,"complete_presented_lifetimes":len(complete),
            "complete_burst_lifetimes":sum(row["outcome"] == "burst" for row in complete),
            "complete_absorbed_lifetimes":sum(row["outcome"] == "absorbed" for row in complete),
            "observed_source_sprites":sorted({sprite for row in rows for sprite in row["sprites"]}),"lifetimes":rows,"expected_absence":expect_none,
            "scope":"Original captured Toyland bubble paths: source-table offsets, four-tick forming/movement/rupture/absorption selection, eight-bit progress wraps, fixed original direction, current doubled terrain datum and unclickable ownership. Fresh lifetimes require every phase from original first-tick progress1 through the final terminal hold phase. No RNG is drawn or reproduced; observed floating choices are checked against legal original branches. Each capture gap or reused pool ID is a new boundary. Spawn coordinates/altitude agree with the original generator table, but actual hidden/occluded industry ownership, random frequency and between-frame presentation remain separate acceptance work.","final_visual_approvals":0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    gate = parser.add_mutually_exclusive_group()
    gate.add_argument("--require-complete",action="store_true")
    gate.add_argument("--expect-none",action="store_true")
    parser.add_argument("--require-outcomes",nargs="+",choices=("burst","absorbed"))
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new report path to preserve earlier evidence")
    if args.require_outcomes and not args.require_complete:
        parser.error("--require-outcomes requires --require-complete")
    log, sources = args.log.read_bytes(), [path.read_bytes() for path in SOURCES]
    report = audit(log.decode(),*(source.decode() for source in sources),args.expect_none)
    report.update(log=str(args.log),log_sha256=hashlib.sha256(log).hexdigest(),
                  original_source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(source).hexdigest() for path,source in zip(SOURCES,sources)})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "lifetimes"}))
    if args.require_complete and (not report["complete_presented_lifetimes"] or
                                 any(not report[f"complete_{outcome}_lifetimes"] for outcome in args.require_outcomes or ())):
        raise SystemExit("Required complete original bubble lifetimes were not observed; partial evidence retained")


if __name__ == "__main__":
    main()

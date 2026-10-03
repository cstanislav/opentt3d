#!/usr/bin/env python3
"""Inventory vanilla definitions and track authored/reviewed coverage separately."""

import argparse
import json
from pathlib import Path
import re
from compile_vehicles import compile_catalogue
from compile_voxels import compile_catalogue as compile_voxel_catalogue
from original_objects import catalogue as original_object_catalogue

ROOT=Path(__file__).resolve().parents[2]


def placement(model):
    """Report authored world bounds/contact, without inferring a footprint from art."""
    size, origin, cell = model["size"], model["origin"], model["cell_size"]
    low, high = list(size), [0,0,0]
    contact = set()
    for x,y,z,length,material in model["runs"]:
        low = [min(low[0],x),min(low[1],y),min(low[2],z)]
        high = [max(high[0],x+length),max(high[1],y+1),max(high[2],z+1)]
        if origin[2]+z*cell[2] <= 0 <= origin[2]+(z+1)*cell[2]:
            contact.update((x+i,y) for i in range(length))
    bounds = [[origin[i]+point[i]*cell[i] for i in range(3)] for point in (low,high)]
    contact_bounds = None
    if contact:
        contact_bounds = [[origin[i]+min(point[i] for point in contact)*cell[i] for i in (0,1)],
                          [origin[i]+(max(point[i] for point in contact)+1)*cell[i] for i in (0,1)]]
    return {"world_bounds": bounds, "ground_contact_bounds": contact_bounds,
            "ground_contact_area": len(contact)*cell[0]*cell[1], "footprint_reviewed": False}


def inventory(voxels=None):
    if voxels is None:
        voxels = compile_voxel_catalogue(json.loads((ROOT / "assets/3d/voxels.json").read_text()))
    def voxel_states(category, identifier):
        return sorted(map(int, voxels["bindings"].get(category, {}).get(str(identifier), {})))
    engines=(ROOT/"src/table/engines.h").read_text().split("_orig_engine_info[] = {",1)[1].split("\n};",1)[0]
    vehicles=[]
    kinds={"MT":"train","MM":"train","MW":"wagon","MR":"road_vehicle","MS":"ship","MA":"aircraft"}
    for line in engines.splitlines():
        match=re.search(r"\b(M[TMWRSA])\(.*//\s*(\d+)\s+(.+)",line)
        if match:
            vehicles.append({"id":int(match[2]),"kind":kinds[match[1]],"name":match[3].strip(),
                             "states":["directions","company_livery","cargo","animation","crashed"],"reviewed":False})
    vehicle_models = compile_catalogue(json.loads((ROOT / "assets/3d/vehicles.json").read_text()))["models"]
    vehicle_families = {}
    for vehicle in vehicles:
        model = vehicle_models.get(str(vehicle["id"]))
        vehicle["authored_profile"] = model is not None
        vehicle["assembly"] = model["assembly"] if model else None
        vehicle["reviewed"] = model is not None and model["review_status"] == "approved"
        vehicle["voxel_states"] = voxel_states("vehicles", vehicle["id"])
        vehicle["voxel_climate_states"] = {}
        if model:
            for climate in model["climates"]:
                base = {"T":0,"A":2,"S":4,"Y":6}[climate]
                vehicle["voxel_climate_states"][climate] = [base+cargo if base+cargo in vehicle["voxel_states"] else cargo if cargo in vehicle["voxel_states"] else None for cargo in range(2)]
            key = (model["kind"],tuple(model["climates"]),tuple(model["sprites"]),tuple(model["loaded_sprites"]))
            family = vehicle_families.setdefault(key,{"kind":model["kind"],"climates":model["climates"],
                "sprites":model["sprites"],"loaded_sprites":model["loaded_sprites"],"engines":[],
                "voxel_engines":[],"pass1_verified":False})
            family["engines"].append(vehicle["id"])
            if vehicle["voxel_states"]:
                family["voxel_engines"].append(vehicle["id"])
    drawing=(ROOT/"src/table/town_land.h").read_text().split("_original_house_specs[] = {",1)[1]
    names=re.findall(r"MS\(.*?(STR_TOWN_BUILDING_NAME_[A-Z0-9_]+).*?\), // ([0-9A-Fa-f]{2})",drawing,re.S)
    houses=[{"id":int(id_,16),"name":name,"variants":4,"construction_stages":4,"reviewed":False} for name,id_ in names]
    models=json.loads((ROOT/"assets/3d/houses.json").read_text())
    authored={int(k) for k in models["models"]}|{int(k) for k in models["aliases"]}
    for house in houses:
        house["authored_profile"]=house["id"] in authored
        house["voxel_states"] = voxel_states("houses", house["id"])
        house["voxel_ground_states"] = voxel_states("house_ground", house["id"])
        house["voxel_construction_stages"] = sorted({state % 4 for state in house["voxel_states"]})
        house["explicit_voxel_variant_stages"] = {str(variant): sorted(state % 4 for state in house["voxel_states"] if state // 4 == variant) for variant in range(4)}
        house["variant_fallback"] = "Variant 0 only when the original resolved building sprite is identical; checked by runtime variant verification"
    tree_source = (ROOT / "src/table/tree_land.h").read_text().split("_tree_layout_sprite", 1)[1]
    tree_bindings = {}
    for sprite, palette in re.findall(r"\{\s*(0x[0-9a-fA-F]+)\s*,\s*([^{}]+?)\s*\}", tree_source):
        tree_bindings.setdefault(int(sprite, 16), set()).add(palette.strip())
    tree_models = json.loads((ROOT / "assets/3d/trees.json").read_text())
    authored_trees = {int(k) for k in tree_models["models"]} | {int(k) for k in tree_models["aliases"]}
    trees = [{"base_sprite": base, "palettes": sorted(palettes),
              "states": ["growing_1", "growing_2", "growing_3", "grown", "dying_1", "dying_2", "dead"],
              "authored_profile": base in authored_trees, "reviewed": False}
              for base, palettes in sorted(tree_bindings.items())]
    for tree in trees:
        tree["voxel_states"] = voxel_states("trees", tree["base_sprite"])
    industry_source = (ROOT / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data", 1)[1].split("};", 1)[0]
    industry_rows = re.findall(r"\bM\(\s*([^\n]+)\)", industry_source)
    if len(industry_rows) % 4:
        raise ValueError("Industry tile-state table is not grouped into four stages")
    industries = [{"graphics": index, "construction_stages": 4, "authored_profile": False, "reviewed": False}
                  for index in range(len(industry_rows) // 4)]
    industry_models = json.loads((ROOT / "assets/3d/industries.json").read_text())["models"]
    for industry in industries:
        model = industry_models.get(str(industry["graphics"]))
        industry["authored_profile"] = model is not None
        industry["modelled_sprites"] = model.get("sprites", ["completed-table-sprite"]) if model else []
        body_states = voxel_states("industries", industry["graphics"])
        ground_states = voxel_states("industry_ground", industry["graphics"])
        if any(state >= 64 or state % 16 >= 4 for state in body_states + ground_states):
            raise ValueError("Industry climate states must be climate*16+construction stage0..3")
        industry["voxel_states"] = [state for state in body_states if state < 4]
        industry["voxel_ground_states"] = [state for state in ground_states if state < 4]
        for layer,states in (("body",body_states),("ground",ground_states)):
            industry[f"explicit_{layer}_climate_states"] = {
                climate:[state%16 for state in states if state//16 == index]
                for index,climate in enumerate(("temperate","arctic","tropic","toyland")) if index != 0}
        if industry["graphics"] == 143:
            industry["procedural_children"] = [
                {"name":name,"sprite":sprite,"voxel_states":voxel_states("infrastructure",sprite)}
                for name,sprite in (("clay",4719),("robot_duck",4720),("stamp",4718),("holder",4717))]
            industry["procedural_source_frames"] = 50
            industry["procedural_source_note"] = "Original ordered completed frames and255 absences; conveyor+X and press-Z motion. Construction has no children. All four source/binding checks are linked to142..146 bodies;4675 ground remains independent."
        elif industry["graphics"] == 162:
            industry["procedural_children"] = [
                {"name":name,"sprite":sprite,"voxel_states":voxel_states("infrastructure",sprite)}
                for name,sprite in (("bubble_plunger",4747),("spring_cylinder",4746))]
            industry["procedural_source_frames"] = 40
            industry["procedural_source_note"] = "Stage0 has no children; stages1/2 draw only4746; completed40-frame motion draws4747 then4746. Plunger travel is only-Z. Body sources160..162 and both children are linked;4675/4676 grounds remain independent. Floating-bubble effects are separate."
        elif industry["graphics"] == 165:
            industry["procedural_children"] = [
                {"name":name,"sprite":sprite,"voxel_states":voxel_states("infrastructure",sprite),"shared_parent":sprite==4766}
                for name,sprite in (("shovel",4767),("toffee_parent_redraw",4766))]
            industry["procedural_source_frames"] = 70
            industry["procedural_source_note"] = "Both children occur at every construction stage. Original4766 exactly redraws4764 and shares its physical body; never duplicate the solid. Completed70-frame cutter travel follows the inclined shaft;255 means zero shift, not absence. Body164..166 and both child sources are linked;Toyland3981 ground stays independent."
        elif industry["graphics"] == 174:
            industry["procedural_children"] = [
                {"name":f"{family}_{sprite-first}","sprite":sprite,"voxel_states":voxel_states("infrastructure",sprite)}
                for family,first,count in (("sieve",4775,5),("cloud",4784,6),("pile",4780,4)) for sprite in range(first,first+count)]
            industry["procedural_source_frames"] = 96
            industry["procedural_source_note"] = "Construction has no children. Completed96-frame motion preserves sieve/cloud/pile order and genuine middle/trailing absences. The sieve moves along the crossbar at constantZ; clouds and piles have independent registered poses. Body172..174 and all15 children are linked;171..174 Toyland3981 grass stays independent."
        if industry["graphics"] in (16,17) or 33 <= industry["graphics"] <= 38:
            complete = all(state+16 in body_states for state in industry["voxel_states"]) and all(state+16 in ground_states for state in industry["voxel_ground_states"])
            industry["voxel_climates"] = ["temperate"] + (["arctic"] if complete else [])
            industry["missing_voxel_climates"] = [] if complete else ["arctic"]
            industry["climate_source_note"] = "Arctic replaces both source layers; equal sprite numbers do not permit a temperate alias. Only explicit climate states select independently authored artwork; missing layers retain supplied artwork."
            if industry["graphics"] in (16,17):
                toyland = all(state+48 in body_states for state in range(4)) and all(state+48 in ground_states for state in range(4))
                industry["voxel_climates"] += ["toyland"] if toyland else []
                industry["missing_voxel_climates"] += [] if toyland else ["toyland"]
                industry["climate_source_note"] += " Toyland2072..2077 exactly match the cotton129/130 source pixels, palette, dimensions, origins and offsets; explicit aliases preserve separate body/ground ownership. Original industry availability remains authoritative."
        if industry["graphics"] in (129,130):
            industry["voxel_climates"] = ["toyland"]
            industry["climate_source_note"] = "Cotton-candy crowns, bare sticks and checker soil replace forest2072..2077 in Toyland; other climates retain independently supplied artwork."
        restricted_grounds = []
        for stage in industry["voxel_ground_states"]:
            # Colour modifiers belong to sprite rendering, not the source ID.
            sprite = int(industry_rows[industry["graphics"]*4+stage].split(",")[0].split("|",1)[0].strip(),0)
            if industry["graphics"] in (129,130):
                restricted_grounds.append({"stage":stage,"sprite":sprite,"voxel_climates":["toyland"],"other_climates":"retain supplied independently painted forest ground"})
            elif (131 <= industry["graphics"] <= 134 or 138 <= industry["graphics"] <= 141) and sprite == 2022:
                restricted_grounds.append({"stage":stage,"sprite":sprite,"voxel_climates":["toyland"],"other_climates":"retain supplied independently painted bare soil; unchanged factory bodies remain bound"})
            elif industry["graphics"] in (135,136,137) and sprite == 2077:
                restricted_grounds.append({"stage":stage,"sprite":sprite,"voxel_climates":["toyland"],"other_climates":"retain supplied independently painted forest ground; unchanged battery/cola bodies remain bound"})
            elif 164 <= industry["graphics"] <= 174 and sprite == 3981:
                restricted_grounds.append({"stage":stage,"sprite":sprite,"voxel_climates":["toyland"],"other_climates":"retain supplied independently painted grass; unchanged toffee/sugar bodies and children remain bound"})
            elif sprite in (3924,2173):
                explicit = [climate for index,climate in enumerate(("temperate","arctic","tropic","toyland"))
                            if index and index*16+stage in ground_states]
                restricted_grounds.append({"stage":stage,"sprite":sprite,"voxel_climates":["temperate",*explicit],
                                           "missing_voxel_climates":[climate for climate in ("arctic","tropic","toyland") if climate not in explicit],
                                           "source_note":"Explicit climate states retain independently painted grounds or audited exact source aliases; body ownership stays independent"})
            elif sprite in (2022,2077,2257,2260,2261,4061):
                explicit = 48+stage in ground_states
                restricted_grounds.append({"stage":stage,"sprite":sprite,"missing_voxel_climates":[] if explicit else ["toyland"],
                                           "toyland_source":"explicit independently authored or exact source-alias ground" if explicit else "retain supplied Toyland source ground"})
        if restricted_grounds:
            industry["ground_climate_restrictions"] = restricted_grounds
        restricted_bodies = []
        for stage in industry["voxel_states"]:
            sprite = int(industry_rows[industry["graphics"]*4+stage].split(",")[2].split("|",1)[0].strip(),0)
            if industry["graphics"] in (26,27,28) or (industry["graphics"] == 67 and sprite == 2206):
                explicit = 48+stage in body_states
                restricted_bodies.append({"stage":stage,"sprite":sprite,"missing_voxel_climates":[] if explicit else ["toyland"],
                                          "toyland_source":"explicit source-audited animated-palette alias" if explicit else "retain supplied Toyland source body"})
        if restricted_bodies:
            industry["body_climate_restrictions"] = restricted_bodies
    airport_source = (ROOT / "src/table/airporttile_ids.h").read_text().split("enum AirportTiles", 1)[1].split("};", 1)[0]
    airports = [{"id": i, "name": name, "voxel_states": [state for state in voxel_states("airport_tiles", i) if state < 16],
                 "explicit_body_climate_states": {climate:[state%16 for state in voxel_states("airport_tiles",i) if state//16 == index]
                     for index,climate in enumerate(("temperate","arctic","tropic","toyland"))},
                 "voxel_ground_states": [state for state in voxel_states("airport_ground", i) if state < 16],
                 "explicit_ground_climate_states": {climate:[state%16 for state in voxel_states("airport_ground",i) if state//16 == index]
                     for index,climate in enumerate(("temperate","arctic","tropic","toyland"))}, "reviewed": False}
                for i, name in enumerate(re.findall(r"\b(APT_\w+)\s*,", airport_source))]
    airport_specs = (ROOT / "src/table/airporttiles.h").read_text().split("_origin_airporttile_specs[] = {", 1)[1].split("};", 1)[0]
    frame_counts = [1 if kind == "AT_NOANIM" else int(last)+1 for kind,last in
                    re.findall(r"\b(AT_NOANIM|AT\(\s*(\d+)\s*,\s*\d+\s*\))", airport_specs)]
    airport_layouts = (ROOT / "src/table/station_land.h").read_text().split("_station_display_datas_airport[] = {",1)[1].split("};",1)[0]
    body_owners = [kind != "LINE_NOTHING" for kind in re.findall(r"\bTILE_SPRITE_(LINE_NOTHING|LINE|NULL)\(",airport_layouts)]
    if len(frame_counts) != len(airports) or len(body_owners) != len(airports):
        raise ValueError("Airport definitions and animation tables disagree")
    for airport,frames,body in zip(airports,frame_counts,body_owners):
        airport["source_frames"] = frames
        airport["source_has_body"] = body
        airport["bound_voxel_states"] = airport["voxel_states"] if body else airport["voxel_ground_states"]
        airport["missing_voxel_states"] = sorted(set(range(frames))-set(airport["bound_voxel_states"]))
        airport["missing_voxel_ground_states"] = sorted(set(range(frames))-set(airport["voxel_ground_states"]))
        airport["all_source_frames_bound"] = not airport["missing_voxel_states"]
        if airport["id"] in (*range(19,29),43,47):
            missing = sorted(set(range(frames))-set(airport["explicit_body_climate_states"]["toyland"]))
            airport["missing_voxel_climates"] = ["toyland"] if missing else []
            airport["missing_toyland_body_frames"] = missing
            airport["climate_source_note"] = "Toyland replaces original body paint; explicit climate frames retain source-confirmed geometry with independent spatial paint. Missing frames retain the supplied complete tile."
    depots = [{"kind": kind, "name": name, "voxel_states": voxel_states("depots", kind),
               "voxel_directions": sorted({state%4 for state in voxel_states("depots", kind)}),
               "climate_variant_states": {label: [state%4 for state in voxel_states("depots", kind) if state//4 == variant]
                                          for variant, label in enumerate(("temperate_arctic_tropic", "toyland"))},
               "voxel_floor_states": voxel_states("depot_floors", kind), "reviewed": False}
              for kind, name in enumerate(("rail", "electric_rail", "monorail", "maglev", "road", "tram"))]
    ship_depots = [{"axis":axis,"voxel_parts":voxel_states("ship_depots",axis),"reviewed":False,
                    "ground":"Independent original water-class surface"} for axis in range(2)]
    docks = [{"graphics":graphics,"voxel_states":voxel_states("docks",graphics),"reviewed":False,
              "climate_states":{"0":"temperate_arctic_tropic","1":"toyland"},
              "ground":"Independent original sloped shore or water-class surface"} for graphics in range(6)]
    sprite_ids = {name:int(value) for name,value in re.findall(r"static const SpriteID (SPR_\w+) = (\d+);",(ROOT / "src/table/sprites.h").read_text())}
    effect_families = (
        ("chimney","SPR_CHIMNEY_SMOKE_0","SPR_CHIMNEY_SMOKE_7","ChimneySmokeInit"),
        ("steam","SPR_STEAM_SMOKE_0","SPR_STEAM_SMOKE_4","SteamSmokeInit"),
        ("diesel","SPR_DIESEL_SMOKE_0","SPR_DIESEL_SMOKE_5","DieselSmokeInit"),
        ("electric-spark","SPR_ELECTRIC_SPARK_0","SPR_ELECTRIC_SPARK_5","ElectricSparkInit"),
        ("smoke","SPR_SMOKE_0","SPR_SMOKE_4","SmokeInit"),
        ("explosion-large","SPR_EXPLOSION_LARGE_0","SPR_EXPLOSION_LARGE_F","ExplosionLargeInit"),
        ("breakdown","SPR_BREAKDOWN_SMOKE_0","SPR_BREAKDOWN_SMOKE_3","BreakdownSmokeInit"),
        ("explosion-small","SPR_EXPLOSION_SMALL_0","SPR_EXPLOSION_SMALL_B","ExplosionSmallInit"),
        ("bulldozer","SPR_BULLDOZER_NE","SPR_BULLDOZER_NW","BulldozerInit"),
        ("bubble","SPR_BUBBLE_0","SPR_BUBBLE_ABSORB_4","BubbleInit"),
    )
    effect_frames = [{"family":family,"frame":sprite-sprite_ids[first],"sprite":sprite,
                      "presentable":sprite != sprite_ids["SPR_BUBBLE_GENERATE_3"],
                      "voxel_states":voxel_states("effects",sprite),"reviewed":False}
                     for family,first,last,init in effect_families for sprite in range(sprite_ids[first],sprite_ids[last]+1)]
    effect_init_families = {init:family for family,first,last,init in effect_families}
    effect_types = [{"type":name,"init":init,"tick":tick,"transparency":transparency,"source_family":effect_init_families[init]}
                    for init,tick,transparency,name in re.findall(r"\{\s*(\w+Init),\s*(\w+Tick),\s*(TO_\w+)\s*\},\s*//\s*(EV_\w+)",(ROOT / "src/effectvehicle.cpp").read_text())]
    # Procedural C++ volumes are tracked separately from the JSON model count.
    # This is an implementation catalogue, not automatic source/fidelity approval.
    fences = [{"id": identifier, "name": name, "runtime_layouts": 16 if identifier == 6 else 4,
               "source_variants": 8 if identifier == 6 else 6, "lods": 3,
               "implementation": "src/renderer3d/terrain_geometry.hpp::MakeFenceMesh",
               "review_status": "work-in-progress"}
              for identifier, name in enumerate(("hedge", "hedge_gate", "white_timber", "cream_blossom", "coral_blossom", "stone_wall", "railway_chain_link"))]
    running_rails = [{"id": identifier, "name": name, "routes": 6, "lods": 3,
                     "implementation": "src/renderer3d/rail_geometry.hpp::MakeRailAssembly",
                     "scope": "running assembly; other railway infrastructure remains",
                     "review_status": "work-in-progress"}
                    for identifier, name in enumerate(("conventional", "electric", "monorail", "maglev"))]
    foundation_source = (ROOT / "src/slope_type.h").read_text().split("enum Foundation", 1)[1].split("};", 1)[0]
    foundation_names = re.findall(r"^\s*(FOUNDATION_[A-Z_]+)\s*,", foundation_source, re.M)
    foundations = [{"id": identifier, "name": name.removeprefix("FOUNDATION_").lower(), "lods": 3,
                    "implementation": "src/renderer3d/terrain_geometry.hpp::MakeFoundationMesh",
                    "scope": "retaining support; ground surfaces and other structures are separate",
                    "review_status": "work-in-progress"}
                   for identifier,name in enumerate(foundation_names) if identifier != 0]
    return {"upstream":json.loads((ROOT/"opentt3d/upstream.json").read_text()),
              "vehicles":vehicles,"vehicle_source_families":list(vehicle_families.values()),
              "houses":houses,"trees":trees,"industry_tiles":industries,
               "airport_tiles": airports, "depots": depots, "ship_depots": ship_depots, "docks": docks,
               "effect_types":effect_types,"effect_source_frames":effect_frames,
                "effect_source_note":"Source export alone is not voxel coverage. Bubble generation threshold4754 is immediately replaced before viewport presentation; retain its original source without inventing a runtime frame. Movement, lifetimes, transparency and unclickable ownership remain original.",
                "original_objects":original_object_catalogue(),
              "voxel_models": {name: {"occupied_cells": model["occupied"], "cell_size": model["cell_size"], "review_status": model["review_status"], **placement(model)}
                              for name, model in voxels["models"].items()},
             "voxel_bindings": voxels["bindings"],
             "procedural_voxels": {"fences": fences, "running_rails": running_rails, "foundations": foundations},
            "remaining_catalogues":["infrastructure","effects","base-set parameter variants"],
            "release_ready":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--catalogue",type=Path,help="Use an already compiled voxel catalogue from the exact reviewed build")
    parser.add_argument("--require-complete",action="store_true")
    parser.add_argument("--footprints",action="store_true",help="List static ground-contact bounds; outside-tile contacts require explicit source/layout review")
    parser.add_argument("--vehicle-families",choices=("train","road","ship","aircraft"),help="List exact sprite/cargo/climate families for breadth-first authoring; not automatic geometry approval")
    args=parser.parse_args()
    data=inventory(json.loads(args.catalogue.read_text()) if args.catalogue else None)
    print(f"Vehicles: {len(data['vehicles'])}; houses: {len(data['houses'])}; authored house profiles: {sum(h['authored_profile'] for h in data['houses'])}")
    print(f"Authored vehicle bindings: {sum(v['authored_profile'] for v in data['vehicles'])}; visually reviewed vehicles: {sum(v['reviewed'] for v in data['vehicles'])}")
    print(f"Tree sprite families: {len(data['trees'])}; authored tree profiles: {sum(t['authored_profile'] for t in data['trees'])}; visually reviewed: {sum(t['reviewed'] for t in data['trees'])}")
    print(f"Industry tile definitions: {len(data['industry_tiles'])}; authored: {sum(i['authored_profile'] for i in data['industry_tiles'])}; voxel bodies: {sum(bool(i['voxel_states']) for i in data['industry_tiles'])}; voxel grounds: {sum(bool(i['voxel_ground_states']) for i in data['industry_tiles'])}")
    missing_arctic = [i["graphics"] for i in data["industry_tiles"] if "arctic" in i.get("missing_voxel_climates",[])]
    print(f"Industry definitions still missing complete explicit Arctic body/ground artwork: {missing_arctic}")
    climate_grounds = [r for industry in data["industry_tiles"] for r in industry.get("ground_climate_restrictions",[]) if r["sprite"] in (3924,2173)]
    print(f"Industry grounds3924/2173: {len(climate_grounds)} original layers; missing explicit non-temperate layer states: {sum(len(r['missing_voxel_climates']) for r in climate_grounds)}; independent body ownership retained")
    print(f"Airport tile definitions: {len(data['airport_tiles'])}; voxel-bound body or ground-only: {sum(bool(a['bound_voxel_states']) for a in data['airport_tiles'])}; body owners: {sum(bool(a['voxel_states']) for a in data['airport_tiles'])}")
    print(f"Independently bound voxel airport grounds: {sum(bool(a['voxel_ground_states']) for a in data['airport_tiles'])}")
    print(f"Distinct Toyland airport body frames: {sum(len(a['explicit_body_climate_states']['toyland']) for a in data['airport_tiles'])} explicit bindings; {sum(len(a.get('missing_toyland_body_frames',[])) for a in data['airport_tiles'])} missing bindings")
    print(f"Depot families: {len(data['depots'])}; voxel directions: {sum(len(d['voxel_directions']) for d in data['depots'])}; full four-direction families: {sum(len(d['voxel_directions']) == 4 for d in data['depots'])}")
    print(f"Ship-depot axes: {sum(d['voxel_parts'] == [0,1] for d in data['ship_depots'])} / 2; both original tile parts required; water remains independent")
    print(f"Dock sections: {sum(d['voxel_states'] == [0,1] for d in data['docks'])} / 6; ordinary/Toyland states required; shore/water remains independent")
    animated = [airport for airport in data["airport_tiles"] if airport["source_frames"] > 1]
    print(f"Animated airport definitions: {len(animated)}; all source frames voxel-bound: {sum(a['all_source_frames_bound'] for a in animated)}; visual approval remains separate")
    print(f"Voxel volumes: {len(data['voxel_models'])}; house definitions with voxel body or ground: {sum(bool(h['voxel_states'] or h['voxel_ground_states']) for h in data['houses'])}; approved voxel models: {sum(m['review_status'] == 'approved' for m in data['voxel_models'].values())}")
    print(f"Independently bound voxel house bodies: {sum(bool(h['voxel_states']) for h in data['houses'])}; ground-only source definitions remain separate")
    print(f"Independently bound voxel house grounds: {sum(bool(h['voxel_ground_states']) for h in data['houses'])}")
    print(f"Voxel-bound vehicles: {sum(bool(v['voxel_states']) for v in data['vehicles'])} / {len(data['vehicles'])}; tree families: {sum(bool(t['voxel_states']) for t in data['trees'])} / {len(data['trees'])}")
    effects = data["effect_source_frames"]
    print(f"Original effect types: {len(data['effect_types'])}; source sprites: {len(effects)}; presentable: {sum(e['presentable'] for e in effects)}; voxel-bound presentable sprites: {sum(e['presentable'] and bool(e['voxel_states']) for e in effects)}; source export is not artwork approval")
    objects = data["original_objects"]
    print(f"Original objects: {len(objects['types'])} types, {len(objects['tiles'])} tile layouts including five four-tile HQ sizes; {objects['headquarters_ground_only_slots']} HQ slots have no separate body; source inventory does not assert voxel coverage")
    if args.vehicle_families:
        for family in data["vehicle_source_families"]:
            if family["kind"] == args.vehicle_families:
                print(json.dumps(family))
    print(f"Procedural voxel families: {len(data['procedural_voxels']['fences'])} fences, {len(data['procedural_voxels']['running_rails'])} running-rail systems, {len(data['procedural_voxels']['foundations'])} foundation forms; all work-in-progress")
    if args.footprints:
        for category in ("houses", "house_ground", "industries", "industry_ground", "airport_tiles", "airport_ground", "depots", "depot_floors", "ship_depots", "docks"):
            names = sorted({name for states in data["voxel_bindings"].get(category, {}).values() for name in states.values()})
            for name in names:
                model = data["voxel_models"][name]
                contact = model["ground_contact_bounds"]
                outside = contact is not None and (min(contact[0]) < 0 or max(contact[1]) > 16)
                print(json.dumps({"category": category, "model": name, "ground_contact_bounds": contact,
                                  "world_bounds": model["world_bounds"], "outside_single_tile": outside,
                                  "reviewed": False}))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(data,indent=2)+"\n")
    if args.require_complete and not data["release_ready"]:
        raise SystemExit("Release requirements incomplete: artwork/state coverage and visual review remain")


if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Validate actual river feature/offset/absence observations, never infer them from IDs."""
import copy
import re

from live_water import integers
from original_water import ROOT, catalogue as water_catalogue, constant_reader


def source_slopes(source=None):
    """Read original corner bits, not the order of screen-facing slope names."""
    source = (ROOT / "src/slope_type.h").read_text() if source is None else source
    corners = {name:int(value,0) for name,value in re.findall(
        r"^\s*(SLOPE_(?:FLAT|N|E|S|W))\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*,",source,re.M)}
    if set(corners) != {"SLOPE_FLAT","SLOPE_N","SLOPE_E","SLOPE_S","SLOPE_W"}:
        raise ValueError("Original river slope corner values need explicit source review")
    values = {"SLOPE_FLAT":corners["SLOPE_FLAT"]}
    for name in ("SLOPE_NE","SLOPE_SE","SLOPE_SW","SLOPE_NW"):
        match = re.search(rf"^\s*{name}\s*=\s*(SLOPE_[NESW])\s*\|\s*(SLOPE_[NESW])\s*,",source,re.M)
        if not match or {match[1],match[2]} != {"SLOPE_"+corner for corner in name.removeprefix("SLOPE_")}:
            raise ValueError("Original river slope corner composition changed")
        values[name] = corners[match[1]] | corners[match[2]]
    if len(set(values.values())) != 5 or any(type(value) is not int or not 0 <= value < 16 for value in values.values()):
        raise ValueError("Original river slopes must remain five distinct ordinary source slopes")
    return values


def selected_river_selectors(observations, fixture, climate, originals=None):
    """Match already-selected callback values to original flat/slope/group rules.

    This classifies a source's feature, not its internal water/terrain/raised
    ownership. A CF_RIVER_SLOPE source can contain rocks or island relief. Empty
    observations never prove absence or completion; absent CF_RIVER_EDGE requires
    an explicit original zero-base record. Deduplication is not a draw-order trace.
    """
    originals = water_catalogue() if originals is None else originals
    if type(climate) is not int or climate not in range(4) or not isinstance(observations,list):
        raise ValueError("Use a real climate and original river selector observations")
    if not isinstance(fixture,dict):
        raise ValueError("Require the original saved map dimensions")
    width,height = fixture.get("map_width"),fixture.get("map_height")
    if any(type(value) is not int or value < 16 for value in (width,height)):
        raise ValueError("Original saved map dimensions are missing")
    slopes = source_slopes()
    slope_names = {value:name for name,value in slopes.items()}
    groups = {slopes[row["slope"]]:row for row in originals["runtime_selection"]["river_custom_groups"]}
    integer = constant_reader((ROOT / "src/table/sprites.h").read_text())
    defaults = {slopes["SLOPE_FLAT"]:integer("SPR_FLAT_WATER_TILE")}
    defaults.update({slopes[row["slope"]]:integer(row["sprite_name"]) for row in originals["runtime_selection"]["river_default_slopes"]})
    ground,edges,absences,states = {},{},{},{}
    for row in observations:
        if not isinstance(row,dict) or row.get("feature") not in ("CF_RIVER_SLOPE","CF_RIVER_EDGE"):
            raise ValueError("Original river selector feature is missing or unknown")
        if (type(row.get("climate")) is not int or row["climate"] != climate or type(row.get("water_class")) is not int or row["water_class"] != 2 or
                type(row.get("slope")) is not int or row["slope"] not in slope_names):
            raise ValueError("Original river climate/water class/slope differs")
        tile,height_z = row.get("tile"),row.get("source_height")
        if type(tile) is not int or not 0 <= tile < width*height or type(height_z) is not int or height_z < 0 or height_z % 8:
            raise ValueError("Original river tile/source height must remain integral")
        xy = integers(row,"tile_xy",2)
        if xy != [tile%width,tile//width] or integers(row,"draw_origin",3) != [xy[0]*16,xy[1]*16,height_z]:
            raise ValueError("Original river tile/source anchor differs")
        if any(type(row.get(key)) is not int or not 0 <= row[key] <= 0xFFFFFFFF for key in ("base_sprite","selected_sprite","requested_offset","resolved_offset")):
            raise ValueError("River sprite/callback offsets must remain exact unsigned integers")
        if (type(row.get("feature_flags")) is not int or not 0 <= row["feature_flags"] < 256 or
                type(row.get("offset_callback")) is not bool or type(row.get("absent")) is not bool or
                type(row.get("palette")) is not int or row["palette"] != 0 or not isinstance(row.get("base_set"),str) or not row["base_set"]):
            raise ValueError("Original river feature flags/palette/absence/provenance are missing")
        state = (row["slope"],height_z,row["base_set"])
        if tile in states and states[tile] != state:
            raise ValueError("Original river owners disagree about their tile state")
        states[tile] = state
        value = {key:copy.deepcopy(item) for key,item in row.items() if key not in ("texture_generation","source_image")}
        image_fields = ("source_offset","source_size","source_file","base_graphics","source_image","source_image_sha256")
        if row["absent"]:
            if (row["feature"] != "CF_RIVER_EDGE" or any(row[key] != 0 for key in ("base_sprite","selected_sprite","resolved_offset")) or
                    row["offset_callback"] or any(key in row for key in image_fields)):
                raise ValueError("Absent river edge needs an actual zero feature base, not an invented source")
            destination,key = absences,tile
        else:
            if row["selected_sprite"] <= 0 or type(row.get("base_graphics")) is not bool or not isinstance(row.get("source_file"),str) or not row["source_file"]:
                raise ValueError("Selected river source provenance is missing")
            integers(row,"source_offset",2)
            integers(row,"source_size",2,positive=True)
            digest = row.get("source_image_sha256")
            if not isinstance(digest,str) or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError("Retain SHA-256 of each complete selected river source")
            if row["feature"] == "CF_RIVER_SLOPE":
                expected = 0 if row["slope"] == slopes["SLOPE_FLAT"] else groups[row["slope"]]["ground_offset"] + (row["feature_flags"] & 1)
                if row["base_sprite"] == 0:
                    if row["offset_callback"] or row["requested_offset"] != 0 or row["resolved_offset"] != 0 or row["selected_sprite"] != defaults[row["slope"]]:
                        raise ValueError("Original default river ground selection differs")
                elif (not row["offset_callback"] or row["requested_offset"] != expected or
                      (row["slope"] == slopes["SLOPE_FLAT"] and not row["feature_flags"] & 1) or
                      row["selected_sprite"] != row["base_sprite"]+row["resolved_offset"]):
                    raise ValueError("Original custom river ground flag/input/output selection differs")
                destination,key = ground,tile
            else:
                if (row["base_sprite"] == 0 or row["selected_sprite"] != row["base_sprite"]+row["resolved_offset"] or
                        row["offset_callback"] != (row["base_sprite"] != defaults[slopes["SLOPE_FLAT"]]) or
                        (not row["offset_callback"] and row["requested_offset"] != row["resolved_offset"])):
                    raise ValueError("Original conditional river edge callback selection differs")
                destination,key = edges,(tile,row["requested_offset"])
        if key in destination and destination[key] != value:
            raise ValueError("Same river selector chooses conflicting source bytes/metadata")
        destination[key] = value
    for row in list(edges.values())+list(absences.values()):
        tile = row["tile"]
        if tile not in ground:
            raise ValueError("River edge needs its independently selected ground owner")
        offset = groups[row["slope"]]["edge_offset"] if ground[tile]["base_sprite"] != 0 else 0
        if (row["absent"] and row["requested_offset"] != offset) or (not row["absent"] and not offset <= row["requested_offset"] < offset+12):
            raise ValueError("Original river ground/edge source groups disagree")
        if not row["absent"] and tile in absences:
            raise ValueError("Same original river edge feature cannot be present and absent")
    return {"ground_sources":[row for key,row in sorted(ground.items())],"edge_sources":[row for key,row in sorted(edges.items())],
            "absent_edge_features":[row for key,row in sorted(absences.items())],"observed_tiles":len(ground),
            "observed_slopes":sorted({row["slope"] for row in ground.values()}),"slope_source_values":slopes,
            "observed_input_groups_checked":bool(ground),"callback_outputs_retained":bool(ground),
            "complete_river_family_verified":False,"raised_water_ownership_verified":False,
            "layer_order_or_animation_verified":False,"geometry_or_quality_approved":False,
            "scope":"Actual observed feature/input/output/source/absence values only, matched to original slope bits and callback groups. CF_RIVER_SLOPE ground can include raised relief as well as water; feature identity does not establish relief dimensions/owners or structural coverage. Empty or unobserved edges never imply absence. Flat/all-slope/climate/custom-family completeness, repeated draw order, phases and ships remain unverified."}

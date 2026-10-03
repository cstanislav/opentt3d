#!/usr/bin/env python3
"""Read original lock/water ownership and selectors; never infer 3D coverage from sprites."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PARTS = ("middle", "lower", "upper")
DIRECTIONS = ("ne", "se", "sw", "nw")
SOURCES = ("src/table/water_land.h", "src/table/sprites.h", "src/tile_type.h",
           "src/water_cmd.cpp", "src/water_map.h", "src/direction_type.h", "src/newgrf_canal.h")


def constant_reader(source):
    """Resolve only the integer/additive expressions needed by the source tables."""
    expressions = dict(re.findall(
        r"static\s+(?:const|constexpr)\s+(?:SpriteID|uint\d*_t|uint|int|size_t)\s+(\w+)\s*=\s*([^;]+);", source))
    visiting = set()
    resolved = {}

    def integer(expression):
        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) is int:
                return node.value
            if isinstance(node, ast.Name):
                return named(node.id)
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
                first, last = visit(node.left), visit(node.right)
                return first + last if isinstance(node.op, ast.Add) else first - last
            raise ValueError("Original water constant needs explicit integer source review")
        try:
            return visit(ast.parse(expression.strip(), mode="eval").body)
        except SyntaxError as error:
            raise ValueError("Invalid original water constant") from error

    def named(name):
        if name in resolved:
            return resolved[name]
        if name not in expressions or name in visiting:
            raise ValueError(f"Unknown/cyclic original water constant: {name}")
        visiting.add(name)
        value = integer(expressions[name])
        visiting.remove(name)
        resolved[name] = value
        return value

    return integer


def layers(table, constants):
    integer = constant_reader(constants + "\n" + table)
    sequences = {}
    for name, body in re.findall(r"static const DrawTileSeqStruct (_lock_display_\w+_seq)\[\] = \{(.*?)\};", table, re.S):
        body = re.sub(r"//[^\n]*", "", body)
        macros = re.findall(r"TILE_SEQ_LINE\(([^()]*)\)", body)
        remainder = re.sub(r"TILE_SEQ_LINE\([^()]*\)", "", body).strip()
        if len(macros) != 2 or remainder or name in sequences:
            raise ValueError("Original lock must retain separate ordered rear/front source owners")
        owners = []
        for face, macro in zip(("rear", "front"), macros):
            arguments = macro.split(",")
            if len(arguments) != 7:
                raise ValueError("Original lock source origin/sort extent changed")
            values = [integer(argument) for argument in arguments]
            owners.append({"face": face, "origin": values[:3], "sort_extent": values[3:6],
                           "sprite_offset": values[6], "palette": "PAL_NONE"})
        sequences[name] = owners
    match = re.search(r"static const DrawTileSpriteSpan _lock_display_data\[\]\[DIAGDIR_END\] = \{(.*?)\};", table, re.S)
    if not match or len(sequences) != 12:
        raise ValueError("Original lock table needs all three parts/four directions")
    body = re.sub(r"//[^\n]*", "", match[1])
    entries = re.findall(r"TILE_SPRITE_LINE\(\s*([^,()]+),\s*(_lock_display_\w+_seq)\s*\)", body)
    remainder = re.sub(r"TILE_SPRITE_LINE\([^()]*\)", "", body)
    if len(entries) != 12 or re.sub(r"[\s{},]", "", remainder):
        raise ValueError("Original lock table contains unknown/extra source owners")
    rows = []
    lock_base, water_base = integer("SPR_LOCK_BASE"), integer("SPR_CANALS_BASE")
    flat = integer("SPR_FLAT_WATER_TILE")
    for index, (ground, sequence) in enumerate(entries):
        part, direction = divmod(index, 4)
        if sequence != f"_lock_display_{PARTS[part]}_{DIRECTIONS[direction]}_seq":
            raise ValueError("Original lock part/direction ordering changed")
        ground = integer(ground)
        rows.append({"part": part, "part_name": PARTS[part], "direction": direction,
                     "direction_name": DIRECTIONS[direction].upper(), "footprint_tiles": [1, 1],
                     "ground": {"source_value": ground, "default_sprite": water_base + ground if ground < 5 else ground,
                                "is_flat_water": ground == flat, "palette": "PAL_NONE",
                                "ownership": "Independent animated water surface; not a lock wall or billboard volume."},
                     "body": copy.deepcopy(sequences[sequence]), "reviewed": False})
    offsets = {owner["sprite_offset"] for row in rows for owner in row["body"]}
    if offsets != set(range(24)) or any(owner["origin"][2] != 0 for row in rows for owner in row["body"]):
        raise ValueError("Original lock source offsets/vertical registration changed")
    for row in rows:
        for owner in row["body"]:
            owner["default_sprite_variants"] = [lock_base + owner["sprite_offset"] + offset for offset in (0, 24)]
    return rows


def runtime_selection(drawing, enums, directions, feature_flags):
    if ([(name, int(value)) for name, value in re.findall(r"(Middle|Lower|Upper)\s*=\s*(\d+)", enums)] !=
            [("Middle", 0), ("Lower", 1), ("Upper", 2)] or
            [(name, int(value)) for name, value in re.findall(r"DIAGDIR_(NE|SE|SW|NW)\s*=\s*(\d+)", directions)] !=
            [("NE", 0), ("SE", 1), ("SW", 2), ("NW", 3)]):
        raise ValueError("Original water part/direction enums changed")
    lock = drawing.split("static void DrawWaterLock(const TileInfo *ti)", 1)[1].split("/** Draw a ship depot tile. */", 1)[0]
    required = ("_lock_display_data[to_underlying(part)][GetLockDirection(ti->tile)]",
                "GetCanalSprite(CF_WATERSLOPE, ti->tile)", "water_base = SPR_CANALS_BASE;",
                "HasBit(_water_feature[CF_WATERSLOPE].flags, CFF_HAS_FLAT_SPRITE)",
                "if (image == SPR_FLAT_WATER_TILE)", "image = water_base;", "image++;",
                "if (image < 5) image += water_base;", "DrawGroundSprite(image, PAL_NONE);",
                "GetCanalSprite(CF_LOCKS, ti->tile)", "base = SPR_LOCK_BASE;",
                "part == LockPart::Upper ? 8 : 0", "zoffs = ti->z > z_threshold ? 24 : 0;",
                "DrawWaterTileStruct(ti, dts.GetSequence(), base, zoffs, PAL_NONE, CF_LOCKS);")
    if not all(token in lock for token in required) or not re.search(r"CFF_HAS_FLAT_SPRITE\s*=\s*0", feature_flags):
        raise ValueError("Original lock/default elevation/custom flat-water selection changed")
    structure = drawing.split("static void DrawWaterTileStruct(", 1)[1].split("/** Draw a lock tile. */", 1)[0]
    if not all(token in structure for token in ("offset + dtss.image.sprite", "GetCanalSpriteOffset(feature, ti->tile, tile_offs)",
                                               "IsInvisibilitySet(TO_BUILDINGS)", "IsTransparencySet(TO_BUILDINGS)")):
        raise ValueError("Original water callback/order/visibility semantics changed")
    river = drawing.split("static void DrawRiverWater(const TileInfo *ti)", 1)[1].split("void DrawShoreTile", 1)[0]
    slopes = re.findall(r"case\s+(SLOPE_\w+):\s*image\s*=\s*(SPR_WATER_SLOPE_\w+);\s*break;", river)
    if len(slopes) != 4 or {slope for slope, sprite in slopes} != {"SLOPE_NW", "SLOPE_SW", "SLOPE_SE", "SLOPE_NE"}:
        raise ValueError("Original river default slope catalogue changed")
    if not all(token in river for token in ("GetCanalSprite(CF_RIVER_SLOPE, ti->tile)",
            "HasBit(_water_feature[CF_RIVER_SLOPE].flags, CFF_HAS_FLAT_SPRITE)",
            "GetCanalSpriteOffset(CF_RIVER_SLOPE, ti->tile, offset)", "DrawWaterEdges(false, edges_offset, ti->tile)")):
        raise ValueError("Original river custom flat/slope callback/edge selection changed")
    edge_groups = re.findall(r"case\s+(SLOPE_\w+):\s*(?:offset\s*\+=\s*(\d+);\s*)?edges_offset\s*\+=\s*(\d+);\s*break;", river)
    if sorted((slope, int(offset or 0), int(edges)) for slope, offset, edges in edge_groups) != [
            ("SLOPE_NE", 1, 24), ("SLOPE_NW", 3, 48), ("SLOPE_SE", 0, 12), ("SLOPE_SW", 2, 36)]:
        raise ValueError("Original river custom ground/edge offset coupling changed")
    edges = drawing.split("static void DrawWaterEdges(", 1)[1].split("/** Draw a plain sea water tile", 1)[0]
    if not all(token in edges for token in ("GetCanalSprite(CF_RIVER_EDGE, tile)", "if (base == 0) return;",
                                           "offset + 11", "IsWateredTile", "GetCanalSprite(CF_DIKES, tile)")):
        raise ValueError("Original river edge absence/connectivity semantics changed")
    return {"default_elevation_threshold_source_pixels": {"middle": 0, "lower": 0, "upper": 8},
            "elevated_default_sprite_offset": 24, "elevation_only_applies_when_lock_base_is_zero": True,
            "source_height_is_not_doubled_for_selection": True, "structure_visibility": "TO_BUILDINGS",
            "custom_feature_resolution_required": ["CF_LOCKS", "CF_WATERSLOPE", "CF_RIVER_SLOPE", "CF_RIVER_EDGE"],
            "callback_offsets_required": True, "custom_flat_water_flag": "CFF_HAS_FLAT_SPRITE bit0",
            "river_default_slopes": [{"slope": slope, "sprite_name": sprite} for slope, sprite in slopes],
            "river_custom_groups": [{"slope": "SLOPE_FLAT", "ground_offset": 0, "edge_offset": 0}] +
                [{"slope": slope, "ground_offset": int(offset or 0), "edge_offset": int(edges)} for slope, offset, edges in edge_groups],
            "river_bank_absence": "No CF_RIVER_EDGE sprite base means original edges intentionally absent; never invent a native bank owner.",
            "custom_rule": "Observe actual resolved base/callback/flag/provenance before binding; static source IDs are not proof of live Classic/NewGRF selection."}


def catalogue():
    data = {name: (ROOT / name).read_bytes() for name in SOURCES}
    constants = data["src/table/sprites.h"].decode() + "\n" + data["src/tile_type.h"].decode()
    locks = layers(data["src/table/water_land.h"].decode(), constants)
    selection = runtime_selection(data["src/water_cmd.cpp"].decode(), data["src/water_map.h"].decode(),
                                  data["src/direction_type.h"].decode(), data["src/newgrf_canal.h"].decode())
    integer = constant_reader(constants)
    return {"format": 1, "locks": locks, "runtime_selection": selection,
            "default_lock_source_count": 48, "default_water_slopes": [{"slot": slot, "sprite": integer("SPR_CANALS_BASE") + slot} for slot in range(4)],
            "river_edge_source_offsets": [{"slope": row["slope"], "edge": edge, "offset": row["edge_offset"] + edge}
                                          for row in selection["river_custom_groups"] for edge in range(12)],
            "source_sha256": {name: hashlib.sha256(content).hexdigest() for name, content in data.items()},
            "reviewed": False, "final_visual_approvals": 0,
            "scope": "Read-only original source table/selector inventory. Rear/front walls retain distinct origins and sorting extents, not inferred artwork dimensions. All three parts/four directions/two default elevation variants, four default water slopes and sixty custom river edge offsets are retained. Custom resolved IDs, source pixels, geometry, every climate/state/world, fleet clearance and ratings remain unaccepted. Animated water surfaces stay independently owned; no simulation, commands, heights, callbacks, RNG, geometry or bindings are modified."}


def default_lock_selection(part, direction, source_z, inventory=None):
    if any(type(value) is not int for value in (part, direction, source_z)) or not 0 <= part < 3 or not 0 <= direction < 4 or source_z < 0:
        raise ValueError("Use original integral part/direction/nonnegative source height")
    inventory = catalogue() if inventory is None else inventory
    row = copy.deepcopy(inventory["locks"][part * 4 + direction])
    threshold = inventory["runtime_selection"]["default_elevation_threshold_source_pixels"][row["part_name"]]
    variant = int(source_z > threshold)
    row["source_z"] = source_z
    row["elevation_variant"] = variant
    for owner in row["body"]:
        owner["selected_default_sprite"] = owner["default_sprite_variants"][variant]
    row["scope"] = "Default-base source expectation only; not a live custom selector or a 3D/world approval."
    return row


def validate_default_export(exported, inventory=None):
    inventory = catalogue() if inventory is None else inventory
    expected = {(elevation, owner["sprite_offset"]): owner["default_sprite_variants"][elevation]
                for row in inventory["locks"] for owner in row["body"] for elevation in range(2)}
    expected.update({("slope", row["slot"]): row["sprite"] for row in inventory["default_water_slopes"]})
    found = {}
    if not isinstance(exported, list):
        raise ValueError("Original terrain export must be a source-entry list")
    for row in exported:
        if not isinstance(row, dict):
            raise ValueError("Invalid original terrain source entry")
        if row.get("category") not in ("canal-lock", "water-slope"):
            continue
        key = (row.get("style"), row.get("variant")) if row["category"] == "canal-lock" else ("slope", row.get("variant"))
        if (type(row.get("style")) is not int or type(row.get("variant")) is not int or
                type(row.get("sprite")) is not int or key not in expected or key in found or row["sprite"] != expected[key] or
                (row["category"] == "water-slope" and row["style"] != 0)):
            raise ValueError("Original water default source count/ID/order differs")
        for field in ("offset", "size"):
            values = row.get(field)
            if not isinstance(values, list) or len(values) != 2 or any(type(value) is not int or (field == "size" and value <= 0) for value in values):
                raise ValueError("Original water source registration must remain exact integral metadata")
        if row.get("image") != f"{row['category']}-{row['style']}-{row['variant']}.pam":
            raise ValueError("Original water exported image ownership differs")
        found[key] = row
    if found.keys() != expected.keys():
        raise ValueError("Missing original water default source layers")
    return {"default_lock_sources": 48, "default_water_slopes": 4, "source_entries_verified": 52,
            "live_custom_selection_verified": False, "geometry_or_quality_approved": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--export", type=Path, help="Check default source metadata, not live custom selection")
    args = parser.parse_args()
    result = catalogue()
    if args.export:
        result["export_verification"] = validate_default_export(json.loads(args.export.read_text()), result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"lock_sources": 48, "water_slopes": 4, "river_edge_offsets": 60, "approved": False}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Inventory original object layers and HQ sizes without inventing geometry or states.

Sorting extents are source metadata, not inferred artwork dimensions. Ground sprites
can contain raised artwork, so a missing sortable body does not mean an empty tile.
The inventory never changes companies, ratings, objects, the map or simulation RNG.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/table/object_land.h"
SPRITES = ROOT / "src/table/sprites.h"
DRAWING = ROOT / "src/object_cmd.cpp"
KINDS = ("transmitter", "lighthouse", "statue", "owned_land", "headquarters")
CLIMATES = {"T":"temperate", "A":"arctic", "S":"tropic", "Y":"toyland"}


def layers(source, sprite_source):
    constants = {name:int(value,0) for name,value in re.findall(r"static const SpriteID (SPR_\w+)\s*=\s*(0x[\da-fA-F]+|\d+)\s*;",sprite_source)}
    recolour = re.search(r"static constexpr uint8_t RECOLOUR_BIT\s*=\s*(\d+)\s*;",sprite_source)
    palette = re.search(r"static const PaletteID PAL_NONE\s*=\s*(\d+)\s*;",sprite_source)
    if not recolour or not palette or not 0 <= int(recolour[1]) < 32:
        raise ValueError("Original object palette constants changed; review the source flags")

    def sprite(expression, company=False):
        match = re.fullmatch(r"\s*(SPR_\w+)(\s*\|\s*\(1\s*<<\s*PALETTE_MODIFIER_COLOUR\))?\s*",expression)
        if not match or match[1] not in constants:
            raise ValueError("Unknown original object sprite expression")
        company = company or bool(match[2])
        return {"sprite":constants[match[1]],"sprite_name":match[1],"company_colour":company,
                "sprite_flags":(1 << int(recolour[1])) if company else 0,"palette":"PAL_NONE","palette_id":int(palette[1])}

    sequences = {}
    for name,body in re.findall(r"static const DrawTileSeqStruct (_object_\w+_seq|_object_hq_\w+)\[\] = \{(.*?)\};",source,re.S):
        macro = re.fullmatch(r"\s*TILE_SEQ_LINE\(\s*(\d+)\s*,\s*(.*?)\)\s*",body,re.S)
        if macro:
            piece = {**sprite(macro[2]),"origin":[0,0,0],"sort_extent":[16,16,int(macro[1])]}
        else:
            direct = re.fullmatch(r"\s*\{\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*\{(.*?),\s*PAL_NONE\}\s*\},\s*",body,re.S)
            if not direct:
                raise ValueError("Original object sequence needs explicit source-layer review")
            piece = {**sprite(direct[7]),"origin":list(map(int,direct.groups()[:3])),"sort_extent":list(map(int,direct.groups()[3:6]))}
        sequences[name] = [piece]
    if len(sequences) != 13:
        raise ValueError("Original object body sequences changed; review all source layers")
    specs = re.findall(r"M\(\s*(STR_\w+)\s*,\s*(0x[\da-fA-F]+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*LandscapeTypes\(\{([^}]+)\}\)\s*,\s*(\d+)\s*,\s*ObjectFlags\(\{([^}]+)\}\)\s*\)",source)
    if len(specs) != 5:
        raise ValueError("Original object type catalogue changed; review its source specifications")
    types = []
    for identifier,(label,size,build_cost,clear_cost,height,climates,generation,flags) in enumerate(specs):
        climate_names = [value.strip() for value in climates.split(",")]
        if any(value not in CLIMATES for value in climate_names):
            raise ValueError("Unknown original object climate")
        size = int(size,0)
        types.append({"id":identifier,"kind":KINDS[identifier],"name":label,"footprint_tiles":[size&15,size>>4],
                      "build_cost_multiplier":int(build_cost),"clear_cost_multiplier":int(clear_cost),"spec_height":int(height),
                      "climates":[CLIMATES[value] for value in climate_names],"generation_amount":int(generation),
                      "flags":re.findall(r"ObjectFlag::(\w+)",flags),"reviewed":False})
    ordinary = source.split("extern const DrawTileSpriteSpan _objects[] = {",1)[1].split("};",1)[0]
    base = re.findall(r"\{\s*\{\s*(SPR_\w+)\s*,\s*PAL_NONE\s*\}\s*,\s*(_object_\w+_seq)\s*\}",ordinary)
    if len(base) != 4:
        raise ValueError("Original non-HQ object layers changed; review their catalogue")
    tiles = []
    for identifier,(ground,sequence) in enumerate(base):
        if sequence not in sequences:
            raise ValueError("Original object references an unknown body sequence")
        tiles.append({"object_id":identifier,"kind":KINDS[identifier],"size_stage":None,"part":0,"tile_offset":[0,0],
                      "ground":sprite(ground),"body":sequences[sequence],"reviewed":False})
    hq = source.split("static const DrawTileSpriteSpan _object_hq[] = {",1)[1].split("};",1)[0]
    entries = re.findall(r"TILE_SPRITE_(LINE_NOTHING|LINE)\(\s*(SPR_\w+)\s*(?:,\s*(_object_hq_\w+)\s*)?\)",hq)
    if len(entries) != 20:
        raise ValueError("Original headquarters needs all five four-tile sizes")
    for index,(kind,ground,sequence) in enumerate(entries):
        stage,part = divmod(index,4)
        if (kind == "LINE_NOTHING" and sequence) or (kind == "LINE" and sequence not in sequences):
            raise ValueError("Original HQ ground/body ownership changed; review the source layers")
        tiles.append({"object_id":4,"kind":"headquarters","size_stage":stage,"part":part,"tile_offset":[part%2,part//2],
                      "ground":sprite(ground,True),"body":sequences[sequence] if sequence else [],"reviewed":False})
    return {"types":types,"tiles":tiles,"headquarters_size_count":5,"headquarters_tile_count":20,
            "headquarters_ground_only_slots":sum(not tile["body"] for tile in tiles if tile["object_id"]==4),
            "scope":"Original static object source catalogue only: five types, four non-HQ layouts and all twenty HQ tiles/five score-dependent sizes. Preserve separate ground/body ownership, original palette modifiers, climates, flags and source sorting extents. Ground-only sprites can include raised artwork. No source pixels are inspected here, no voxel geometry or runtime capture is asserted, and no company rating, map, object, source clock or RNG changes. Source-image/world/footprint/clearance/fidelity review remains required.","final_visual_approvals":0}


def runtime_selection(source):
    """Check the original layer/size selectors, never evaluating game state or scores."""
    draw = source.split("static void DrawTile_Object(TileInfo *ti)",1)[1].split("static int GetSlopePixelZ_Object",1)[0]
    update = source.split("void UpdateCompanyHQ(TileIndex tile, uint score)",1)[1].split("void UpdateObjectColours",1)[0]
    size = source.split("static uint8_t GetCompanyHQSize(TileIndex tile)",1)[1].split("void UpdateCompanyHQ",1)[0]
    increase = source.split("static void IncreaseCompanyHQSize(TileIndex tile)",1)[1].split("static uint8_t GetCompanyHQSize",1)[0]
    if ("return GetAnimationFrame(tile);" not in size or
            "GetCompanyHQSize(ti->tile) << 2 | TileY(diff) << 1 | TileX(diff)" not in draw or
            "ti->tile - Object::GetByTile(ti->tile)->location.tile" not in draw or
            "to == OWNER_NONE ? PAL_NONE : GetCompanyPalette(to)" not in draw or
            "while (GetCompanyHQSize(tile) < val)" not in update or
            [int(value) for value in re.findall(r"if \(score >= (\d+)\) val\+\+;",update)] != [170,350,520,720] or
            "for (TileIndex t : ta)" not in increase or "SetAnimationFrame(t, GetAnimationFrame(t) + 1);" not in increase or
            "if (spec->flags.Test(ObjectFlag::HasNoFoundation))" not in draw or
            "case SPR_FLAT_BARE_LAND:          DrawClearLandTile(ti, 0); break;" not in draw or
            "if (!IsInvisibilitySet(TO_STRUCTURES))" not in draw or
            "AddSortableSpriteToDraw(dtss.image.sprite, palette, *ti, dtss, IsTransparencySet(TO_STRUCTURES))" not in draw):
        raise ValueError("Original object runtime selection changed; review source ordering, ownership and state semantics")
    return {"headquarters_score_thresholds":[170,350,520,720],"headquarters_size_storage":"tile animation frame",
            "headquarters_upgrades_only":True,"headquarters_layout_index":"size*4+tile_y*2+tile_x",
            "headquarters_tile_order":["north","west","east","south"],
            "company_palette":"owner palette, or PAL_NONE for OWNER_NONE",
            "owned_land_ground":"original slope-following bare-land selection, not forced flat ground",
            "structure_visibility":"original invisibility omits body sequence; transparency applies to bodies"}


def validate_export(exported, expected=None):
    """Match the native exporter to every independently parsed source layer."""
    def same_value(actual, original):
        if type(actual) is not type(original):
            return False
        if isinstance(original,list):
            return len(actual)==len(original) and all(same_value(a,b) for a,b in zip(actual,original))
        return actual == original

    expected = catalogue()["tiles"] if expected is None else expected
    if not isinstance(exported,list) or len(exported) != len(expected):
        raise ValueError("Original object exported layout count differs")
    for actual, source in zip(exported,expected):
        if not isinstance(actual,dict) or any(key not in actual or not same_value(actual[key],source[key]) for key in ("object_id","size_stage","part","tile_offset")):
            raise ValueError("Original object exported source order/registration differs")
        if not isinstance(actual.get("body"),list) or len(actual["body"]) != len(source["body"]):
            raise ValueError("Original object exported body ownership differs")
        for role, originals, images in (("ground",[source["ground"]],[actual.get("ground")]),("body",source["body"],actual["body"])):
            for index,(original,image) in enumerate(zip(originals,images)):
                if (not isinstance(image,dict) or any(key not in image or not same_value(image[key],original[key]) for key in ("sprite","sprite_flags","company_colour")) or
                        not same_value(image.get("palette"),original["palette_id"]) or
                        (role == "body" and any(key not in image or not same_value(image[key],original[key]) for key in ("origin","sort_extent")))):
                    raise ValueError("Original object exported layer metadata differs")
                stage = source["size_stage"] if source["size_stage"] is not None else 0
                filename = f"object-{source['object_id']}-{stage}-{source['part']}-{role}"+(f"-{index}" if role == "body" else "")+".pam"
                if image.get("image") != filename:
                    raise ValueError("Original object exported image ownership differs")
                for key in ("sprite_offset","sprite_size"):
                    values = image.get(key)
                    if not isinstance(values,list) or len(values) != 2 or any(type(value) is not int or (key == "sprite_size" and value <= 0) for value in values):
                        raise ValueError("Original object exported pixel registration is invalid")
                colours = image.get("palette_indices")
                if not isinstance(colours,list) or any(type(value) is not int or not 1 <= value <= 255 for value in colours) or colours != sorted(set(colours)):
                    raise ValueError("Original object exported source palette is invalid")
    return {"source_equivalent_layouts":len(expected),"ground_layers":len(expected),
            "separate_body_layers":sum(len(row["body"]) for row in expected),
            "ground_only_headquarters_slots":sum(row["object_id"]==4 and not row["body"] for row in expected)}


def catalogue():
    source, sprites, drawing = SOURCE.read_bytes(), SPRITES.read_bytes(), DRAWING.read_bytes()
    result = layers(source.decode(),sprites.decode())
    result["runtime_selection"] = runtime_selection(drawing.decode())
    result["source_sha256"] = {str(path.relative_to(ROOT)):hashlib.sha256(data).hexdigest() for path,data in ((SOURCE,source),(SPRITES,sprites),(DRAWING,drawing))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a fresh output path to preserve earlier source audits")
    result = catalogue()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(f"Original objects: {len(result['types'])} types, {len(result['tiles'])} source tile layouts, five HQ sizes; voxel coverage and visual approval unproven")


if __name__ == "__main__":
    main()

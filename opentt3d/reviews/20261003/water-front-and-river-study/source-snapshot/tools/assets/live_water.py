#!/usr/bin/env python3
"""Validate actual water callbacks; source observations never establish geometry coverage."""
import copy

from original_water import catalogue as original_catalogue


def integers(row, field, length, positive=False):
    values = row.get(field)
    if not isinstance(values, list) or len(values) != length or any(type(value) is not int or (positive and value <= 0) for value in values):
        raise ValueError(f"Original water {field} must retain exact integer registration")
    return values


def selected_lock_sources(observations, fixture, climate, originals=None):
    """All48 semantic wall owners must be observed, even when GRF artwork is shared."""
    originals = original_catalogue() if originals is None else originals
    if type(climate) is not int or climate not in range(4) or not isinstance(observations, list):
        raise ValueError("Use a real climate and original callback observation list")
    if not isinstance(fixture, dict) or not isinstance(fixture.get("locks"), list) or len(fixture["locks"]) != 8:
        raise ValueError("Require the complete original saved natural-lock fixture")
    width, map_height = fixture.get("map_width"), fixture.get("map_height")
    if any(type(value) is not int or value < 16 for value in (width, map_height)):
        raise ValueError("Original saved map dimensions are missing")
    sites, selectors = {}, set()
    for lock in fixture["locks"]:
        if not isinstance(lock, dict) or any(type(lock.get(key)) is not int for key in ("tile", "x", "y", "direction", "elevation", "height", "lower", "upper")):
            raise ValueError("Saved lock sites must be integral, not coerced")
        direction, elevation = lock["direction"], lock["elevation"]
        if direction not in range(4) or elevation not in range(2) or (elevation == 0 and lock["height"] != 0) or (elevation == 1 and lock["height"] <= 0):
            raise ValueError("Saved natural lock direction/elevation differs")
        if ((elevation, direction) in selectors or lock.get("connected_both_ways") is not True or
                not (4 <= lock["x"] < width-4 and 4 <= lock["y"] < map_height-4) or lock["tile"] != lock["x"]+width*lock["y"]):
            raise ValueError("Duplicate/unconnected or misregistered original lock site")
        delta = (-1, width, 1, -width)[direction]
        if lock["lower"] != lock["tile"]-delta or lock["upper"] != lock["tile"]+delta:
            raise ValueError("Original lock part offsets differ")
        selectors.add((elevation, direction))
        for part, tile in enumerate((lock["tile"], lock["lower"], lock["upper"])):
            if tile in sites:
                raise ValueError("Original saved lock sites overlap")
            sites[tile] = (elevation, direction, part, (lock["height"]+int(part == 2))*8)
    bodies, grounds = {}, {}
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("Invalid original water callback observation")
        if row.get("kind") != "lock":
            continue
        tile = row.get("tile")
        if type(tile) is not int or tile not in sites:
            raise ValueError("Live lock callback does not belong to the original saved fixture")
        elevation, direction, part, height = sites[tile]
        # Original Slope bits are W=1, S=2, E=4, N=8; never use screen order.
        slope = (12, 6, 3, 9)[direction] if part == 0 else 0
        for field, expected in (("climate", climate), ("direction", direction), ("part", part), ("source_height", height), ("palette", 0), ("slope", slope)):
            if type(row.get(field)) is not int or row[field] != expected:
                raise ValueError(f"Live original lock {field} differs from its saved state")
        xy = integers(row, "tile_xy", 2)
        if xy != [tile % width, tile // width] or integers(row, "draw_origin", 3) != [xy[0]*16, xy[1]*16, height]:
            raise ValueError("Live lock tile/sequence anchor was moved or its source height doubled")
        if row.get("cropped") is not False or row.get("transparent") is not False:
            raise ValueError("Source studies require complete original visible owners")
        if type(row.get("sprite")) is not int or row["sprite"] <= 0 or type(row.get("image")) is not int or row["image"] != row["sprite"]:
            raise ValueError("Live source sprite ownership/flags differ")
        if (type(row.get("base_graphics")) is not bool or not isinstance(row.get("base_set"), str) or not row["base_set"] or
                not isinstance(row.get("source_file"), str) or not row["source_file"]):
            raise ValueError("Live water source provenance is missing")
        if type(row.get("water_class")) is not int or row["water_class"] not in range(3):
            raise ValueError("Original lock water class must remain integral and independently owned")
        integers(row, "source_offset", 2)
        integers(row, "source_size", 2, positive=True)
        digest = row.get("source_image_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(value not in "0123456789abcdef" for value in digest):
            raise ValueError("Retain SHA-256 of every complete actual selected source")
        # A generation or exported filename may vary by reload/run. Neither can
        # change one source pixel, original anchor, palette, owner or sprite ID.
        source = {key: copy.deepcopy(value) for key,value in row.items() if key not in ("texture_generation", "source_image")}
        template = originals["locks"][part*4+direction]
        if row.get("role") == "ground":
            if any(key in row for key in ("sequence_origin", "sort_extent", "sequence_offset")):
                raise ValueError("Animated water must remain an independent ground owner")
            key = (elevation, part, direction)
            target = grounds
        elif row.get("role") == "body":
            origin = integers(row, "sequence_origin", 3)
            owners = [owner for owner in template["body"] if owner["origin"] == origin]
            if len(owners) != 1 or integers(row, "sequence_offset", 3) != [0, 0, 0] or integers(row, "sort_extent", 3) != owners[0]["sort_extent"]:
                raise ValueError("Original rear/front lock sequence ownership/sorting metadata differs")
            key = (elevation, part, direction, owners[0]["face"])
            target = bodies
        else:
            raise ValueError("Unknown original lock layer role")
        if key in target and source != target[key]:
            raise ValueError("Same saved original lock owner selects inconsistent source bytes/metadata")
        target[key] = source
    if len(bodies) != 48 or len(grounds) != 24:
        raise ValueError("Missing actual rear/front/ground callbacks for all original lock sites")
    return {"bodies": [{"elevation": key[0], "part": key[1], "direction": key[2], "face": key[3], "source": source}
                       for key,source in sorted(bodies.items())],
            "grounds": [{"elevation": key[0], "part": key[1], "direction": key[2], "source": source}
                        for key,source in sorted(grounds.items())],
            "wall_owner_states_verified": 48, "independent_water_owners_verified": 24,
            "dynamic_ids_inferred": False, "geometry_or_quality_approved": False,
             "scope": "Actual callback-selected sources match public saved original part/direction/elevation/climate/anchors. This inventories source bytes, not structural models, alternate/custom-family completeness, animated phases, fleet clearance or visual approval."}


def selected_river_sources(observations, fixture, climate):
    """Retain incidental real sloped-river sources without guessing feature/edge IDs.

    Ground callbacks contain both water and conditional bank artwork. Neither a
    numeric sprite ID nor sorting/image dimensions identify CF_RIVER_EDGE offsets.
    The observer deduplicates calls, so this is not a compositing-order/phase trace.
    """
    if type(climate) is not int or climate not in range(4) or not isinstance(observations, list):
        raise ValueError("Use a real climate and original river observation list")
    if not isinstance(fixture, dict):
        raise ValueError("Require the original saved map dimensions")
    width, height = fixture.get("map_width"), fixture.get("map_height")
    if any(type(value) is not int or value < 16 for value in (width, height)):
        raise ValueError("Original saved map dimensions are missing")
    sources, tiles = {}, {}
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("Invalid original river observation")
        if row.get("kind") != "sloped-river":
            continue
        if (type(row.get("climate")) is not int or row["climate"] != climate or
                type(row.get("water_class")) is not int or row["water_class"] != 2 or
                type(row.get("slope")) is not int or row["slope"] not in (12, 6, 3, 9)):
            raise ValueError("Original river climate/water class/slope differs")
        tile, source_height = row.get("tile"), row.get("source_height")
        if (type(tile) is not int or not 0 <= tile < width*height or type(source_height) is not int or
                source_height < 0 or source_height % 8 != 0):
            raise ValueError("Original river tile and source height must remain integral")
        xy = integers(row, "tile_xy", 2)
        if (xy != [tile % width, tile // width] or
                integers(row, "draw_origin", 3) != [xy[0]*16, xy[1]*16, source_height]):
            raise ValueError("Original river tile/source anchor differs")
        tile_state = (row["slope"],source_height)
        if tile in tiles and tiles[tile] != tile_state:
            raise ValueError("Original river owners disagree about their tile state")
        tiles[tile] = tile_state
        if (row.get("role") != "ground" or row.get("transparent") is not False or row.get("cropped") is not False or
                any(key in row for key in ("sequence_origin", "sort_extent", "sequence_offset"))):
            raise ValueError("Keep each complete original ground owner independently registered")
        if (type(row.get("sprite")) is not int or row["sprite"] <= 0 or type(row.get("image")) is not int or
                row["image"] != row["sprite"] or type(row.get("palette")) is not int or row["palette"] != 0):
            raise ValueError("Original river sprite/flags/palette differ")
        if (type(row.get("base_graphics")) is not bool or
                any(not isinstance(row.get(key), str) or not row[key] for key in ("base_set", "source_file"))):
            raise ValueError("Original river source provenance is missing")
        integers(row, "source_offset", 2)
        integers(row, "source_size", 2, positive=True)
        digest = row.get("source_image_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(value not in "0123456789abcdef" for value in digest):
            raise ValueError("Retain SHA-256 of each complete selected original river image")
        source = {key: copy.deepcopy(value) for key, value in row.items() if key not in ("texture_generation", "source_image")}
        key = (tile, row["sprite"], row["palette"])
        if key in sources and sources[key] != source:
            raise ValueError("Same river source owner selects conflicting bytes/metadata")
        sources[key] = source
    return {"selected_ground_sources": [source for key, source in sorted(sources.items())],
            "observed_tiles": len({key[0] for key in sources}),
            "observed_slopes": sorted({row["slope"] for row in sources.values()}),
            "feature_offsets_resolved": False, "conditional_absences_verified": False,
            "layer_order_or_animation_verified": False, "complete_river_family_verified": False,
            "geometry_or_quality_approved": False,
            "scope": "Actual selected sloped-river ground source bytes/provenance/anchors only. Water and bank owners are not classified from IDs or dimensions. Feature offsets, flat rivers, conditional absence, repeated draw order, animated phases, other climates/slopes/custom families, structural volumes and ships remain unverified."}

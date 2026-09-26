#!/usr/bin/env python3
"""Bind hand-authored assemblies to the pinned upstream vehicle sprite tables.

Only metadata is extracted from upstream. Geometry comes exclusively from the
explicit assemblies in assets/3d/vehicles.json, never from image analysis.
"""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def array(path, name):
    source = path.read_text().split(name + "[] = {", 1)[1].split("};", 1)[0]
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    return [int(value.strip(), 0) for value in source.split(",") if value.strip()]


def definitions():
    source = (ROOT / "src/table/engines.h").read_text()
    names = {}
    section = source.split("_orig_engine_info[] = {", 1)[1].split("\n};", 1)[0]
    for line in section.splitlines():
        match = re.search(r"\b(M[TMWRSA])\(.*LandscapeTypes\(\{([^}]+)\}\).*//\s*(\d+)\s+(.+)", line)
        if match:
            names[int(match[3])] = (match[4].strip(), re.findall(r"[TASY]", match[2]))
    train = ROOT / "src/table/train_sprites.h"
    bases = {
        "train": array(train, "_engine_sprite_base"),
        "road": array(ROOT / "src/roadveh_cmd.cpp", "_roadveh_images"),
        "ship": array(ROOT / "src/ship_cmd.cpp", "_ship_sprites"),
        "aircraft": array(ROOT / "src/aircraft_cmd.cpp", "_aircraft_sprite"),
    }
    masks = array(train, "_engine_sprite_and")
    adds = array(train, "_engine_sprite_add")
    cargo = {"train": array(train, "_wagon_full_adder"), "road": array(ROOT / "src/roadveh_cmd.cpp", "_roadveh_full_adder")}
    result = {}
    for kind, table, macro, offset in [("train", "rail", "RVI", 0), ("road", "road", "ROV", 116), ("ship", "ship", "SVI", 204), ("aircraft", "aircraft", "AVI", 215)]:
        section = source.split(f"_orig_{table}_vehicle_info[] = {{", 1)[1].split("\n};", 1)[0]
        for match in re.finditer(rf"\b{macro}\(\s*(\d+),.*?\),?\s*//\s*(\d+)\s+([^\n]+)", section):
            image, local = int(match[1]), int(match[2])
            engine = offset + local
            mask, add = (masks[image], adds[image]) if kind == "train" else (7, 0)
            sprites = [bases[kind][image] + ((direction + add) & mask) for direction in range(8)]
            full = [sprite + cargo.get(kind, [0] * len(bases[kind]))[image] for sprite in sprites]
            name, climates = names[engine]
            result[str(engine)] = {"name": name, "kind": kind, "climates": climates, "image_index": image,
                                   "sprites": sprites, "loaded_sprites": full}
    if set(result) != {str(i) for i in range(256)}:
        raise ValueError("Pinned upstream vehicle catalogue is not the expected complete 0..255 range")
    return result


def compile_catalogue(data):
    assemblies = data["assemblies"]
    def parts(name, stack=()):
        if name in stack:
            raise ValueError(f"Cyclic assembly inheritance: {name}")
        item = assemblies[name]
        base, loaded = [], []
        for parent in item.get("extends", []):
            first, second = parts(parent, (*stack, name))
            base.extend(first)
            loaded.extend(second)
        return base + item.get("parts", []), loaded + item.get("loaded_parts", [])
    vehicles = definitions()
    assigned = set()
    for binding in data["bindings"]:
        base, loaded = parts(binding["assembly"])
        if not base:
            raise ValueError(f"Empty vehicle assembly: {binding['assembly']}")
        for engine in binding["engines"]:
            key = str(engine)
            if key in assigned or key not in vehicles:
                raise ValueError(f"Duplicate/unknown vehicle binding: {engine}")
            assigned.add(key)
            vehicles[key].update(assembly=binding["assembly"], parts=base, loaded_parts=loaded,
                                 review_status=binding.get("review_status", "work-in-progress"))
    if assigned != set(vehicles):
        raise ValueError(f"Unbound vehicles: {sorted(set(vehicles) - assigned, key=int)}")
    sets = {kind: {} for kind in ("train", "road", "ship", "aircraft")}
    for vehicle in definitions().values():
        sets[vehicle["kind"]][str(vehicle["image_index"])] = {"sprites": vehicle["sprites"], "loaded_sprites": vehicle["loaded_sprites"]}
    return {"format": 3, "license": data["license"], "reference": data["reference"], "models": vehicles, "sprite_sets": sets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalogue = compile_catalogue(json.loads(args.source.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalogue, separators=(",", ":")) + "\n")
    print(f"Bound {len(catalogue['models'])} vanilla vehicles to authored assemblies")


if __name__ == "__main__":
    main()

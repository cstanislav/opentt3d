#!/usr/bin/env python3
"""Reject malformed runtime model packs before copying them into a game build."""

import argparse
import json
import math
from pathlib import Path


def reject_constant(value):
    raise ValueError(f"Non-finite model value: {value}")


def numbers(value, length, label, low=None, high=None, positive=False):
    if not isinstance(value, list) or len(value) != length or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        or (low is not None and v < low) or (high is not None and v > high)
        or (positive and v <= 0) for v in value
    ):
        raise ValueError(f"Invalid {label}: {value}")


def crop(value, label):
    numbers(value, 4, label, 0, 1)
    if value[0] >= value[2] or value[1] >= value[3]:
        raise ValueError(f"Empty or inverted {label}: {value}")


def validate_tree(model, identifier):
    materials = model["tree_materials"]
    numbers(materials.get("wood_colour"), 3, "wood colour", 0, 1)
    crop(materials.get("foliage_crop"), "foliage crop")
    for stage, region in materials.get("foliage_crop_by_stage", {}).items():
        if stage not in {str(i) for i in range(7)}:
            raise ValueError(f"Invalid lifecycle stage {stage}")
        crop(region, f"stage {stage} foliage crop")
    for name in ("repeat", "scale"):
        if name in materials:
            numbers(materials[name], 2, name, positive=True)
    if "growth" in materials:
        numbers(materials["growth"], 7, "growth", positive=True)
    for flag in ("retain_dead_foliage", "foliage_charts"):
        if flag in materials and not isinstance(materials[flag], bool):
            raise ValueError(f"{flag} must be boolean")
    roles = set()
    for group in model["parts"]:
        if not isinstance(group, list) or len(group) != 2 or group[0] not in ("wood", "foliage") or not isinstance(group[1], list) or not group[1]:
            raise ValueError(f"Tree {identifier} needs nonempty wood/foliage groups")
        roles.add(group[0])
        for part in group[1]:
            if not isinstance(part, list) or not part:
                raise ValueError(f"Invalid tree {identifier} part")
            if part[0] == "branch":
                if len(part) != 2 or not isinstance(part[1], list) or len(part[1]) < 2:
                    raise ValueError("Branch needs at least two controls")
                for index, point in enumerate(part[1]):
                    numbers(point, 4, "branch control")
                    if point[3] <= 0 or (index and point[:3] == part[1][index-1][:3]):
                        raise ValueError("Branch has zero radius or coincident controls")
            elif part[0] in ("crown", "bough"):
                if len(part) not in (7, 8):
                    raise ValueError("Crown/bough requires position, radii, height and optional seed")
                numbers(part[1:], len(part)-1, "crown/bough")
                numbers(part[4:7], 3, "crown/bough dimensions", positive=True)
            elif part[0] in ("frond", "leaf", "palm_frond"):
                if len(part) not in (8, 9, 10):
                    raise ValueError("Leaf blade requires root, tip, width and optional arch/thickness")
                numbers(part[1:], len(part)-1, "leaf blade")
                if part[7] <= 0 or part[1:3] == part[4:6] or (len(part) == 10 and part[9] <= 0):
                    raise ValueError("Leaf blade has no width, length or thickness")
    if roles != {"wood", "foliage"}:
        raise ValueError(f"Tree {identifier} is missing wood or foliage")


def validate(data):
    if data.get("format") != 2 or not isinstance(data.get("models"), dict) or not isinstance(data.get("aliases"), dict):
        raise ValueError("Invalid runtime model pack")
    for identifier, model in data["models"].items():
        if not isinstance(model.get("parts"), list):
            raise ValueError(f"Model {identifier} has no component list")
        if "tree_materials" in model:
            validate_tree(model, identifier)
    for identifier, alias in data["aliases"].items():
        target = alias.get("model") if isinstance(alias, dict) else alias
        if isinstance(target, bool) or not isinstance(target, int) or str(target) not in data["models"] or identifier in data["models"]:
            raise ValueError(f"Alias {identifier} has no unique model target")
        if isinstance(alias, dict) and "wood_colour" in alias:
            if "tree_materials" not in data["models"][str(target)]:
                raise ValueError("Wood colour override requires component tree materials")
            numbers(alias["wood_colour"], 3, "alias wood colour", 0, 1)
    bound = set()
    for name, material in data.get("bark_materials", {}).items():
        crop(material.get("crop"), f"{name} bark crop")
        numbers(material.get("repeat"), 2, "bark repeat", positive=True)
        numbers(material.get("reference_colour"), 3, "bark reference colour", high=1, positive=True)
        sprite = material.get("sprite")
        if isinstance(sprite, bool) or not isinstance(sprite, int) or not 1576 <= sprite <= 2009:
            raise ValueError(f"Bark material {name} has no tree source sprite")
        for identifier in material.get("models", []):
            key = str(identifier)
            alias = data["aliases"].get(key)
            target = alias.get("model") if isinstance(alias, dict) else alias
            model = data["models"].get(key, data["models"].get(str(target), {}))
            if key in bound or "tree_materials" not in model:
                raise ValueError(f"Invalid or duplicate bark binding {key}")
            bound.add(key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    validate(json.loads(args.source.read_text(encoding="utf-8"), parse_constant=reject_constant))


if __name__ == "__main__":
    main()

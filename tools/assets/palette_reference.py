#!/usr/bin/env python3
"""Inspect the pinned DOS palette for explicitly authored voxel materials."""
import argparse
from pathlib import Path
import re


def colours():
    root = Path(__file__).resolve().parents[2]
    text = (root / "src/table/palettes.h").read_text().split("static const Palette _palette =", 1)[1]
    return [(0, 0, 0)] + [tuple(map(int, row)) for row in re.findall(r"M\(\s*(\d+),\s*(\d+),\s*(\d+)\)", text)[:255]]


def nearest(rgb):
    palette = colours()
    return sorted(range(1, 215), key=lambda index: sum((a-b)**2 for a, b in zip(rgb, palette[index])))[:4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rgb", nargs=3, type=int)
    parser.add_argument("--indices", nargs="+", type=int)
    args = parser.parse_args()
    palette = colours()
    indices = nearest(args.rgb) if args.rgb else args.indices or range(1, 215)
    for index in indices:
        print(f"{index}: {palette[index]}")


if __name__ == "__main__":
    main()

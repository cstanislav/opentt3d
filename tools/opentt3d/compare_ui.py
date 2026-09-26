#!/usr/bin/env python3
"""Compare explicit UI rectangles in native game screenshots, pixel for pixel.

The minimal PNG reader supports non-interlaced 8-bit RGB/RGBA screenshots emitted
by OpenTTD, using only Python's standard library.
"""

import argparse
import json
from pathlib import Path
import struct
import zlib


def read_png(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG: {path}")
    offset, compressed, header = 8, bytearray(), None
    while offset < len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        checksum = struct.unpack_from(">I", data, offset + 8 + length)[0]
        if zlib.crc32(kind + payload) != checksum:
            raise ValueError("Corrupt PNG chunk")
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
        offset += 12 + length
    if header is None:
        raise ValueError("Missing PNG header")
    width, height, depth, colour, compression, filtering, interlace = header
    if depth != 8 or colour not in (2, 6) or compression or filtering or interlace:
        raise ValueError("Expected a non-interlaced 8-bit RGB/RGBA screenshot")
    channels = 3 if colour == 2 else 4
    stride = width * channels
    raw = zlib.decompress(compressed)
    if len(raw) != (stride + 1) * height:
        raise ValueError("Incorrect PNG image length")
    previous = bytearray(stride)
    rows = []
    for y in range(height):
        method = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            left = row[i - channels] if i >= channels else 0
            above = previous[i]
            corner = previous[i - channels] if i >= channels else 0
            if method == 0:
                prediction = 0
            elif method == 1:
                prediction = left
            elif method == 2:
                prediction = above
            elif method == 3:
                prediction = (left + above) // 2
            elif method == 4:
                p = left + above - corner
                a, b, c = abs(p - left), abs(p - above), abs(p - corner)
                prediction = left if a <= b and a <= c else above if b <= c else corner
            else:
                raise ValueError("Invalid PNG filter")
            row[i] = (row[i] + prediction) & 255
        previous = row
        rows.append(bytes(row) if channels == 3 else b"".join(row[i:i + 3] for i in range(0, stride, 4)))
    return width, height, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--rect", action="append", required=True, help="x,y,width,height; repeat for each UI region")
    parser.add_argument("--output", type=Path, help="Retain an exact-comparison JSON report, including failures")
    args = parser.parse_args()
    width, height, reference = read_png(args.reference)
    w, h, actual = read_png(args.actual)
    if (w, h) != (width, height):
        raise SystemExit(f"Screenshot sizes differ: {(width, height)} vs {(w, h)}")
    print(f"Screenshot dimensions: {width}x{height}")
    report = {"reference": str(args.reference), "actual": str(args.actual), "size": [width, height], "channels": "RGB", "regions": []}
    total = 0
    for rect in args.rect:
        x, y, w, h = map(int, rect.split(","))
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
            parser.error(f"Rectangle outside screenshot: {rect}")
        changed = sum(reference[row][col * 3:col * 3 + 3] != actual[row][col * 3:col * 3 + 3]
                      for row in range(y, y + h) for col in range(x, x + w))
        print(f"{rect}: {changed} differing pixels out of {w * h}")
        report["regions"].append({"rect": [x, y, w, h], "pixels": w * h, "different_pixels": changed})
        if changed:
            for row in range(y, y + h):
                mismatch = next((col for col in range(x, x + w) if reference[row][col * 3:col * 3 + 3] != actual[row][col * 3:col * 3 + 3]), None)
                if mismatch is not None:
                    i = mismatch * 3
                    print(f"  First difference at {mismatch},{row}: {tuple(reference[row][i:i + 3])} vs {tuple(actual[row][i:i + 3])}")
                    break
        total += changed
    report["exact"] = total == 0
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    if total:
        raise SystemExit(f"UI comparison failed: {total} differing pixels")
    print("All selected UI regions match exactly")


if __name__ == "__main__":
    main()

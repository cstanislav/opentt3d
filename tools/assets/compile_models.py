#!/usr/bin/env python3
"""Triangulate explicitly authored model assemblies into a C++ mesh library.

This compiler accepts only model descriptions, never reference sprite images.
It also exports glTF 2.0 for inspecting the same meshes in standard 3D tools.
"""

import argparse
import base64
import json
import math
from pathlib import Path
import re
import struct


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def triangle(a, b, c, colour, company):
    u, v = subtract(b, a), subtract(c, a)
    normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    length = math.sqrt(sum(x * x for x in normal))
    if length < 1e-8:
        return []  # Coincident loft apex vertices produce no face.
    normal = tuple(x / length for x in normal)
    return [tuple(p) + normal + tuple(colour) + (float(company),) for p in (a, b, c)]


def polyhedron(points, faces, colour, company):
    vertices = []
    for face in faces:
        for i in range(1, len(face) - 1):
            vertices.extend(triangle(points[face[0]], points[face[i]], points[face[i + 1]], colour, company))
    return vertices


def box(part, colour, company):
    x, y, z = part["min"]
    X, Y, Z = part["max"]
    if not (x < X and y < Y and z < Z):
        raise ValueError("Box/roof bounds must have positive volume")
    if part["shape"] == "roof":
        points = [(x, y, z), (X, y, z), (X, Y, z), (x, Y, z), ((x + X) / 2, y, Z), ((x + X) / 2, Y, Z)]
        faces = [(3, 2, 1, 0), (0, 1, 4), (2, 3, 5), (0, 4, 5, 3), (1, 2, 5, 4)]
    else:
        points = [(x, y, z), (X, y, z), (X, Y, z), (x, Y, z), (x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)]
        faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return polyhedron(points, faces, colour, company)


def loft(part, colour, company):
    n = part["segments"]
    if not 3 <= n <= 64 or len(part["rings"]) < 2 or part["axis"] not in ("x", "y", "z"):
        raise ValueError("Invalid loft")
    points = []
    for along, a, b, ra, rb in part["rings"]:
        if ra < 0 or rb < 0:
            raise ValueError("Negative loft radius")
        for i in range(n):
            p, q = a + ra * math.cos(i * math.tau / n), b + rb * math.sin(i * math.tau / n)
            points.append({"x": (along, p, q), "y": (q, along, p), "z": (p, q, along)}[part["axis"]])
    # The Y-axis ring is cyclically permuted to preserve face winding.
    if part["axis"] == "y":
        # Authors specify ring centre as X,Z, like the other axes' named coordinates.
        for ring, (along, a, b, ra, rb) in enumerate(part["rings"]):
            for i in range(n):
                points[ring * n + i] = (a + ra * math.sin(i * math.tau / n), along, b + rb * math.cos(i * math.tau / n))
    faces = [tuple(reversed(range(n)))]
    for ring in range(len(part["rings"]) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((ring * n + i, ring * n + j, (ring + 1) * n + j, (ring + 1) * n + i))
    start = (len(part["rings"]) - 1) * n
    faces.append(tuple(range(start, start + n)))
    return polyhedron(points, faces, colour, company)


def windows(part, colour, company):
    result = []
    for col in part["columns"]:
        for row in part["rows"]:
            w, h = part["size"]
            plane = part["plane"]
            if part["face"] == "x":
                lo, hi = [plane - 0.03, col, row], [plane + 0.03, col + w, row + h]
            elif part["face"] == "y":
                lo, hi = [col, plane - 0.03, row], [col + w, plane + 0.03, row + h]
            else:
                raise ValueError("Invalid window face")
            result.extend(box({"shape": "box", "min": lo, "max": hi}, colour, company))
    return result


def compile_pack(path):
    pack = json.loads(path.read_text())
    if pack["format"] != 1 or pack["license"] != "GPL-2.0-only":
        raise ValueError("Unsupported pack format or license")
    result = {}
    for model in pack["models"]:
        name = model["name"]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in result:
            raise ValueError(f"Invalid or duplicate model name: {name}")
        if model["status"] != "placeholder" and not model["references"]:
            raise ValueError(f"Missing artwork reference: {name}")
        vertices = []
        for part in model["parts"]:
            colour = pack["materials"][part["material"]]
            if len(colour) != 3 or any(not 0 <= c <= 1 for c in colour):
                raise ValueError("Invalid material colour")
            operation = {"box": box, "roof": box, "loft": loft, "windows": windows}.get(part["shape"])
            if operation is None:
                raise ValueError(f"Unsupported modelling operation: {part['shape']}")
            vertices.extend(operation(part, colour, part["material"] == "company"))
        if not vertices or any(not math.isfinite(n) for v in vertices for n in v):
            raise ValueError(f"Empty or invalid model: {name}")
        result[name] = vertices
    return result


def write_header(models, destination):
    lines = ["/* Generated from authored assets/3d/models.json. GPL-2.0-only. */", "#pragma once", '#include "geometry.hpp"', "namespace Renderer3D {"]
    f = lambda n: f"{n:.7f}f"
    for name, vertices in models.items():
        lines.append(f"inline constexpr Vertex mesh_{name}[] = {{")
        for v in vertices:
            lines.append("\t{{" + ", ".join(map(f, v[:3])) + "}, {" + ", ".join(map(f, v[3:6])) + "}, {" + ", ".join(map(f, v[6:9])) + "}, " + f(v[9]) + "},")
        lines.append("};")
    lines.append("inline constexpr Model authored_models[] = {")
    lines.extend(f'\t{{"{name}", mesh_{name}}},' for name in models)
    lines.extend(["};", "}", ""])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines))


def write_gltf(models, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name, vertices in models.items():
        # glTF is Y-up. Rotate the authored Z-up coordinates, preserving handedness.
        data = b"".join(struct.pack("<9f", v[0], v[2], -v[1], v[3], v[5], -v[4], *v[6:9]) for v in vertices)
        positions = [(v[0], v[2], -v[1]) for v in vertices]
        low = [min(v[i] for v in positions) for i in range(3)]
        high = [max(v[i] for v in positions) for i in range(3)]
        gltf = {
            "asset": {"version": "2.0", "generator": "OpenTT3D authored model compiler"},
            "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": name}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "COLOR_0": 2}, "material": 0}]}],
            "materials": [{"pbrMetallicRoughness": {"metallicFactor": 0, "roughnessFactor": 1}}],
            "buffers": [{"uri": "data:application/octet-stream;base64," + base64.b64encode(data).decode(), "byteLength": len(data)}],
            "bufferViews": [{"buffer": 0, "byteLength": len(data), "byteStride": 36, "target": 34962}],
            "accessors": [
                {"bufferView": 0, "byteOffset": 0, "componentType": 5126, "count": len(vertices), "type": "VEC3", "min": low, "max": high},
                {"bufferView": 0, "byteOffset": 12, "componentType": 5126, "count": len(vertices), "type": "VEC3"},
                {"bufferView": 0, "byteOffset": 24, "componentType": 5126, "count": len(vertices), "type": "VEC3"},
            ],
        }
        (destination / f"{name}.gltf").write_text(json.dumps(gltf, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--header", type=Path)
    parser.add_argument("--gltf", type=Path)
    args = parser.parse_args()
    models = compile_pack(args.source)
    if args.header:
        write_header(models, args.header)
    if args.gltf:
        write_gltf(models, args.gltf)
    for name, vertices in models.items():
        print(f"{name}: {len(vertices) // 3} triangles")


if __name__ == "__main__":
    main()

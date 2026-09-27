#!/usr/bin/env python3
"""Compile explicitly authored voxel operations to bounded material-cell runs.

No geometry is inferred from images. Palette indices and cell coordinates are
editable authoring data; source-image inspection is a separate review step.
"""
import argparse
from array import array
import json
import math
from fractions import Fraction
from pathlib import Path
import re


def integer(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"Invalid {label}: {value}")
    return value


def vector(value, label, integer_only=False):
    if not isinstance(value, list) or len(value) != 3 or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        or (integer_only and not isinstance(v, int)) for v in value
    ):
        raise ValueError(f"Invalid {label}: {value}")
    return value


def grain_value(x, y, z, seed):
    value = (x*0x9e3779b9 ^ y*0x85ebca6b ^ z*0xc2b2ae35 ^ seed) & 0xffffffff
    value ^= value >> 16
    value = (value * 0x7feb352d) & 0xffffffff
    return value ^ (value >> 15)


def compile_catalogue(data):
    if data.get("format") != 1 or not isinstance(data.get("models"), dict):
        raise ValueError("Invalid voxel source format")
    names, materials = {}, []
    for name, colours in data.get("materials", {}).items():
        colours = [colours] * 6 if isinstance(colours, int) else colours
        if not isinstance(colours, list) or len(colours) != 6:
            raise ValueError(f"Material {name} needs one or six palette colours")
        materials.append([integer(c, 1, 255, "palette colour") for c in colours])
        names[name] = len(materials)
    if not materials or len(materials) > 65535:
        raise ValueError("Invalid voxel material count")
    mixed_materials = {tuple(colours): index+1 for index, colours in enumerate(materials)}

    def face_material(colours):
        key = tuple(colours)
        if key not in mixed_materials:
            if len(materials) >= 65535:
                raise ValueError("Voxel face painting exceeds the material budget")
            materials.append(list(colours))
            mixed_materials[key] = len(materials)
        return mixed_materials[key]
    components = data.get("components", {})
    if not isinstance(components, dict) or any(not isinstance(name, str) or
            not re.fullmatch(r"[a-z][a-z0-9_]{0,95}", name) or not isinstance(ops, list)
            for name, ops in components.items()):
        raise ValueError("Invalid voxel component definitions")
    compiled, volumes, active = {}, {}, set()

    def compile_model(name):
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,95}", name):
            raise ValueError(f"Invalid voxel model name {name}")
        if name in compiled:
            return
        if name not in data["models"] or name in active:
            raise ValueError(f"Missing or cyclic voxel model {name}")
        active.add(name)
        source = data["models"][name]
        parent = source.get("extends")
        if parent:
            compile_model(parent)
        base = compiled[parent] if parent else {}
        size = vector(source.get("size", base.get("size")), "grid size", True)
        for extent in size:
            integer(extent, 1, 1024, "grid extent")
        if math.prod(size) > 16 * 1024 * 1024:
            raise ValueError("Voxel grid exceeds its cell budget")
        origin = vector(source.get("origin", base.get("origin", [0, 0, 0])), "grid origin")
        cell_size = vector(source.get("cell_size", base.get("cell_size", [0.5, 0.5, 1])), "cell size")
        if any(not 0 < value <= 16 for value in cell_size):
            raise ValueError("Invalid voxel cell size")
        if parent and size != base["size"]:
            raise ValueError("An inherited grid cannot change dimensions")
        if parent and cell_size != base["cell_size"]:
            raise ValueError("An inherited grid cannot change cell size")
        cells = array("H", volumes[parent]) if parent else array("H", [0]) * math.prod(size)
        expanded_ops = 0
        transform_work = 0
        component_stack = set()

        def apply(ops, offset=(0, 0, 0), depth=0, target=None):
            nonlocal expanded_ops, transform_work
            if target is None:
                target = cells
            if depth > 16 or not isinstance(ops, list):
                raise ValueError("Invalid/deep voxel operation list")
            for op in ops:
                expanded_ops += 1
                if expanded_ops > 100000 or not isinstance(op, list) or not op:
                    raise ValueError("Invalid/excessive voxel operations")
                kind = op[0]
                if kind in ("erase_material", "replace_material"):
                    if len(op) != (2 if kind == "erase_material" else 3) or op[1] not in names or (kind == "replace_material" and op[2] not in names):
                        raise ValueError("Material replacement/erasure needs known materials")
                    material = names[op[1]]
                    replacement = 0 if kind == "erase_material" else names[op[2]]
                    for index, value in enumerate(target):
                        if value == material:
                            target[index] = replacement
                    continue
                if kind == "use":
                    if len(op) not in (2, 3) or not isinstance(op[1], str) or op[1] not in components or op[1] in component_stack:
                        raise ValueError("Missing or cyclic voxel component")
                    delta = vector(op[2], "component offset", True) if len(op) == 3 else (0, 0, 0)
                    component_stack.add(op[1])
                    apply(components[op[1]], tuple(offset[d]+delta[d] for d in range(3)), depth+1, target)
                    component_stack.remove(op[1])
                    continue
                if kind == "rotate_z":
                    if len(op) != 4 or isinstance(op[1], bool) or not isinstance(op[1], (int, float)) or not math.isfinite(op[1]) or not -360 <= op[1] <= 360:
                        raise ValueError("Rotation needs a finite angle, pivot and component operations")
                    if cell_size[0] != cell_size[1]:
                        raise ValueError("Z rotations require equal horizontal cell sizes")
                    pivot = vector(op[2], "rotation pivot")
                    px, py = pivot[0]+offset[0], pivot[1]+offset[1]
                    cs, sn = math.cos(math.radians(op[1])), math.sin(math.radians(op[1]))
                    source_cells = array("H", [0]) * len(cells)
                    apply(op[3], offset, depth+1, source_cells)
                    nearest = array("f", [math.inf]) * len(cells)
                    radius = 0.5*(abs(cs)+abs(sn))
                    limit = radius+0.5-1e-7
                    for index, material in enumerate(source_cells):
                        if material == 0:
                            continue
                        x, yz = index % size[0], index // size[0]
                        y, z = yz % size[1], yz // size[1]
                        sx, sy = x+0.5-px, y+0.5-py
                        cx, cy = px+sx*cs-sy*sn, py+sx*sn+sy*cs
                        for ty in range(math.floor(cy-radius+1e-7), math.ceil(cy+radius-1e-7)):
                            for tx in range(math.floor(cx-radius+1e-7), math.ceil(cx+radius-1e-7)):
                                transform_work += 1
                                if transform_work > 16*1024*1024:
                                    raise ValueError("Voxel transforms exceed their cell budget")
                                dx, dy = tx+0.5-cx, ty+0.5-cy
                                # Positive-area square intersections keep thin rotated
                                # parts face-connected. Touching neighbours are excluded.
                                if max(abs(dx), abs(dy), abs(dx*cs+dy*sn), abs(-dx*sn+dy*cs)) >= limit:
                                    continue
                                if not 0 <= tx < size[0] or not 0 <= ty < size[1]:
                                    raise ValueError(f"Rotated component is outside {name}")
                                destination = (z*size[1]+ty)*size[0]+tx
                                distance = dx*dx+dy*dy
                                if distance+1e-6 < nearest[destination]:
                                    nearest[destination] = distance
                                    target[destination] = material
                    continue
                if kind == "repeat":
                    if len(op) != 4:
                        raise ValueError("Repeat needs a delta, count and operation list")
                    delta = vector(op[1], "repeat delta", True)
                    for i in range(integer(op[2], 1, 1024, "repeat count")):
                        apply(op[3], tuple(offset[d] + delta[d] * i for d in range(3)), depth + 1, target)
                    continue
                if kind == "prism":
                    # Explicit integer outline, extruded on one stated axis.
                    # Rational cell-centre scan conversion is winding independent;
                    # no source image or floating-point edge tolerance is involved.
                    if len(op) != 6 or op[1] not in names or not isinstance(op[5],list) or not 3 <= len(op[5]) <= 128:
                        raise ValueError("Prism needs a material, axis, extent and simple integer outline")
                    axis = integer(op[2],0,2,"prism axis")
                    low,high = (integer(v,-1024,1024,"prism extent")+offset[axis] for v in op[3:5])
                    if not 0 <= low < high <= size[axis]:
                        raise ValueError(f"Prism extent is outside {name}")
                    plane = [d for d in range(3) if d != axis]
                    points = []
                    for pair in op[5]:
                        if not isinstance(pair,list) or len(pair) != 2:
                            raise ValueError("Prism outline needs coordinate pairs")
                        point = tuple(integer(v,-1024,1024,"prism coordinate")+offset[d] for v,d in zip(pair,plane))
                        if any(not 0 <= point[i] <= size[d] for i,d in enumerate(plane)):
                            raise ValueError(f"Prism outline is outside {name}")
                        points.append(point)
                    edges = list(zip(points,points[1:]+points[:1]))
                    if any(a == b for a,b in edges) or sum(a[0]*b[1]-b[0]*a[1] for a,b in edges) == 0:
                        raise ValueError("Prism outline has a degenerate edge or area")
                    def side(a,b,c):
                        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                    for i,(a,b) in enumerate(edges):
                        for j,(c,d) in enumerate(edges[i+1:],i+1):
                            if j == i+1 or (i == 0 and j == len(edges)-1):
                                continue
                            if (all(max(min(a[k],b[k]),min(c[k],d[k])) <= min(max(a[k],b[k]),max(c[k],d[k])) for k in (0,1)) and
                                side(a,b,c)*side(a,b,d) <= 0 and side(c,d,a)*side(c,d,b) <= 0):
                                raise ValueError("Prism outline crosses or touches itself")
                    material = names[op[1]]
                    for v in range(min(p[1] for p in points),max(p[1] for p in points)):
                        crossings = []
                        for a,b in edges:
                            if a[1] > b[1]:
                                a,b = b,a
                            if not 2*a[1] <= 2*v+1 < 2*b[1]:
                                continue
                            dy = b[1]-a[1]
                            crossings.append(Fraction(2*a[0]*dy+(2*v+1-2*a[1])*(b[0]-a[0]),2*dy))
                        crossings.sort()
                        for left,right in zip(crossings[::2],crossings[1::2]):
                            start,end = math.ceil(left-Fraction(1,2)),math.ceil(right-Fraction(1,2))
                            transform_work += (end-start)*(high-low)
                            if transform_work > 16*1024*1024:
                                raise ValueError("Voxel transforms exceed their cell budget")
                            for u in range(start,end):
                                point = [0,0,0]
                                point[plane[0]],point[plane[1]] = u,v
                                for cell_depth in range(low,high):
                                    point[axis] = cell_depth
                                    x,y,z = point
                                    target[(z*size[1]+y)*size[0]+x] = material
                    continue
                if kind == "hull":
                    # Explicit transverse sections of a flared/chined hull. Each
                    # knot is [x, lower half-beam, upper half-beam, keel, deck].
                    # Optional deck paint changes only top faces inside a stated rim.
                    if len(op) not in (4,6) or op[1] not in names:
                        raise ValueError("Hull needs a material, centre line and section profile")
                    _, cy, _ = vector([0,op[2],0], "hull centre")
                    cy += offset[1]
                    if not isinstance(op[3],list) or not 2 <= len(op[3]) <= 1025:
                        raise ValueError("Hull needs two or more bounded section knots")
                    deck_material, rim = None, 0
                    if len(op) == 6:
                        if op[4] not in names:
                            raise ValueError("Hull deck needs a known material")
                        deck_material = names[op[4]]
                        rim = integer(op[5],0,32,"hull deck rim")
                    profile = []
                    for knot in op[3]:
                        if not isinstance(knot,list) or len(knot) != 5 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in knot):
                            raise ValueError("Hull sections need five finite coordinates")
                        x, lower, upper, keel, deck = knot
                        integer(x,0,size[0],"hull section position")
                        x += offset[0]
                        keel += offset[2]
                        deck += offset[2]
                        if not 0 <= x <= size[0] or not 0 <= lower <= 512 or not 0 < upper <= 512 or not 0 <= keel < deck <= size[2] or (profile and x <= profile[-1][0]):
                            raise ValueError("Hull sections must increase with valid beams and vertical bounds")
                        radius = max(lower,upper)
                        if cy-radius < -1e-7 or cy+radius > size[1]+1e-7:
                            raise ValueError(f"Hull is outside {name}")
                        profile.append((x,lower,upper,keel,deck))
                    for first,last in zip(profile,profile[1:]):
                        for x in range(first[0],last[0]):
                            t = (x+0.5-first[0])/(last[0]-first[0])
                            lower,upper,keel,deck = (first[i]+t*(last[i]-first[i]) for i in range(1,5))
                            radius = max(lower,upper)
                            ymin,ymax = max(0,math.floor(cy-radius)),min(size[1],math.ceil(cy+radius))
                            zmin,zmax = max(0,math.floor(keel)),min(size[2],math.ceil(deck))
                            transform_work += (ymax-ymin)*(zmax-zmin)
                            if transform_work > 16*1024*1024:
                                raise ValueError("Voxel transforms exceed their cell budget")
                            for z in range(zmin,zmax):
                                if not keel <= z+0.5 < deck:
                                    continue
                                beam = lower+(upper-lower)*(z+0.5-keel)/(deck-keel)
                                for y in range(ymin,ymax):
                                    if abs(y+0.5-cy) >= beam:
                                        continue
                                    material = names[op[1]]
                                    if deck_material is not None and z+1.5 >= deck and profile[0][0]+rim <= x < profile[-1][0]-rim and abs(y+0.5-cy) < beam-rim:
                                        colours = list(materials[material-1])
                                        colours[5] = materials[deck_material-1][5]
                                        material = face_material(colours)
                                    target[(z*size[1]+y)*size[0]+x] = material
                    continue
                if kind in ("radial_paint", "radial_erase"):
                    # Authored angular panels on existing volume cells. This is
                    # independent of source images and never fills empty space.
                    painting = kind == "radial_paint"
                    if (painting and (len(op) not in (7,8) or op[1] not in names)) or (not painting and len(op) not in (6,7)):
                        raise ValueError("Radial brush needs a centre, height range, sector count and mask")
                    values = op[2:] if painting else op[1:]
                    if not isinstance(values[0],list) or len(values[0]) != 2:
                        raise ValueError("Radial brush needs an XY centre")
                    cx,cy,_ = vector([*values[0],0],"radial centre")
                    cx += offset[0]; cy += offset[1]
                    low = integer(values[1],-1024,1024,"radial lower height")+offset[2]
                    high = integer(values[2],-1024,1024,"radial upper height")+offset[2]
                    sectors = integer(values[3],1,32,"radial sectors")
                    mask = integer(values[4],0,(1 << sectors)-1,"radial sector mask")
                    if high <= low or (not painting and len(values) == 6 and values[5] not in names):
                        raise ValueError("Invalid radial brush height or material filter")
                    only = names[values[5]] if not painting and len(values) == 6 else None
                    phase, twist = 0, 0
                    if painting and len(values) == 6:
                        # An authored angular phase and degrees per radial cell
                        # paint spiral bands without changing the occupied volume.
                        curve = values[5]
                        if not isinstance(curve,list) or len(curve) != 2 or any(
                            isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)
                            or not -360 <= value <= 360 for value in curve
                        ):
                            raise ValueError("Radial paint curve needs finite phase and twist angles in -360..360")
                        phase,twist = map(math.radians,curve)
                    material = names[op[1]] if painting else 0
                    zmin,zmax = max(0,low),min(size[2],high)
                    transform_work += size[0]*size[1]*max(0,zmax-zmin)
                    if transform_work > 16*1024*1024:
                        raise ValueError("Voxel transforms exceed their cell budget")
                    for y in range(size[1]):
                        for x in range(size[0]):
                            angle = math.atan2(y+0.5-cy,x+0.5-cx) % math.tau
                            if phase or twist:
                                angle = (angle+phase+twist*math.hypot(x+0.5-cx,y+0.5-cy)) % math.tau
                            sector = math.floor(angle*sectors/math.tau+1e-12) % sectors
                            if not mask & (1 << sector):
                                continue
                            for z in range(zmin,zmax):
                                index = (z*size[1]+y)*size[0]+x
                                if target[index] and (only is None or target[index] == only):
                                    target[index] = material
                    continue
                if kind in ("lathe", "lathe_paint_inner"):
                    # Explicit radial sections, not a sampled picture/height map.
                    # Each knot is [height, outer radius, inner radius]; an optional
                    # authored XY scale/angle also permits oblique oval footprints.
                    if len(op) not in ((4, 5, 6) if kind == "lathe_paint_inner" else (4, 5)) or op[1] not in names or not isinstance(op[2], list) or len(op[2]) != 2:
                        raise ValueError("Lathe needs a material, XY centre and radius profile")
                    if cell_size[0] != cell_size[1]:
                        raise ValueError("Lathe requires equal horizontal cell sizes")
                    cx, cy, _ = vector([*op[2], 0], "lathe centre")
                    cx += offset[0]
                    cy += offset[1]
                    sx, sy, angle = vector(op[4] if len(op) >= 5 else [1, 1, 0], "lathe transform")
                    if not 0 < sx <= 16 or not 0 < sy <= 16 or not -360 <= angle <= 360:
                        raise ValueError("Invalid lathe transform")
                    frequency, seed = 1, 0
                    if len(op) == 6:
                        if not isinstance(op[5], list) or len(op[5]) != 2:
                            raise ValueError("Inner-face grain needs frequency and seed")
                        frequency = integer(op[5][0], 1, 1024, "inner-face grain frequency")
                        seed = integer(op[5][1], 0, 0xffffffff, "inner-face grain seed")
                    if not isinstance(op[3], list) or not 2 <= len(op[3]) <= 1025:
                        raise ValueError("Lathe needs two or more bounded profile knots")
                    profile = []
                    for knot in op[3]:
                        z, outer, inner = vector(knot, "lathe profile knot")
                        integer(z, 0, size[2], "lathe profile height")
                        z += offset[2]
                        if not 0 <= z <= size[2] or not 0 <= inner < outer <= 1024 or (profile and z <= profile[-1][0]):
                            raise ValueError("Lathe profile must increase in height with valid inner/outer radii")
                        profile.append((z, outer, inner))
                    cs, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                    radius = max(knot[1] for knot in profile)
                    rx = radius*math.hypot(sx*cs, sy*sn)
                    ry = radius*math.hypot(sx*sn, sy*cs)
                    if cx-rx < -1e-7 or cy-ry < -1e-7 or cx+rx > size[0]+1e-7 or cy+ry > size[1]+1e-7:
                        raise ValueError(f"Lathe is outside {name}")
                    bounds = (max(0, math.floor(cx-rx)), min(size[0], math.ceil(cx+rx)),
                              max(0, math.floor(cy-ry)), min(size[1], math.ceil(cy+ry)))
                    transform_work += (1 if kind == "lathe" else 7)*(bounds[1]-bounds[0])*(bounds[3]-bounds[2])*(profile[-1][0]-profile[0][0])
                    if transform_work > 16*1024*1024:
                        raise ValueError("Voxel transforms exceed their cell budget")
                    radii = {}
                    for first, last in zip(profile, profile[1:]):
                        for z in range(first[0], last[0]):
                            fraction = (z+0.5-first[0])/(last[0]-first[0])
                            radii[z] = (first[1]+fraction*(last[1]-first[1]), first[2]+fraction*(last[2]-first[2]))
                    def radial_squared(x, y):
                        dx, dy = x+0.5-cx, y+0.5-cy
                        return ((dx*cs+dy*sn)/sx)**2 + ((-dx*sn+dy*cs)/sy)**2
                    for z, (outer, inner) in radii.items():
                        for y in range(bounds[2], bounds[3]):
                            for x in range(bounds[0], bounds[1]):
                                if frequency > 1 and grain_value(x,y,z,seed) % frequency != 0:
                                    continue
                                r2 = radial_squared(x,y)
                                if inner*inner <= r2 < outer*outer:
                                    index = (z*size[1]+y)*size[0]+x
                                    if kind == "lathe":
                                        target[index] = names[op[1]]
                                    elif target[index]:
                                        # Recolour only faces bordering the authored
                                        # inner air column. Painting whole thin wall
                                        # cells leaks dark lining onto exterior steps.
                                        original = materials[target[index]-1]
                                        colours = list(original)
                                        lining = materials[names[op[1]]-1]
                                        for face, (dx,dy,dz) in enumerate(((-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1))):
                                            neighbour = radii.get(z+dz)
                                            if neighbour and radial_squared(x+dx,y+dy) < neighbour[1]*neighbour[1]:
                                                colours[face] = lining[face]
                                        if colours != original:
                                            target[index] = face_material(colours)
                    continue
                if kind == "line":
                    if len(op) != 8 or op[1] not in names:
                        raise ValueError("A voxel line needs a material and two cell endpoints")
                    first = vector(op[2:5], "line start", True)
                    last = vector(op[5:8], "line end", True)
                    first = tuple(first[d]+offset[d] for d in range(3))
                    last = tuple(last[d]+offset[d] for d in range(3))
                    if any(not 0 <= point[d] < size[d] for point in (first,last) for d in range(3)):
                        raise ValueError(f"Voxel line is outside {name}")
                    # Canonical direction resolves simultaneous cell crossings the
                    # same way for reversed endpoints. Single-axis steps keep thin
                    # authored wires face-connected instead of touching at corners.
                    if last < first:
                        first, last = last, first
                    delta = [abs(last[d]-first[d]) for d in range(3)]
                    direction = [1 if last[d] > first[d] else -1 for d in range(3)]
                    transform_work += sum(delta)+1
                    if transform_work > 16*1024*1024:
                        raise ValueError("Voxel transforms exceed their cell budget")
                    point, steps = list(first), [0,0,0]
                    while True:
                        target[(point[2]*size[1]+point[1])*size[0]+point[0]] = names[op[1]]
                        if tuple(point) == last:
                            break
                        axis = min((d for d in range(3) if steps[d] < delta[d]),
                                   key=lambda d: (2*steps[d]+1)/delta[d])
                        point[axis] += direction[axis]
                        steps[axis] += 1
                    continue
                erase = kind == "erase"
                scatter = kind == "scatter_paint"
                face_paint = kind == "face_paint"
                expected = 7 if erase else 10 if scatter else 9 if face_paint or kind in ("gable", "hip", "barrel", "barrel_fill") else 8
                if scatter and len(op) in (11, 12):
                    expected = len(op)
                if kind not in ("box", "paint", "face_paint", "erase", "gable", "hip", "barrel", "barrel_fill", "ellipsoid", "ellipsoid_paint", "mound", "scatter_paint") or len(op) != expected:
                    raise ValueError(f"Invalid voxel operation {op}")
                if not erase and op[1] not in names:
                    raise ValueError(f"Unknown voxel material {op[1]}")
                material = 0 if erase else names[op[1]]
                if face_paint:
                    face_mask = integer(op[2], 1, 63, "paint face mask")
                if scatter:
                    frequency = integer(op[2], 1, 1024, "scatter frequency")
                    seed = integer(op[3], 0, 0xffffffff, "scatter seed")
                    if len(op) >= 11 and (not isinstance(op[10], str) or op[10] not in names):
                        raise ValueError("Scatter material mask needs a known material")
                    only_material = names[op[10]] if len(op) >= 11 else None
                    block = vector(op[11], "scatter colour block", True) if len(op) == 12 else (1, 1, 1)
                    for extent in block:
                        integer(extent, 1, 1024, "scatter colour block extent")
                bounds = op[1:7] if erase else op[4:10] if scatter else op[3:9] if face_paint else op[2:8]
                for coordinate in bounds:
                    integer(coordinate, -1024, 2048, "cell coordinate")
                low = [bounds[d] + offset[d] for d in range(3)]
                high = [bounds[d+3] + offset[d] for d in range(3)]
                if any(not 0 <= low[d] < high[d] <= size[d] for d in range(3)):
                    raise ValueError(f"Voxel operation is outside {name}: {op}")
                if kind in ("gable", "barrel", "barrel_fill") and op[8] not in ("x", "y"):
                    raise ValueError("Roof profile axis must be x or y")
                if kind == "hip":
                    integer(op[8], 0, (min(high[0]-low[0], high[1]-low[1])-1)//2, "hip inset")
                if kind in ("barrel", "barrel_fill"):
                    axis = 0 if op[8] == "x" else 1
                    other = 1-axis
                    width = high[axis]-low[axis]
                    if width < 3:
                        raise ValueError("Barrel roof needs at least three columns")
                    tops = [low[2]+1+round((high[2]-low[2]-1)*math.sqrt(max(0, 1-(2*i/(width-1)-1)**2))) for i in range(width)]
                    for i, top in enumerate(tops):
                        bottom = low[2] if kind == "barrel_fill" else max(low[2], min(tops[max(0,i-1):min(width,i+2)])-1)
                        for span in range(low[other], high[other]):
                            p = [0, 0]
                            p[axis], p[other] = low[axis]+i, span
                            for z in range(bottom, top):
                                target[(z*size[1]+p[1])*size[0]+p[0]] = material
                    continue
                for z in range(low[2], high[2]):
                    a, b = low[:2], high[:2]
                    if kind == "gable":
                        axis = 0 if op[8] == "x" else 1
                        inset = (z-low[2]) * ((high[axis]-low[axis]-1)//2) // max(1, high[2]-low[2]-1)
                        a[axis] += inset
                        b[axis] -= inset
                    elif kind == "hip":
                        inset = (z-low[2]) * op[8] // max(1, high[2]-low[2]-1)
                        a = [p+inset for p in a]
                        b = [p-inset for p in b]
                    for y in range(a[1], b[1]):
                        start = (z*size[1]+y)*size[0]
                        if kind in ("ellipsoid", "ellipsoid_paint", "mound"):
                            for x in range(a[0], b[0]):
                                if kind == "ellipsoid_paint" and not target[start+x]:
                                    continue
                                if kind == "mound":
                                    # An explicitly bounded elliptical cone, filled
                                    # from its base: every occupied column is supported.
                                    radius = math.sqrt(sum(((2*p+1-low[d]-high[d])/(high[d]-low[d]))**2 for d,p in enumerate((x,y))))
                                    inside = radius + (z-low[2]+0.5)/(high[2]-low[2]) <= 1
                                else:
                                    inside = sum(((2*p+1-low[d]-high[d])/(high[d]-low[d]))**2 for d,p in enumerate((x,y,z))) <= 1
                                if inside:
                                    target[start+x] = material
                        elif face_paint:
                            for x in range(a[0], b[0]):
                                if not target[start+x]:
                                    continue
                                colours = list(materials[target[start+x]-1])
                                for face in range(6):
                                    if face_mask & (1 << face):
                                        colours[face] = materials[material-1][face]
                                target[start+x] = face_material(colours)
                        elif kind == "paint" or scatter:
                            for x in range(a[0], b[0]):
                                if target[start+x] and (not scatter or only_material is None or target[start+x] == only_material):
                                    if scatter:
                                        value = grain_value(x//block[0], y//block[1], z//block[2], seed)
                                        if value % frequency:
                                            continue
                                    target[start+x] = material
                        else:
                            target[start+a[0]:start+b[0]] = array("H", [material]) * (b[0]-a[0])
        apply(source.get("ops", []))
        transpose = source.get("transpose_xy", False)
        if not isinstance(transpose, bool):
            raise ValueError("transpose_xy must be boolean")
        if transpose:
            changed = array("H", [0]) * len(cells)
            for z in range(size[2]):
                for y in range(size[1]):
                    for x in range(size[0]):
                        changed[(z*size[0]+x)*size[1]+y] = cells[(z*size[1]+y)*size[0]+x]
            cells = changed
            size = [size[1], size[0], size[2]]
        runs = []
        for z in range(size[2]):
            for y in range(size[1]):
                x = 0
                while x < size[0]:
                    material = cells[(z*size[1]+y)*size[0]+x]
                    end = x+1
                    while end < size[0] and cells[(z*size[1]+y)*size[0]+end] == material:
                        end += 1
                    if material:
                        runs.append([x, y, z, end-x, material])
                    x = end
        if not runs:
            raise ValueError(f"Empty voxel model {name}")
        compiled[name] = {"size": size, "origin": origin, "cell_size": cell_size, "runs": runs,
                          "occupied": sum(c != 0 for c in cells),
                          "review_status": source.get("review_status", "work-in-progress")}
        volumes[name] = cells
        active.remove(name)

    for name in data["models"]:
        compile_model(name)
    bindings = data.get("bindings", {})
    for category, identifiers in bindings.items():
        if category not in ("houses", "house_ground", "industries", "industry_ground", "vehicles", "vehicle_collectors", "trees", "airport_tiles", "airport_ground", "infrastructure", "depots", "depot_floors", "depot_wires", "ship_depots", "docks") or not isinstance(identifiers, dict):
            raise ValueError(f"Unknown voxel binding category {category}")
        for identifier, states in identifiers.items():
            if not identifier.isascii() or not identifier.isdecimal() or int(identifier) > 65535 or not isinstance(states, dict) or not states:
                raise ValueError("Voxel bindings need numeric identifiers and explicit states")
            for state, model in states.items():
                if not state.isascii() or not state.isdecimal() or int(state) > 65535 or model not in compiled:
                    raise ValueError(f"Invalid voxel binding {category}/{identifier}/{state}")
            if category == "vehicle_collectors" and (int(identifier) not in (23,24,25,26) or set(states) != ({"0","1"} if int(identifier) in (23,24) else {"0"})):
                raise ValueError("Original electric locomotives need their complete independently mounted collectors")
            if category in ("airport_tiles", "airport_ground") and (int(identifier) >= 74 or any(int(state) >= (64 if category == "airport_ground" else 16) for state in states)):
                raise ValueError("Airport bindings use original tile IDs, body frames0..15 and ground climate*16+frame states0..63")
            if category == "vehicles":
                if int(identifier) >= 256 or any(int(state) >= 8 for state in states):
                    raise ValueError("Vehicle bindings use original engine IDs and climate*2+cargo states0..7")
                for climate in range(4):
                    pair = {str(climate*2),str(climate*2+1)}
                    if pair & states.keys() and not pair <= states.keys():
                        raise ValueError("Vehicle climate bindings need both original empty/loaded states")
    return {"format": 1, "reference": data.get("reference"), "cell_size": [0.5, 0.5, 1],
            "materials": materials, "models": compiled, "bindings": bindings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compile_catalogue(json.loads(args.source.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    print(f"Compiled {len(result['models'])} authored voxel volumes; visual approval remains separate")


if __name__ == "__main__":
    main()

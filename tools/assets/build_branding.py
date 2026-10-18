#!/usr/bin/env python3
"""Build the OpenTT3D icon: an isometric orange cube with OPEN / TT3D ribbons."""
import argparse
import math
from pathlib import Path

SVG_HEADER = '''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <title>OpenTT3D - an orange cube with OPEN and TT3D ribbons</title>
  <metadata>OpenTT3D project artwork. SPDX-License-Identifier: GPL-2.0-only.</metadata>
'''
FONT = {
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
}
DOLLAR = ("0011100", "0100010", "0100000", "0011100", "0000010", "0100010", "0011100", "0001000", "0001000")


def polygon(points, fill):
    values = " ".join(f"{x:.3f},{y:.3f}" for x, y in points)
    return f'  <polygon points="{values}" fill="{fill}"/>\n'


def rotate(point, angle):
    c, s = math.cos(angle), math.sin(angle)
    x, y = point
    return x*c-y*s, x*s+y*c


def ribbon(cx, cy, angle, length, height, text, cell=2.15):
    out = []
    direction = (math.cos(angle), math.sin(angle))
    normal = (-math.sin(angle), math.cos(angle))
    def rect(along, across, width, tall):
        points = []
        for a, b in ((-width/2, -tall/2), (width/2, -tall/2), (width/2, tall/2), (-width/2, tall/2)):
            points.append((cx+direction[0]*(along+a)+normal[0]*(across+b),
                           cy+direction[1]*(along+a)+normal[1]*(across+b)))
        return points
    out.append(polygon(rect(0, 0, length+7, height+7), "#0f1519"))
    out.append(polygon(rect(0, 0, length, height), "#5fca2e"))
    # A darker inner edge makes the ribbon read as a printed cloth strip.
    out.append(polygon(rect(0, height/2-1.5, length, 3), "#3f9f1f"))
    out.append(polygon(rect(0, -height/2+1.5, length, 3), "#7fdf4a"))
    glyph_width, gap = 5*cell, cell
    total = len(text)*glyph_width + (len(text)-1)*gap
    start = -total/2
    for index, letter in enumerate(text):
        rows = FONT[letter]
        left = start + index*(glyph_width+gap)
        for row, bits in enumerate(rows):
            run = None
            for column in range(6):
                on = column < 5 and bits[column] == "1"
                if on and run is None:
                    run = column
                if (not on or column == 5) and run is not None:
                    end = column
                    along = left + run*cell - glyph_width/2
                    across = (row-3)*cell
                    out.append(polygon(rect(along+(end-run)*cell/2, across, (end-run)*cell, cell), "#0f1519"))
                    run = None
    return out


def face(origin, u, v):
    ox, oy = origin
    return lambda x, y: (ox+u[0]*x+v[0]*y, oy+u[1]*x+v[1]*y)


def build_svg():
    shapes = []
    # Black silhouette: the cube reads as solid even on a light page.
    shapes.append(polygon([(128,22),(222,72),(222,174),(128,224),(34,174),(34,72)],"#0f1519"))
    shapes.append(polygon([(128,38),(208,82),(128,126),(48,82)],"#ffb24a"))
    shapes.append(polygon([(48,82),(128,126),(128,210),(48,166)],"#ee7410"))
    shapes.append(polygon([(128,126),(208,82),(208,166),(128,210)],"#bd4705"))
    # Bevel highlights.
    shapes.append(polygon([(54,84),(122,120),(122,132),(54,97)],"#ffc46a"))
    shapes.append(polygon([(134,128),(202,88),(202,98),(134,138)],"#df640c"))
    shapes.append(polygon([(54,156),(54,164),(124,204),(124,196)],"#c95a0a"))
    # White dollar sign is painted on the right face.
    point = face((128,126),(80,-42),(0,78))
    left, right, top, bottom = 0.06, 0.94, 0.03, 0.97
    cell_w, cell_h = (right-left)/7, (bottom-top)/len(DOLLAR)
    for row, bits in enumerate(DOLLAR):
        run = None
        for column in range(8):
            on = column < 7 and bits[column] == "1"
            if on and run is None:
                run = column
            if (not on or column == 7) and run is not None:
                end = column
                x0, x1 = left+run*cell_w, left+end*cell_w
                y0, y1 = top+row*cell_h, top+(row+1)*cell_h
                shapes.append(polygon([point(x0,y0),point(x1,y0),point(x1,y1),point(x0,y1)],"#fff4d6"))
                run = None
    # Two green ribbons, as close as possible to the classic OPEN/TTD layout.
    shapes.extend(ribbon(60,205,-0.66,112,27,"OPEN"))
    shapes.extend(ribbon(196,205,0.66,112,27,"TT3D"))
    return SVG_HEADER + "".join(shapes) + "</svg>\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    args.svg.write_text(build_svg())
    if args.output:
        import subprocess, sys
        subprocess.run([sys.executable,str(Path(__file__).with_name("compile_branding.py")),
                        str(args.svg),str(args.output)],check=True)


if __name__ == "__main__":
    main()

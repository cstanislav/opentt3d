#!/usr/bin/env python3
"""Rasterize the small authored SVG subset into desktop application icon formats.

Run in the art container (Pillow). Generated icons are distributed with source,
so normal game builds do not depend on an SVG or image-processing installation.
"""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

GLYPHS = {
    "O": (14, 17, 17, 17, 17, 17, 14), "P": (30, 17, 17, 30, 16, 16, 16),
    "E": (31, 16, 16, 30, 16, 16, 31), "N": (17, 25, 25, 21, 19, 19, 17),
    "T": (31, 4, 4, 4, 4, 4, 4), "3": (30, 1, 1, 14, 1, 1, 30),
    "D": (30, 17, 17, 17, 17, 17, 30),
}


def wordmark(image, x, y, pixel):
    draw = ImageDraw.Draw(image)
    for column, letter in enumerate("OPENTT3D"):
        for row, bits in enumerate(GLYPHS[letter]):
            for bit in range(5):
                if bits & (1 << (4 - bit)):
                    left, top = x + (column * 6 + bit) * pixel, y + row * pixel
                    draw.rectangle((left, top, left + pixel - 1, top + pixel - 1), fill="#ffc84e" if column >= 6 else "#eaf3f5")


def render(source):
    image = Image.new("RGBA", (1024, 1024))
    draw = ImageDraw.Draw(image)
    scale = 4
    for element in ET.parse(source).getroot().iter():
        kind = element.tag.rsplit("}", 1)[-1]
        fill = element.get("fill")
        if kind == "rect":
            x, y, w, h = (float(element.get(k, "0")) * scale for k in ("x", "y", "width", "height"))
            draw.rounded_rectangle((x, y, x + w, y + h), radius=float(element.get("rx", "0")) * scale, fill=fill)
        elif kind == "polygon":
            points = [tuple(float(v) * scale for v in point.split(",")) for point in element.get("points").split()]
            draw.polygon(points, fill=fill)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    image = render(args.source)
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        image.resize((size, size), Image.Resampling.LANCZOS).save(args.output / f"opentt3d-{size}.png")
    image.save(args.output / "opentt3d.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    image.save(args.output / "opentt3d.icns")
    welcome = Image.new("RGB", (164, 314), "#142c40")
    icon = image.resize((144, 144), Image.Resampling.LANCZOS)
    welcome.paste(icon, (10, 45), icon)
    wordmark(welcome, 11, 220, 3)
    welcome.save(args.output / "installer-welcome.bmp")
    image.resize((64, 64), Image.Resampling.LANCZOS).convert("RGB").save(args.output / "installer-header.bmp")
    background = Image.new("RGB", (640, 420), "#142c40")
    wordmark(background, (640 - 47 * 6) // 2, 36, 6)
    background.save(args.output / "install-background.png")
    rgba = image.resize((32, 32), Image.Resampling.LANCZOS).tobytes()
    lines = ["/* Generated from assets/branding/opentt3d.svg; GPL-2.0-only. */", "#pragma once", "#include <array>",
             "inline constexpr std::array<unsigned char, 4096> _opentt3d_icon_rgba = {"]
    for offset in range(0, len(rgba), 32):
        lines.append("\t" + ",".join(str(value) for value in rgba[offset:offset + 32]) + ",")
    lines.append("};")
    (args.output / "opentt3d_icon.hpp").write_text("\n".join(lines) + "\n")
    print(f"Generated OpenTT3D PNG, ICO, ICNS and SDL icons in {args.output}")


if __name__ == "__main__":
    main()

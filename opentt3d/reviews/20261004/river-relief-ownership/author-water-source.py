"""Retain independent original water paint; author no geometry from sprite pixels.

Only source-layer relief paint is replaced in this diagnostic material. Every
visible original water component remains byte-exact. Hidden water comes from the
pinned Water Texture layer and its original exact DOS indices, not inpainting,
nearest-colour fitting, duplicate callbacks or the rendered phase's RGB values.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "river-relief-breadth"
RUN = ROOT / "build-macos/breadth-original-river-ownership-components-wide-{}-vulkan-on/renderer3d-reference"


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / "water-source-study"
    if target.exists(): raise ValueError("Retain the previous water material study")
    target.mkdir()
    tools_text = (ROOT / "build-opengfx2/graphics/tools.py").read_text()
    palette = next(ast.literal_eval(node.value) for node in ast.parse(tools_text).body
                   if isinstance(node,ast.Assign) and any(isinstance(value,ast.Name) and value.id == "openttd_palette" for value in node.targets))
    # Exact five-entry authored water cycle in the original source palette.
    water_indices = {tuple(palette[channel][index] for channel in ("r","g","b")):index for index in range(245,250)}
    assert len(water_indices) == 5
    (target / "pinned-upstream-tools.py").write_text(tools_text)
    layers = json.loads((HERE / "original-layer-index.json").read_text())
    rows = []
    for source in json.loads((PRIOR / "source-index.json").read_text()):
        climate = source["climate_name"]
        directory = Path(str(RUN).format(climate))
        selectors = json.loads((directory / "river-selectors.json").read_text())["observations"]
        actual = next(row for row in selectors if row["feature"] == "CF_RIVER_SLOPE" and row["slope"] == source["slope"] and
                      digest(directory / row["source_image"]) == source["sha256"])
        raw_path = directory / actual["source_components"]
        components = json.loads(raw_path.read_text())
        assert components["size"] == source["native_source_size"] and components["source_offset"] == source["source_offset"]
        assert components["zoom"] == 2 and components["palette"] == 0
        document = next(row for row in layers if row["source"].endswith(
            ("toyland" if source["climate"] == 3 else "universal")+"_rivertiles_32bpp.pdn"))
        relief_path = ROOT / next(row["image"] for row in document["layers"] if row["name"] == ("Rocks" if source["climate"] == 3 else "Rocks Unshaded"))
        texture_path = ROOT / next(row["image"] for row in document["layers"] if row["name"] == "Water Texture")
        shading_path = HERE / "original-layers/universal_rivertiles_cbt32bpp/01-shadingsource.png"
        with Image.open(relief_path) as relief, Image.open(texture_path) as water_texture, Image.open(shading_path) as shading:
            x0,y0 = {3:81,6:161,9:241,12:321}[source["slope"]],1
            expected,water,owners = [],[],[]
            visible_water = filled = 0
            for v in range(components["size"][1]):
                for u in range(components["size"][0]):
                    pixel = components["pixels"][v*components["size"][0]+u]
                    expected.append(pixel)
                    owner = 2 if relief.getpixel((x0+u,y0+v))[3] else 1 if pixel[3] else 0
                    owners.append(owner)
                    if owner == 2:
                        original = water_texture.getpixel((x0+u,y0+v))
                        assert original[3] == 255 and original[:3] in water_indices
                        neutral = shading.getpixel((x0+u,y0+v))
                        assert neutral[0] == neutral[1] == neutral[2]
                        water.append([*neutral[:4],water_indices[original[:3]]])
                        filled += 1
                    else:
                        water.append(pixel)
                        if owner == 1:
                            visible_water += 1
                            original = water_texture.getpixel((x0+u,y0+v))
                            if pixel[4] in range(245,250): assert pixel[4] == water_indices[original[:3]]
            assert all(a == b for a,b,owner in zip(expected,water,owners) if owner != 2)
            assert not any(pixel[3] and pixel[4] not in range(245,250) for pixel,owner in zip(water,owners) if owner == 2)
            label = climate+"-"+source["slope_name"].lower()
            mask = Image.new("L",tuple(components["size"])); mask.putdata(owners); mask.save(target / (label+"-ownership.png"))
            (target / (label+"-source-components.json")).write_bytes(raw_path.read_bytes())
            (target / (label+"-source.pam")).write_bytes((directory / actual["source_image"]).read_bytes())
            rows.append({"climate":source["climate"],"slope":source["slope"],"size":components["size"],
                "source_size":components["source_size"],"source_offset":components["source_offset"],"pixels":expected,"water_pixels":water,
                "source":source,"actual_selector":actual,"source_components_sha256":digest(raw_path),"owners":owners,
                "visible_original_water_pixels_exact":visible_water,"original_hidden_water_pixels_retained":filled,
                "hidden_water_inpainted":False,"remap_indices_inferred_from_phase_rgb":False,
                "water_layer":str(texture_path.relative_to(ROOT)),"water_layer_sha256":digest(texture_path),
                "relief_layer":str(relief_path.relative_to(ROOT)),"relief_layer_sha256":digest(relief_path),
                "original_shading_layer":str(shading_path.relative_to(ROOT)),"original_shading_layer_sha256":digest(shading_path),
                "geometry_approved":False})
    assert len(rows) == 8
    runtime = []
    for climate in range(4):
        for row in rows:
            if (row["climate"] == 3) != (climate == 3): continue
            runtime.append({key:(climate if key == "climate" else row[key]) for key in (
                "climate","slope","size","source_size","source_offset","pixels","water_pixels")})
    assert len(runtime) == 16
    (target / "authored-river-water.json").write_text(json.dumps({"format":1,"sources":runtime,
        "scope":"Diagnostic original-layer water/relief decomposition only. Original raw-source equality and complete actual Classic family are mandatory; no flat, alternate/custom, phase/ship, quality or performance acceptance."},separators=(",",":"))+"\n")
    (target / "source-material-index.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps({"original_slope_source_materials":8,"explicit_diagnostic_climates":16,
        "visible_original_water_pixels_exact":sum(row["visible_original_water_pixels_exact"] for row in rows),
        "original_hidden_water_pixels_retained":sum(row["original_hidden_water_pixels_retained"] for row in rows),
        "water_inpainted":False,"approvals":0}))


if __name__ == "__main__": main()

"""Use the entire original lower water stack, never only its five-entry base cycle.

The initial retained material omitted hidden anti-flicker and sparkle paint. It is
rejected and preserved. This companion uses the original visible layer order,
exact DOS source-palette matches and original neutral shading. No rendered-phase
RGB, colour fitting, geometry extraction or hole filling is used. Existing visible
runtime components (including upstream dither/border exceptions) remain exact.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COMMIT = "013cbc9e700c796af001a381a2d93592d49146ac"


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / "water-source-study-complete-layers"
    if target.exists(): raise ValueError("Retain previous material studies")
    target.mkdir()
    pinned_tools = subprocess.check_output(["git","show",COMMIT+":graphics/tools.py"],cwd=ROOT / "build-opengfx2")
    palette = next(ast.literal_eval(node.value) for node in ast.parse(pinned_tools).body
                   if isinstance(node,ast.Assign) and any(isinstance(value,ast.Name) and value.id == "openttd_palette" for value in node.targets))
    source_indices = {}
    for index in range(256): source_indices.setdefault(tuple(palette[channel][index] for channel in ("r","g","b")),[]).append(index)
    (target / "pinned-upstream-tools.py").write_bytes(pinned_tools)
    documents = json.loads((HERE / "original-layer-index.json").read_text())
    prior = json.loads((HERE / "water-source-study/source-material-index.json").read_text())
    rows,hidden_differences,hidden_indices = [],[],Counter()
    for row in prior:
        document = next(doc for doc in documents if doc["source"].endswith(
            ("/toyland" if row["climate"] == 3 else "/universal")+"_rivertiles_32bpp.pdn"))
        layers = [layer for layer in document["layers"] if layer["name"] in ("Water Texture","Anti-flickr","SparkleMask") and layer["visible"]]
        lower = Image.new("RGBA",tuple(document["size"]))
        for layer in layers:
            with Image.open(ROOT / layer["image"]) as image:
                assert set(image.getchannel("A").get_flattened_data()) <= {0,255}
                lower = Image.alpha_composite(lower,image)
        label = row["source"]["climate_name"]+"-"+row["source"]["slope_name"].lower()
        lower_path = target / (label+"-original-lower-stack.png"); lower.save(lower_path)
        x0 = {3:81,6:161,9:241,12:321}[row["slope"]]
        with Image.open(ROOT / row["original_shading_layer"]) as shading:
            water,changes = [],[]
            for i,(original,owner) in enumerate(zip(row["pixels"],row["owners"])):
                if owner != 2:
                    water.append(original)
                    continue
                xy = (x0+i%row["size"][0],1+i//row["size"][0])
                authored = lower.getpixel(xy)
                assert authored[3] == 255 and len(source_indices.get(authored[:3],[])) == 1
                index = source_indices[authored[:3]][0]
                neutral = shading.getpixel(xy)
                assert neutral[0] == neutral[1] == neutral[2] and neutral[3] == 255
                component = [*neutral,index]; water.append(component)
                hidden_indices[index] += 1
                if component != row["water_pixels"][i]: changes.append({"native_xy":[i%row["size"][0],i//row["size"][0]],
                    "rejected_components":row["water_pixels"][i],"complete_original_lower_components":component})
            assert all(a == b for a,b,owner in zip(row["pixels"],water,row["owners"]) if owner != 2)
        hidden_differences.append({"climate":row["climate"],"slope":row["slope"],"rejected_hidden_material_pixels":changes})
        value = dict(row,water_pixels=water,original_lower_layers=layers,original_lower_stack=str(lower_path.relative_to(ROOT)),
            original_lower_stack_sha256=digest(lower_path),hidden_water_inpainted=False,
            hidden_water_generation="Exact retained lower authoring layers and unique original DOS source-palette entries; not an assertion of unknowable hidden compiled dither bytes.",
            independent_phase_coverage=False,geometry_approved=False)
        rows.append(value)
    runtime = []
    for climate in range(4):
        for row in rows:
            if (row["climate"] == 3) != (climate == 3): continue
            runtime.append({key:(climate if key == "climate" else row[key]) for key in (
                "climate","slope","size","source_size","source_offset","pixels","water_pixels")})
    assert len(runtime) == 16
    (target / "authored-river-water.json").write_text(json.dumps({"format":1,"sources":runtime,
        "scope":"Diagnostic companion from the full original water layer stack. Visible actual runtime components are unchanged; hidden authored paint is retained, not an assertion of hidden compiled-dither bytes. Complete actual Classic raw-source equality is mandatory; no quality, phase/ship or performance approval."},separators=(",",":"))+"\n")
    (target / "source-material-index.json").write_text(json.dumps(rows,indent=2)+"\n")
    (target / "retained-initial-material-defects.json").write_text(json.dumps(hidden_differences,indent=2)+"\n")
    result = {"sources":8,"explicit_climate_sources":16,"hidden_original_layer_pixels":sum(hidden_indices.values()),
        "hidden_original_source_palette_indices":dict(sorted(hidden_indices.items())),
        "rejected_initial_hidden_pixels":sum(len(row["rejected_hidden_material_pixels"]) for row in hidden_differences),
        "visible_actual_runtime_pixels_changed":0,"independent_phase_coverage":False,"approvals":0}
    (target / "receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__": main()

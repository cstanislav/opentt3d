"""Show complete feature-identified river sources at their original datum; no inferred relief."""
from pathlib import Path
import hashlib, json, sys
from PIL import Image, ImageDraw

sys.path.insert(0,"tools/assets")
from compare_galleries import image

root = Path("build-macos")
out = root / "breadth-original-river-selector-source-sheets"
assert not out.exists()
out.mkdir()
verified = json.loads((root / "breadth-original-river-selector-classic-verification.json").read_text())["selected_sources"]
runs = json.loads((root / "breadth-original-river-selector-runs.json").read_text())
index = []
for climate,selection in verified.items():
    run = next(row for row in runs if row["climate"] == climate and row["backend"] == "vulkan" and row["tracing"])
    directory = Path(run["output"]) / "renderer3d-reference"
    originals = json.loads((directory / "river-selectors.json").read_text())["observations"]
    mapping = {(row["tile"],row["feature"],row["requested_offset"]):row["source_image"] for row in originals if not row["absent"]}
    selected = selection["ground_sources"]+selection["edge_sources"]
    unique = {(row["feature"],row["slope"],row["requested_offset"],row["resolved_offset"],row["selected_sprite"],row["source_image_sha256"]):row for row in selected}
    assert len(unique) == 16
    sheet = Image.new("RGB",(4*360,4*360),(38,39,47))
    draw = ImageDraw.Draw(sheet)
    for slot,(key,row) in enumerate(sorted(unique.items())):
        path = directory / mapping[row["tile"],row["feature"],row["requested_offset"]]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["source_image_sha256"]
        picture = image(path)
        assert [picture.width*4,picture.height*4] == row["source_size"]
        ox,oy = row["source_offset"]
        assert ox%4 == oy%4 == 0
        offset = (50+ox//4,52+oy//4)
        assert min(offset) >= 0 and offset[0]+picture.width <= 120 and offset[1]+picture.height <= 104
        panel = Image.new("RGBA",(120,104))
        panel.alpha_composite(picture,offset)
        left,top = slot%4*360,slot//4*360
        enlarged = panel.resize((360,312),Image.Resampling.NEAREST)
        sheet.paste(enlarged,(left,top+48),enlarged)
        draw.text((left+6,top+4),f"{climate} {row['feature']} slope{row['slope']}",fill="white")
        draw.text((left+6,top+18),f"input{row['requested_offset']} -> output{row['resolved_offset']}, sprite{row['selected_sprite']}",fill="white")
        draw.text((left+6,top+32),"Complete3x native; feature != relief/water ownership",fill="white")
        index.append({"climate":climate,"source":row,"source_image":str(path),"sheet":str(out / (climate+".png")),
                      "tile_anchor":[50,52],"native_offset":[ox//4,oy//4],"approved":False})
    sheet.save(out / (climate+".png"))
(out / "index.json").write_text(json.dumps(index,indent=2)+"\n")
print(json.dumps({"feature_identified_source_states":len(index),"sheets":4,"relief_water_ownership_or_geometry_approved":False}))

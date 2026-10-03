"""Inspect exact actual source owners at shared original tile/sequence anchors."""
from pathlib import Path
import hashlib, json, sys
from PIL import Image, ImageDraw

sys.path.insert(0,"tools/assets")
from compare_galleries import image
from contact_sheet import compose_registered

root = Path("build-macos")
out = root / "breadth-original-lock-live-source-sheets"
assert not out.exists()
out.mkdir()
verification = json.loads((root / "breadth-original-lock-live-source-verification.json").read_text())
sources = verification["selected_sources"]["temperate"]
files = {}
for run in json.loads((root / "breadth-original-lock-live-source-runs.json").read_text()):
    if run["climate"] != "temperate":
        continue
    directory = Path(run["output"]) / "renderer3d-reference"
    for row in json.loads((directory / "water-live.json").read_text())["observations"]:
        path = directory / row["source_image"]
        with path.open("rb") as data:
            digest = hashlib.file_digest(data,"sha256").hexdigest()
        files.setdefault(digest,path)
index = []
for elevation in range(2):
    for part, part_name in enumerate(("middle","lower","upper")):
        sheet = Image.new("RGB",(4*320,2*290),(38,39,47))
        draw = ImageDraw.Draw(sheet)
        for direction, name in enumerate(("NE","SE","SW","NW")):
            for face_index, face in enumerate(("rear","front")):
                selected, = [row for row in sources["bodies"] if (row["elevation"],row["part"],row["direction"],row["face"]) == (elevation,part,direction,face)]
                source = selected["source"]
                x,y,z = source["sequence_origin"]
                ox,oy = source["source_offset"]
                assert ox%4 == oy%4 == 0
                picture = image(files[source["source_image_sha256"]])
                assert list(picture.size) == [value//4 for value in source["source_size"]]
                # One owner's complete original image, not inferred geometry.
                registered = Image.new("RGBA",(96,80))
                offset = (48+2*(y-x)+ox//4,40+x+y-z+oy//4)
                registered.alpha_composite(picture,offset)
                registered = registered.resize((288,240),Image.Resampling.NEAREST)
                left,top = direction*320,face_index*290
                sheet.paste(registered,(left+16,top+40),registered)
                draw.text((left+8,top+8),f"{part_name} {name} {face}, elevation {elevation}; sprite {source['sprite']}",fill="white")
                draw.text((left+8,top+24),f"Original tile/sequence anchor, 3x native; sort != dimensions",fill="white")
                index.append({"elevation":elevation,"part":part,"direction":direction,"face":face,
                    "source":str(files[source["source_image_sha256"]]),"source_sha256":source["source_image_sha256"],
                    "anchor_in_panel":[48,40],"sprite_native_offset":[ox//4,oy//4],"sequence_origin":[x,y,z],"approved":False})
        sheet.save(out / f"source-elevation{elevation}-{part_name}.png")
(out / "index.json").write_text(json.dumps(index,indent=2)+"\n")
print(json.dumps({"owner_sources":len(index),"sheets":6,"approved":False}))

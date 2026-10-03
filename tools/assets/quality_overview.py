#!/usr/bin/env python3
"""Make a name-indexed breadth sheet from actual native voxel review captures.

No models are inferred or scored. Every catalogue model needs all eight orbit/
street images and its registered native study. Fresh PAM and losslessly compacted
PNG are both supported. Source-scale studies stay available for detailed review.
"""
import argparse
import hashlib
import json
from pathlib import Path

from quality_audit import fingerprint


def image_path(directory, name):
    for suffix in (".pam", ".png"):
        path = directory/(name+suffix)
        if path.is_file():
            return path
    raise ValueError(f"Missing native review image: {name}")


def model_images(directory, catalogue):
    owners = {}
    for category, identifiers in catalogue["bindings"].items():
        for identifier, states in identifiers.items():
            for state, model in states.items():
                owners.setdefault(model,[]).append(f"{category}/{identifier}/{state}")
    records = []
    for name, model in sorted(catalogue["models"].items()):
        prefix = "model-voxel-"+name
        views = [image_path(directory,prefix+f"-{view}") for view in range(8)]
        native = image_path(directory,prefix+"-native")
        registration = directory/(prefix+"-native.json")
        if not registration.is_file():
            raise ValueError(f"Missing source-scale registration: {name}")
        records.append({"model":name,"fingerprint":fingerprint(model,catalogue["materials"]),"owners":owners.get(name,[]),
                        "views":[str(path) for path in views],"native":str(native),"registration":str(registration)})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--catalogue",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a fresh sheet directory to preserve prior review evidence")
    records = model_images(args.directory,json.loads(args.catalogue.read_text()))
    from PIL import Image,ImageDraw,ImageChops
    from contact_sheet import read_pam
    args.output.mkdir(parents=True)
    for start in range(0,len(records),32):
        group = records[start:start+32]
        sheet = Image.new("RGB",(1536,1432),(35,38,43))
        draw = ImageDraw.Draw(sheet)
        draw.text((8,8),f"Actual 3D catalogue breadth / models{start+1}…{start+len(group)} / orbit0, opposite2, street4 / NOT detail or world approval",fill="white")
        for slot,record in enumerate(group):
            x,y = (slot%4)*384,40+(slot//4)*174
            draw.text((x+4,y+2),record["model"],fill="white")
            owner = record["owners"][0] if record["owners"] else "unbound diagnostic"
            draw.text((x+4,y+18),owner,fill=(170,178,189))
            for column,view in enumerate((0,2,4)):
                path = Path(record["views"][view])
                if path.suffix == ".pam":
                    image = read_pam(path)
                else:
                    with Image.open(path) as source:
                        if "opentt3d_pam_header" not in source.info:
                            raise ValueError(f"Not a verified compacted capture: {path}")
                        image = source.convert("RGBA")
                rgb = image.convert("RGB")
                # Street previews have a uniform blue sky, not a black canvas.
                # Crop display-only padding; do not change the retained capture.
                background = Image.new("RGB",image.size,rgb.getpixel((0,0)))
                bounds = ImageChops.difference(rgb,background).getbbox()
                if bounds is None:
                    raise ValueError(f"Blank authored model view: {path}")
                image = image.crop(bounds)
                image.thumbnail((122,134),Image.Resampling.NEAREST)
                sheet.paste(image,(x+column*128+(128-image.width)//2,y+36+(134-image.height)//2),image)
            record["sheet"] = str(args.output/f"models-{start:04}.png")
        sheet.save(args.output/f"models-{start:04}.png")
    manifest = {"format":1,"catalogue_sha256":hashlib.sha256(args.catalogue.read_bytes()).hexdigest(),
                "models":records,"sheet_crop":"Uniform background removed for display only; exact originals and registration retained.",
                "note":"Full catalogue capture index only; ratings require individual inspection, source and live-world evidence."}
    (args.output/"index.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"models":len(records),"sheets":(len(records)+31)//32,"native_studies":len(records),"orbit_street_views":len(records)*8}))


if __name__ == "__main__":
    main()

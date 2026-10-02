#!/usr/bin/env python3
"""Compose original object layers at their native tile anchors; never generate geometry."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from contact_sheet import compose_registered, read_pam
from original_objects import KINDS, validate_export


def compose(directory, entries):
    grounds, bodies, records = [], [], []
    for entry in entries:
        tx, ty = (value*16 for value in entry["tile_offset"])
        for role, layers in (("ground",[entry["ground"]]),("body",entry["body"])):
            for index,layer in enumerate(layers):
                path = directory/layer["image"]
                image = read_pam(path)
                if image.size != tuple((value+3)//4 for value in layer["sprite_size"]):
                    raise ValueError("Original object image dimensions differ from native sprite metadata")
                dx, dy = (value//4 for value in layer["sprite_offset"])
                x, y, z = layer.get("origin",[0,0,0])
                sx, sy = 2*(ty+y-tx-x)+dx, tx+x+ty+y-z+dy
                (grounds if role == "ground" else bodies).append((image,sx,sy))
                visible = image.getchannel("A").getbbox()
                records.append({"part":entry["part"],"layer":role,"body_index":index if role == "body" else None,
                                "sprite":layer["sprite"],"company_colour":layer["company_colour"],"image":str(path),
                                "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"registered_image_origin":[sx,sy],
                                "registered_visible_bounds":[sx+visible[0],sy+visible[1],sx+visible[2],sy+visible[3]] if visible else None})
    image, bounds = compose_registered(grounds+bodies)
    return image, {"registered_visible_bounds":list(bounds),"layers":records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path,help="Native --export-objects renderer3d-reference directory")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--scale",type=int,choices=range(1,9),default=4)
    args = parser.parse_args()
    report_path = args.output.with_suffix(".json")
    if args.output.suffix != ".png" or args.output.exists() or report_path.exists():
        parser.error("Use a fresh PNG output path and companion JSON path")
    manifest_path = args.directory/"objects.json"
    entries = json.loads(manifest_path.read_text())
    source_check = validate_export(entries)
    panels, records = [], []
    for kind in range(5):
        for stage in (range(5) if kind == 4 else [None]):
            tiles = [row for row in entries if row["object_id"]==kind and row["size_stage"]==stage]
            image, record = compose(args.directory,tiles)
            label = KINDS[kind]+(f" size {stage}" if stage is not None else "")
            panels.append((label,image))
            records.append({"object_id":kind,"size_stage":stage,"source_tiles":len(tiles),**record})
    width = max(200,max(image.width for label,image in panels)*args.scale+32)
    height = max(200,max(image.height for label,image in panels)*args.scale+50)
    sheet = Image.new("RGB",(width*3,height*3),(40,40,48))
    draw = ImageDraw.Draw(sheet)
    for index,(label,image) in enumerate(panels):
        x, y = index%3*width, index//3*height
        draw.text((x+12,y+10),label,fill=(245,245,250))
        image = image.resize((image.width*args.scale,image.height*args.scale),Image.Resampling.NEAREST)
        sheet.paste(image,(x+(width-image.width)//2,y+34),image)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(args.output)
    report = {"source_manifest":str(manifest_path),"manifest_sha256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "sheet":str(args.output),"sheet_sha256":hashlib.sha256(args.output.read_bytes()).hexdigest(),"scale":args.scale,
              "source_check":source_check,"panels":records,
              "scope":"Original native source RGBA/palette layers only. Every tile and ground/body layer keeps its original world/tile/sprite offset and HQ order. Ground-only HQ slots can contain raised artwork. Layers are composed, never extruded or converted into voxel geometry; this does not approve coverage, runtime object placement, company colour, palette animation, nonflat clearances or final fidelity.","final_visual_approvals":0}
    report_path.write_text(json.dumps(report,indent=2)+"\n")
    print(f"Original object sheet: nine layouts, {len(entries)} source tiles; no geometry or visual approval inferred")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Display original object layers and registered XYZ studies without artwork edits.

Run with Pillow. Equal-scale native panels retain their shared tile origin; tight
orbit/street thumbnails are display-only and do not confer coverage or approval.
"""
import argparse
import hashlib
import json
from pathlib import Path


def source_layer_registrations(rows):
    layers = []
    # Upstream sortable bodies are presented above their independently owned
    # ground. Keep the declared source tile/sequence anchors, not visible centres.
    for role in ("ground","body"):
        for row in sorted(rows,key=lambda row:row["part"]):
            root_x,root_y = (value*16 for value in row["tile_offset"])
            for layer in ([row[role]] if role == "ground" else row[role]):
                offset = layer["sprite_offset"]
                if len(offset) != 2 or any(type(value) is not int or value%4 for value in offset):
                    raise ValueError("Source offset is not registered at native sprite scale")
                x,y,z = layer.get("origin",[0,0,0])
                px = -2*(root_x+x)+2*(root_y+y)+offset[0]//4
                py = root_x+x+root_y+y-z+offset[1]//4
                layers.append((layer["image"],px,py))
    return layers


def source_evidence_paths(rows, directory):
    return [directory/filename for filename,x,y in source_layer_registrations(rows)]


def original_layers(rows, directory):
    from compare_galleries import image
    from contact_sheet import compose_registered
    return compose_registered([(image(directory/filename),x,y) for filename,x,y in source_layer_registrations(rows)])


def registered_native(path, registration):
    from compare_galleries import image
    from contact_sheet import compose_registered
    origin = registration["model_origin"]
    picture = image(path)
    if list(picture.size) != registration["image_size"]:
        raise ValueError("Native study size differs from its registration")
    return compose_registered([(picture,-origin[0],-origin[1])])


def equal_scale_pair(source, native, factor=4):
    from PIL import Image
    pictures = [source,native]
    left = min(bounds[0] for picture,bounds in pictures)
    top = min(bounds[1] for picture,bounds in pictures)
    right = max(bounds[2] for picture,bounds in pictures)
    bottom = max(bounds[3] for picture,bounds in pictures)
    result = []
    for picture,bounds in pictures:
        canvas = Image.new("RGBA",(right-left,bottom-top))
        canvas.alpha_composite(picture,(bounds[0]-left,bounds[1]-top))
        result.append(canvas.resize((canvas.width*factor,canvas.height*factor),Image.Resampling.NEAREST))
    return result,(left,top,right,bottom)


def tight_thumbnail(picture, size):
    from PIL import Image, ImageChops
    rgb = picture.convert("RGB")
    box = ImageChops.difference(rgb,Image.new("RGB",rgb.size,rgb.getpixel((0,0)))).getbbox()
    if box: picture = picture.crop(box)
    picture.thumbnail(size,Image.Resampling.NEAREST)
    return picture


def main():
    from PIL import Image, ImageDraw
    from compare_galleries import captures, image
    from original_objects import validate_export
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("references",type=Path)
    parser.add_argument("gallery",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error("Use a fresh output directory to retain earlier studies")
    original = json.loads((args.references/"objects.json").read_text())
    validate_export(original)
    layouts = json.loads((args.gallery/"voxel-object-layouts.json").read_text())
    rendered = captures(args.gallery,"model-voxel-object-*")
    if not layouts: parser.error("No complete active-climate original object layouts in the gallery")
    args.output.mkdir(parents=True)
    ledger = []
    for layout in layouts:
        kind,size = layout["object"],layout["size"]
        rows = [row for row in original if row["object_id"] == kind and (row["size_stage"] or 0) == size]
        if len(rows) != layout["parts"]: raise ValueError("Original source part count differs from the selected XYZ family")
        label = f"model-voxel-object-{kind}-{size}"
        source = original_layers(rows,args.references)
        registration = json.loads((args.gallery/(label+"-native.json")).read_text())
        native = registered_native(rendered[label+"-native"],registration)
        pair,bounds = equal_scale_pair(source,native)
        top_height = max(picture.height for picture in pair)+64
        panel_width = max(500,max(picture.width for picture in pair)+24)
        quarter_width = panel_width//2
        sheet = Image.new("RGB",(panel_width*2,top_height+480),(38,39,47))
        draw = ImageDraw.Draw(sheet)
        draw.text((12,10),f"Original object{kind} size{size} climate{layout['climate']} — source / registered XYZ; not an approval",fill="white")
        for slot,picture in enumerate(pair):
            x = slot*panel_width+(panel_width-picture.width)//2
            sheet.paste(picture,(x,45),picture)
            draw.text((slot*panel_width+12,29),"source at4x native scale" if slot == 0 else "XYZ at the same4x native scale and tile anchor",fill="white")
        evidence = [args.references/"objects.json",args.gallery/"voxel-object-layouts.json",args.gallery/(label+"-native.json"),rendered[label+"-native"]]
        evidence.extend(source_evidence_paths(rows,args.references))
        for view in range(8):
            path = rendered[f"{label}-{view}"]
            evidence.append(path)
            picture = tight_thumbnail(image(path),(quarter_width-12,200))
            x,y = view%4*quarter_width,top_height+view//4*240
            sheet.paste(picture,(x+(quarter_width-picture.width)//2,y+22+(200-picture.height)//2))
            draw.text((x+12,y+4),f"{'orbit' if view < 4 else 'street'} {view%4} — display crop",fill="white")
        filename = f"object-{kind}-size-{size}.png"
        sheet.save(args.output/filename)
        ledger.append({"object":kind,"size":size,"climate":layout["climate"],"sheet":filename,
                       "source_bounds":source[1],"native_bounds":native[1],"shared_bounds":bounds,
                       "evidence_sha256":{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in evidence},
                       "sheet_sha256":hashlib.sha256((args.output/filename).read_bytes()).hexdigest(),
                       "approval":False,"note":"Native scale/anchors are retained; orbit/street crops are display-only. Full individual source/world/state/consistency acceptance is separate."})
    (args.output/"index.json").write_text(json.dumps(ledger,indent=2)+"\n")
    print(json.dumps({"sheets":len(ledger),"output":str(args.output),"approvals":0}))


if __name__ == "__main__":
    main()

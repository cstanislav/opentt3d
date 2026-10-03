"""Retain original/native/eight-view owner sheets for each unbound lock study."""
from pathlib import Path
import argparse, hashlib, json, re, sys
from PIL import Image, ImageDraw

sys.path.insert(0,"tools/assets")
from compare_galleries import captures, image
from contact_sheet import compose_registered
from object_review import registered_native, equal_scale_pair, tight_thumbnail

root = Path("build-macos")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--prefix",default="breadth-original-lock-authored-study")
args = parser.parse_args()
assert re.fullmatch(r"breadth-original-lock-[a-z0-9-]+",args.prefix)
out = root / (args.prefix+"-sheets")
assert not out.exists()
(out / "owners").mkdir(parents=True)
gallery = root / (args.prefix+"-vulkan/renderer3d-reference")
rendered = captures(gallery,"model-voxel-lock_study_*")
sources = json.loads((root / "breadth-original-lock-live-source-verification.json").read_text())["selected_sources"]["temperate"]["bodies"]
files = {row["sha256"]:Path(row["portable_image"]) for row in json.loads(Path("opentt3d/reviews/20261003/water-live-selectors/source-file-map.json").read_text())}
compiled = json.loads((root / (args.prefix+"-frozen-build/baseset/opentt3d-voxels.json")).read_text())
index = []
for selected in sources:
    part = ("middle","lower","upper")[selected["part"]]
    direction = ("ne","se","sw","nw")[selected["direction"]]
    elevation = ("sea","elevated")[selected["elevation"]]
    face = selected["face"]
    name = f"lock_study_{part}_{direction}_{face}_{elevation}"
    original = selected["source"]
    source_path = files[original["source_image_sha256"]]
    x,y,z = original["sequence_origin"]
    dx,dy = 2*(y-x),x+y-z
    ox,oy = original["source_offset"]
    assert ox%4 == oy%4 == 0
    source = compose_registered([(image(source_path),dx+ox//4,dy+oy//4)])
    label = "model-voxel-"+name
    registration = gallery / (label+"-native.json")
    native = registered_native(rendered[label+"-native"],json.loads(registration.read_text()))
    native = native[0],tuple(value+(dx if i%2 == 0 else dy) for i,value in enumerate(native[1]))
    pair,bounds = equal_scale_pair(source,native)
    header = max(picture.height for picture in pair)+55
    sheet = Image.new("RGB",(640,header+330),(38,39,47))
    draw = ImageDraw.Draw(sheet)
    draw.text((8,8),name+" — unbound diagnostic; no approval",fill="white")
    for slot,picture in enumerate(pair):
        sheet.paste(picture,(slot*320+(320-picture.width)//2,45),picture)
        draw.text((slot*320+8,28),"actual source, 4x native" if slot == 0 else "XYZ, same original tile/sequence anchor",fill="white")
    for view in range(8):
        picture = tight_thumbnail(image(rendered[f"{label}-{view}"]),(150,135))
        left,top = view%4*160,header+view//4*165
        sheet.paste(picture,(left+(160-picture.width)//2,top+25+(135-picture.height)//2))
        draw.text((left+8,top+5),f"{'orbit' if view < 4 else 'street'} {view%4}",fill="white")
    path = out / "owners" / (name+".png")
    sheet.save(path)
    digest = lambda path:hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
    index.append({"model":name,"part":selected["part"],"direction":selected["direction"],"face":face,"elevation":selected["elevation"],
        "sheet":str(path),"sheet_sha256":digest(path),"source":original,"source_image":str(source_path),
        "source_bounds":source[1],"native_bounds":native[1],"shared_bounds":bounds,
        "evidence_sha256":{str(path):digest(path) for path in [source_path,registration,rendered[label+"-native"]]+[rendered[f"{label}-{view}"] for view in range(8)]},
        "approved":False,"runtime_bound":False})
(out / "index.json").write_text(json.dumps(index,indent=2)+"\n")
for part in range(3):
    for elevation in range(2):
        group = [row for row in index if row["part"] == part and row["elevation"] == elevation]
        group.sort(key=lambda row:(row["direction"],row["face"] != "rear"))
        canvas = Image.new("RGB",(1280,4*510),(38,39,47))
        for slot,row in enumerate(group):
            with Image.open(row["sheet"]) as source:
                source.thumbnail((640,510),Image.Resampling.NEAREST)
                canvas.paste(source,(slot%2*640,slot//2*510))
        canvas.save(out / f"{('middle','lower','upper')[part]}-elevation{elevation}.png")
print(json.dumps({"individual_source_native_orbit_street_sheets":len(index),"approved":False}))

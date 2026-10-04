"""Display the complete source and independent relief at one original tile anchor."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures, image
from contact_sheet import compose_registered
from object_review import registered_native, equal_scale_pair, tight_thumbnail


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error("Retain prior sheets and use a new output directory")
    (args.output / "owners").mkdir(parents=True)
    rendered = captures(args.gallery,"model-voxel-river_relief_study_*")
    assert len(rendered) == 72
    rows = []
    for row in json.loads((HERE / "source-index.json").read_text()):
        name = f"river_relief_study_{'island' if row['climate'] == 3 else 'rock'}_{row['slope_name'].lower()}"
        label = "model-voxel-"+name
        source_path = ROOT / row["portable_source"]
        cached = image(source_path)
        native_source = cached.resize(tuple(row["native_source_size"]),Image.Resampling.NEAREST)
        assert native_source.resize(cached.size,Image.Resampling.NEAREST).tobytes() == cached.tobytes()
        source = compose_registered([(native_source,*row["native_offset"])])
        registration = args.gallery / (label+"-native.json")
        native = registered_native(rendered[label+"-native"],json.loads(registration.read_text()))
        pair,bounds = equal_scale_pair(source,native)
        top = max(picture.height for picture in pair)+64
        canvas = Image.new("RGB",(800,top+390),(38,39,47))
        draw = ImageDraw.Draw(canvas)
        draw.text((8,8),name+" — original-datum diagnostic; no world binding or quality approval",fill="white")
        for slot,picture in enumerate(pair):
            canvas.paste(picture,(slot*400+(400-picture.width)//2,48),picture)
            draw.text((slot*400+8,29),"Complete original water+relief; 4x native" if slot == 0 else "Relief XYZ only; same scale and original tile anchor",fill="white")
        for view in range(8):
            picture = tight_thumbnail(image(rendered[f"{label}-{view}"]),(190,165))
            x,y = view%4*200,top+view//4*195
            canvas.paste(picture,(x+(200-picture.width)//2,y+24+(165-picture.height)//2))
            draw.text((x+8,y+4),f"{'orbit' if view < 4 else 'street'} {view%4}",fill="white")
        target = args.output / "owners" / (name+".png")
        canvas.save(target)
        evidence = [source_path,registration,rendered[label+"-native"]]+[rendered[f"{label}-{view}"] for view in range(8)]
        rows.append({"model":name,"source":row,"source_bounds":source[1],"native_bounds":native[1],"shared_bounds":bounds,
            "sheet":str(target),"sheet_sha256":digest(target),"evidence_sha256":{str(path):digest(path) for path in evidence},
            "runtime_bound":False,"source_water_excluded_from_volume":True,"quality_approved":False})
    (args.output / "index.json").write_text(json.dumps(rows,indent=2)+"\n")
    for kind in ("rock","island"):
        selected = [row for row in rows if f"_{kind}_" in row["model"]]
        canvas = Image.new("RGB",(1600,2*580),(38,39,47))
        for slot,row in enumerate(selected):
            with Image.open(row["sheet"]) as sheet:
                sheet.thumbnail((800,580),Image.Resampling.NEAREST)
                canvas.paste(sheet,(slot%2*800,slot//2*580))
        canvas.save(args.output / (kind+"-all-four-source-native-orbit-street.png"))
    print(json.dumps({"individual_owner_sheets":8,"runtime_bound":False,"approvals":0}))


if __name__ == "__main__":
    main()

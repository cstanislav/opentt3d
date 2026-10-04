"""Nearest-neighbour display magnification for individual inspection, never equality."""
import argparse
import json
from pathlib import Path
import sys
from PIL import Image,ImageChops,ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures,image
from contact_sheet import compose_registered
from object_review import registered_native,equal_scale_pair


def inspect_view(picture):
    # Display-only orbit/street crop; full originals stay hashed and compared.
    box = ImageChops.difference(picture.convert("RGB"),Image.new("RGB",picture.size,picture.getpixel((0,0))[:3])).getbbox()
    if box: picture = picture.crop(box)
    factor = max(1,min(8,275//picture.width,250//picture.height))
    return picture.resize((picture.width*factor,picture.height*factor),Image.Resampling.NEAREST)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision",choices=("initial","revised","snow-repaired","paint-repaired","acknowledged"),required=True)
    parser.add_argument("--climates",nargs="+",choices=("temperate","arctic","tropic","toyland"),default=("temperate","arctic","tropic","toyland"))
    args = parser.parse_args()
    target = HERE / (args.revision+"-detail-sheets")
    if target.exists(): raise ValueError("Retain prior display sheets")
    target.mkdir(); rows = []
    for source in json.loads((HERE / "actual-source-index.json").read_text()):
        climate = ("temperate","arctic","tropic","toyland")[source["climate"]]; edge = source["requested_offset"]
        if climate not in args.climates: continue
        name = f"river_bank_study_{climate}_flat_{edge:02d}"; prefix = "model-voxel-"+name
        directory = HERE / (args.revision+"-native-controls") / f"breadth-original-river-bank-{args.revision}-{climate}-vulkan-study/renderer3d-reference"
        frames = captures(directory,prefix+"-*"); assert len(frames) == 9
        registration = directory / (prefix+"-native.json")
        original = compose_registered([(image(ROOT / source["source_pam"]),*source["native_offset"])])
        native = registered_native(frames[prefix+"-native"],json.loads(registration.read_text()))
        pair,bounds = equal_scale_pair(original,native,factor=8)
        canvas = Image.new("RGB",(1200,1000),(38,39,47)); draw = ImageDraw.Draw(canvas)
        draw.text((8,8),name+" — "+args.revision+" unbound study; display magnification does not relax any comparison",fill="white")
        for slot,picture in enumerate(pair):
            canvas.paste(picture,(slot*600+(600-picture.width)//2,60),picture)
            draw.text((slot*600+8,35),"Original at8x native scale" if slot == 0 else "Independent volume at the same8x native tile anchor",fill="white")
        for view in range(8):
            picture = inspect_view(image(frames[prefix+f"-{view}"]))
            x,y = view%4*300,330+view//4*320
            canvas.paste(picture,(x+(300-picture.width)//2,y+35+(250-picture.height)//2))
            draw.text((x+8,y),f"{'Orbit' if view < 4 else 'Street'} {view%4} — display only",fill="white")
        path = target / (name+".png"); canvas.save(path)
        rows.append({"model":name,"climate":source["climate"],"edge":edge,"sheet":str(path.relative_to(ROOT)),
            "source":source["source_pam"],"source_sha256":source["source_pam_sha256"],"shared_bounds":bounds,
            "native_registration":str(registration.relative_to(ROOT)),"native_view":str(frames[prefix+"-native"].relative_to(ROOT)),
            "source_native_display_scale":8,"display_resizing_never_used_for_comparison":True,"approval":False})
    assert len(rows) == 12*len(set(args.climates))
    (target / "index.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps({"individual_model_detail_sheets":len(rows),"same_native_registration":True,"quality_approvals":0}))


if __name__ == "__main__": main()

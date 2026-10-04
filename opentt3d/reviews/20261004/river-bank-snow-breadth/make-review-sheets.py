"""Inspect every snowy bank with complete, byte-preserving registered source pairs."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from PIL import Image,ImageChops,ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures,image
spec = importlib.util.spec_from_file_location("snow_raw_registration",HERE.parent / "river-sloped-bank-breadth/registered-bytes.py")
raw = importlib.util.module_from_spec(spec); spec.loader.exec_module(raw)


def inspect_view(picture):
    box = ImageChops.difference(picture.convert("RGB"),Image.new("RGB",picture.size,picture.getpixel((0,0))[:3])).getbbox()
    if box: picture = picture.crop(box)
    factor = max(1,min(8,275//picture.width,250//picture.height))
    return picture.resize((picture.width*factor,picture.height*factor),Image.Resampling.NEAREST)


def main():
    target = HERE / "individual-review-sheets"
    if target.exists(): raise ValueError("Retain prior snowy bank review sheets")
    target.mkdir(); sheets,comparisons = [],[]
    run = HERE / "initial-native-controls/breadth-original-river-bank-snow-initial-arctic-vulkan-study/renderer3d-reference"
    for source in json.loads((HERE / "actual-source-index.json").read_text()):
        name = f"river_bank_snow_study_arctic_offset{source['requested_offset']:02d}"; label = "model-voxel-"+name
        frames = captures(run,label+"-*"); assert len(frames) == 9
        registration_path = run / (label+"-native.json"); original_path = ROOT / source["source_pam"]
        original = raw.registered(image(original_path),source["native_offset"])
        model = raw.native(image(frames[label+"-native"]),json.loads(registration_path.read_text()))
        (a,b),bounds = raw.pair(original,model); x,y = a.tobytes(),b.tobytes()
        paths = [original_path,frames[label+"-native"],registration_path]
        changes = sum(x[index:index+4] != y[index:index+4] for index in range(0,len(x),4))
        silhouette = sum(bool(x[index+3]) != bool(y[index+3]) for index in range(0,len(x),4))
        comparisons.append({"model":name,"climate":1,"slope":source["slope"],"requested_offset":source["requested_offset"],
            "shared_bounds":bounds,"raw_source_bounds":original[1],"raw_native_bounds":model[1],"complete_rgba_changed_pixels":changes,
            "alpha_presence_differences_additional_diagnostic":silhouette,"exit_code":int(changes != 0),
            "original_visible_pixels":sum(bool(x[index+3]) for index in range(0,len(x),4)),"model_visible_pixels":sum(bool(y[index+3]) for index in range(0,len(y),4)),
            "all_raw_image_bytes_preserved_without_alpha_compositing":True,"resizing_cropping_masks_fitting_or_tolerance_used":False,
            "evidence_sha256":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}})
        pair = [picture.resize((picture.width*7,picture.height*7),Image.Resampling.NEAREST) for picture in (a,b)]
        canvas = Image.new("RGB",(1200,1020),(38,39,47)); draw = ImageDraw.Draw(canvas)
        draw.text((8,8),name+" — unbound original-datum snow bank; extra doubled-terrain support/fidelity unaccepted",fill="white")
        for slot,picture in enumerate(pair):
            canvas.paste(picture,(slot*600+(600-picture.width)//2,65),picture)
            draw.text((slot*600+8,35),"Complete original7x" if slot == 0 else "Complete separate snow volume7x at the same tile anchor",fill="white")
        for view in range(8):
            picture = inspect_view(image(frames[label+f"-{view}"])); x,y = view%4*300,350+view//4*320
            canvas.paste(picture,(x+(300-picture.width)//2,y+35+(250-picture.height)//2))
            draw.text((x+8,y),f"{'Orbit' if view < 4 else 'Street'} {view%4} — display-only magnification",fill="white")
        path = target / (name+".png"); canvas.save(path)
        sheets.append({"model":name,"requested_offset":source["requested_offset"],"slope":source["slope"],"sheet":str(path.relative_to(ROOT)),
            "source_pam":source["source_pam"],"native_view":str(frames[label+"-native"].relative_to(ROOT)),"registration":str(registration_path.relative_to(ROOT)),
            "display_only_native_scale":7,"quality_approved":False})
    assert len(sheets) == len(comparisons) == 20
    (target / "index.json").write_text(json.dumps(sheets,indent=2)+"\n")
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"models":20,"rows":comparisons,
        "different_images":sum(row["exit_code"] for row in comparisons),"different_pixels":sum(row["complete_rgba_changed_pixels"] for row in comparisons),
        "silhouette_differences_additional_diagnostic":sum(row["alpha_presence_differences_additional_diagnostic"] for row in comparisons),
        "all_raw_image_bytes_preserved_without_alpha_compositing":True,"source_geometry_fitted_traced_extruded_or_tolerance_used":False,
        "runtime_bank_coverage_accepted":0,"quality_approvals":0}
    (HERE / "source-native-audit.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

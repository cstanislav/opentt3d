"""Present each original/native/orbit/street bank, retaining full unmasked comparisons."""
from datetime import datetime,timezone
import hashlib
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
    # Display-only magnification; full view canvases remain separately compared.
    box = ImageChops.difference(picture.convert("RGB"),Image.new("RGB",picture.size,picture.getpixel((0,0))[:3])).getbbox()
    if box: picture = picture.crop(box)
    factor = max(1,min(8,275//picture.width,250//picture.height))
    return picture.resize((picture.width*factor,picture.height*factor),Image.Resampling.NEAREST)


def main():
    target = HERE / "individual-review-sheets"
    if target.exists(): raise ValueError("Retain earlier complete individual review sheets")
    target.mkdir(); sheets,comparisons = [],[]
    runs = json.loads((HERE / "runs.json").read_text())
    for row in json.loads((HERE / "actual-source-index.json").read_text()):
        climate = ("temperate","arctic","tropic","toyland")[row["climate"]]
        name = f"river_bank_slope_study_{climate}_{row['direction']}_edge{row['edge']:02d}"; label = "model-voxel-"+name
        run = next(run for run in runs if run["climate"] == climate and run["backend"] == "vulkan")
        directory = HERE / "initial-native-controls" / Path(run["output"]).name / "renderer3d-reference"
        frames = captures(directory,label+"-*"); assert len(frames) == 9
        registration_path = directory / (label+"-native.json")
        original = compose_registered([(image(ROOT / row["source_pam"]),*row["native_offset"])])
        native = registered_native(frames[label+"-native"],json.loads(registration_path.read_text()))
        (a,b),bounds = equal_scale_pair(original,native,factor=1)
        x,y = a.tobytes(),b.tobytes()
        changes = sum(x[index:index+4] != y[index:index+4] for index in range(0,len(x),4))
        silhouette = sum(bool(x[index+3]) != bool(y[index+3]) for index in range(0,len(x),4))
        paths = [ROOT / row["source_pam"],frames[label+"-native"],registration_path]
        comparisons.append({"model":name,"climate":row["climate"],"slope":row["slope"],"edge":row["edge"],"source_state":row["source_state"],
            "shared_native_bounds":bounds,"complete_rgba_changed_pixels":changes,"alpha_presence_differences_additional_diagnostic":silhouette,
            "original_visible_pixels":sum(bool(x[index+3]) for index in range(0,len(x),4)),
            "model_visible_pixels":sum(bool(y[index+3]) for index in range(0,len(y),4)),"exit_code":int(changes != 0),
            "source_images_resized_cropped_masked_fitted_or_tolerance_used":False,
            "comparison_padding":"Transparent union canvas at the exact source tile origin; no source crop or visible-bounds centring.",
            "original_sea_wave_pixels_removed_from_comparison":False,
            "evidence_sha256":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}})
        pair,display_bounds = equal_scale_pair(original,native,factor=8); assert bounds == display_bounds
        canvas = Image.new("RGB",(1200,1000),(38,39,47)); draw = ImageDraw.Draw(canvas)
        draw.text((8,8),name+" - unbound original-datum bank; extra doubled-terrain support and source fidelity unaccepted",fill="white")
        for slot,picture in enumerate(pair):
            canvas.paste(picture,(slot*600+(600-picture.width)//2,65),picture)
            caption = "Complete original at 8x, including sea wave fringe" if slot == 0 else "Separate bank volume at the same 8x tile anchor (no voxel water)"
            draw.text((slot*600+8,35),caption,fill="white")
        for view in range(8):
            picture = inspect_view(image(frames[label+f"-{view}"])); x,y = view%4*300,330+view//4*320
            canvas.paste(picture,(x+(300-picture.width)//2,y+35+(250-picture.height)//2))
            draw.text((x+8,y),f"{'Orbit' if view < 4 else 'Street'} {view%4} - display-only magnification",fill="white")
        path = target / (name+".png"); canvas.save(path)
        sheets.append({"model":name,"climate":row["climate"],"slope":row["slope"],"edge":row["edge"],"source_state":row["source_state"],
            "sheet":str(path.relative_to(ROOT)),"source_pam":row["source_pam"],"source_pam_sha256":row["source_pam_sha256"],
            "native_view":str(frames[label+"-native"].relative_to(ROOT)),"registration":str(registration_path.relative_to(ROOT)),
            "quality_approved":False,"display_only_native_scale":8})
    assert len(sheets) == len(comparisons) == 32
    (target / "index.json").write_text(json.dumps(sheets,indent=2)+"\n")
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"models":32,"rows":comparisons,
        "different_images":sum(row["exit_code"] for row in comparisons),"different_pixels":sum(row["complete_rgba_changed_pixels"] for row in comparisons),
        "silhouette_differences_additional_diagnostic":sum(row["alpha_presence_differences_additional_diagnostic"] for row in comparisons),
        "source_wave_pixels_retained_in_full_comparison":True,"native_backend_equality_is_not_source_quality":True,"quality_approvals":0}
    (HERE / "source-native-audit.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

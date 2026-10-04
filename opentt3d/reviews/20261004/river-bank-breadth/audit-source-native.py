"""Compare complete source/native RGBA at the original shared anchor; never fit art."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures,image
from contact_sheet import compose_registered
from object_review import registered_native,equal_scale_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision",choices=("initial","revised","snow-repaired","paint-repaired","acknowledged"),required=True)
    parser.add_argument("--climates",nargs="+",choices=("temperate","arctic","tropic","toyland"),default=("temperate","arctic","tropic","toyland"))
    args = parser.parse_args(); target = HERE / (args.revision+"-source-native-audit.json")
    if target.exists(): parser.error("Retain previous registration/fidelity failures")
    rows = []
    for row in json.loads((HERE / "actual-source-index.json").read_text()):
        climate = ("temperate","arctic","tropic","toyland")[row["climate"]]
        if climate not in args.climates: continue
        name = f"river_bank_study_{climate}_flat_{row['requested_offset']:02d}"; label = "model-voxel-"+name
        run = HERE / (args.revision+"-native-controls") / f"breadth-original-river-bank-{args.revision}-{climate}-vulkan-study/renderer3d-reference"
        native_path = captures(run,label+"-native")[label+"-native"]
        registration_path = run / (label+"-native.json")
        original = compose_registered([(image(ROOT / row["source_pam"]),*row["native_offset"])])
        native = registered_native(native_path,json.loads(registration_path.read_text()))
        (a,b),bounds = equal_scale_pair(original,native,factor=1)
        x,y = a.tobytes(),b.tobytes()
        changed = sum(x[i:i+4] != y[i:i+4] for i in range(0,len(x),4))
        silhouette = sum(bool(x[i+3]) != bool(y[i+3]) for i in range(0,len(x),4))
        paths = [ROOT / row["source_pam"],native_path,registration_path]
        rows.append({"model":name,"climate":row["climate"],"edge":row["requested_offset"],"shared_bounds":bounds,
            "complete_rgba_changed_pixels":changed,"alpha_presence_differences_additional_diagnostic":silhouette,
            "source_visible_pixels":sum(bool(x[i+3]) for i in range(0,len(x),4)),
            "model_visible_pixels":sum(bool(y[i+3]) for i in range(0,len(y),4)),"exit_code":int(changed != 0),
            "complete_source_and_native_images_retained":True,"resizing_alignment_masks_or_tolerance_used":False,
            "comparison_padding":"Transparent union canvas at the exact original tile origin; no visible-bounds recentering or source crop.",
            "evidence_sha256":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}})
    assert len(rows) == 12*len(set(args.climates))
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"models":len(rows),"rows":rows,
        "different_images":sum(row["exit_code"] for row in rows),"different_pixels":sum(row["complete_rgba_changed_pixels"] for row in rows),
        "silhouette_differences_additional_diagnostic":sum(row["alpha_presence_differences_additional_diagnostic"] for row in rows),
        "quality_approvals":0,"native_backend_equality_is_not_source_fidelity":True,"geometry_or_materials_modified":False}
    target.write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

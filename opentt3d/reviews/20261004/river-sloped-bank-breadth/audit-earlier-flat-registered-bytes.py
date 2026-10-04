"""Supplement immutable flat-bank evidence with a complete raw registered audit."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FLAT = HERE.parent / "river-bank-breadth"
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures,image
spec = importlib.util.spec_from_file_location("earlier_flat_raw_registration",HERE / "registered-bytes.py")
raw = importlib.util.module_from_spec(spec); spec.loader.exec_module(raw)


def main():
    target = HERE / "earlier-flat-byte-preserving-source-native-audit.json"
    if target.exists(): raise ValueError("Retain prior flat audit supplements")
    previous_path = FLAT / "acknowledged-source-native-audit.json"
    previous = json.loads(previous_path.read_text()); rows = []
    for source in json.loads((FLAT / "actual-source-index.json").read_text()):
        climate = ("temperate","arctic","tropic","toyland")[source["climate"]]
        name = f"river_bank_study_{climate}_flat_{source['requested_offset']:02d}"; label = "model-voxel-"+name
        run = FLAT / "acknowledged-native-controls" / f"breadth-original-river-bank-acknowledged-{climate}-vulkan-study/renderer3d-reference"
        source_path = ROOT / source["source_pam"]; native_path = captures(run,label+"-native")[label+"-native"]
        registration_path = run / (label+"-native.json")
        original = raw.registered(image(source_path),source["native_offset"])
        model = raw.native(image(native_path),json.loads(registration_path.read_text()))
        (a,b),bounds = raw.pair(original,model); x,y = a.tobytes(),b.tobytes()
        old = next(row for row in previous["rows"] if row["model"] == name)
        changes = sum(x[index:index+4] != y[index:index+4] for index in range(0,len(x),4))
        silhouette = sum(bool(x[index+3]) != bool(y[index+3]) for index in range(0,len(x),4))
        rows.append({"model":name,"climate":source["climate"],"edge":source["requested_offset"],"shared_bounds":bounds,
            "raw_source_bounds":original[1],"raw_native_bounds":model[1],"complete_rgba_changed_pixels":changes,
            "alpha_presence_differences_additional_diagnostic":silhouette,"exit_code":int(changes != 0),
            "previous_alpha_composited_changed_pixels_not_a_raw_byte_audit":old["complete_rgba_changed_pixels"],
            "all_raw_rgba_preserved_without_alpha_compositing":True,"resizing_cropping_masks_fitting_or_tolerance_used":False,
            "evidence_sha256":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (source_path,native_path,registration_path)}})
    assert len(rows) == 48
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"models":48,"rows":rows,
        "different_images":sum(row["exit_code"] for row in rows),"different_pixels":sum(row["complete_rgba_changed_pixels"] for row in rows),
        "silhouette_differences_additional_diagnostic":sum(row["alpha_presence_differences_additional_diagnostic"] for row in rows),
        "retained_immutable_prior_audit":str(previous_path.relative_to(ROOT)),"retained_immutable_prior_audit_sha256":hashlib.sha256(previous_path.read_bytes()).hexdigest(),
        "prior_full_raw_byte_preservation_claim_accepted":False,"prior_visible_composite_numbers_preserved":True,
        "existing_flat_evidence_or_models_modified":False,"quality_approvals":0,"runtime_bank_coverage_accepted":0}
    target.write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

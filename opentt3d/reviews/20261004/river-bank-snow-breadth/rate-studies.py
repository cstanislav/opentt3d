"""Record separate snow volume/actual-source screenings, never inherited approval."""
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "river-sloped-bank-breadth"
sys.path.insert(0,str(ROOT / "tools/assets"))
from inventory import inventory
from quality_audit import audit,definition_fingerprint,fingerprint,REVIEW_CHECKS,write_ratings_csv

COMMON = [
    "Unbound snow studies are not drawn in the saved worlds. Original-world/atlas/save noninterference and original GPU picking do not establish live snow-bank placement, independent owners, water layering or ship clearances.",
    "Original-datum native shells keep thin bank thickness, but extra doubled-terrain support/joins, all LOD/height/neighbourhood boundaries and live bank-specific selection remain unaccepted.",
    "Twenty particular snow-painted inputs/results do not establish public terrain-type/snowline transition queries or complete snow/shore/desert/grass/grid/parameter/custom/incomplete/absence/phase states. The other160 conditional sloped slots remain unobserved, never declared absent.",
    "Strict renderer/source mismatches are retained in full; exact model/native pairs do not establish fidelity, override whole-world failures or relax any acceptance gate.",
    "The full every-runtime-asset3D/every-model8/10, sustained60fps/memory and platform/input/replay/network objectives remain unmet. No runtime instance or source/terrain/climate variant inherits a model rating or approval.",
]


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    if (HERE / "individual-decisions.json").exists(): raise ValueError("Retain prior individual snow reviews")
    catalogue = json.loads(gzip.decompress((HERE / "initial-native-controls/diagnostic-catalogue.json.gz").read_bytes()))
    notes = json.loads((HERE / "review-observations.json").read_text())["models"]
    sources = json.loads((HERE / "actual-source-index.json").read_text())
    sheets = json.loads((HERE / "individual-review-sheets/index.json").read_text())
    expected = {row["model"] for row in sheets}; assert len(expected) == 20 and set(notes) == expected
    reviewed = {"format":1,"models":{}}; instances = []
    for source in sources:
        name = f"river_bank_snow_study_arctic_offset{source['requested_offset']:02d}"; note = notes[name]
        assert 3 <= note["score"] <= 5 and note["defect"] and note["individually_inspected_source_native_orbit_street"] is True
        sheet = next(row for row in sheets if row["model"] == name); run = (ROOT / sheet["registration"]).parent
        paths = [ROOT / sheet["sheet"],ROOT / sheet["source_pam"],ROOT / sheet["registration"],ROOT / sheet["native_view"],
            HERE / "review-observations.json",HERE / "source-native-audit.json",HERE / "initial-native-controls/verification.json",
            HERE / "initial-native-controls/frozen-authored-source.json",HERE / "source-retention-receipt.json",
            PRIOR / "registered-bytes.py",PRIOR / "registered-bytes-tests.log",run.parent / "console-review.log",run.parent / "save/smoke-state.sav"]
        paths.extend(run / ("model-voxel-"+name+f"-{view}.png") for view in range(8))
        evidence = [str(path.relative_to(ROOT)) for path in paths]; defects = [note["defect"],*COMMON]
        reviewed["models"][name] = {"score":note["score"],"fingerprint":fingerprint(catalogue["models"][name],catalogue["materials"]),
            "checks":{check:False for check in REVIEW_CHECKS},"defects":defects,"evidence":evidence,
            "evidence_sha256":{path:digest(ROOT / path) for path in evidence},
            "notes":[f"Individually inspected particular snow-painted bank source/native/four-orbit/four-street {note['score']}/10 structural screening. Not aesthetic or runtime approval.",*defects]}
        instances.append({"source":source,"study_model":name,"representation":"unbound-diagnostic-source-instance","score":3,
            "fingerprint":definition_fingerprint({"source":source,"model_fingerprint":reviewed["models"][name]["fingerprint"]}),
            "checks":{check:False for check in REVIEW_CHECKS},"defects":defects,"evidence":evidence,
            "evidence_sha256":reviewed["models"][name]["evidence_sha256"],"runtime_bound":False,"quality_approved":False,
            "note":"One independent actually selected snow-painted source-instance screening. No model score, terrain-state coverage or approval is inherited."})
    assert len(reviewed["models"]) == len(instances) == 20
    (HERE / "current-quality-reviews.json").write_text(json.dumps(reviewed,indent=2)+"\n")
    (HERE / "diagnostic-source-instance-records.json").write_text(json.dumps(instances,indent=2)+"\n")
    state = {"reviewed_utc":datetime.now(timezone.utc).isoformat(),"conditional_bank_shape_slots":240,"earlier_flat_sloped_shape_candidates":80,
        "earlier_conditional_slots_unobserved":160,"additional_particular_snow_paint_variants":20,"new_conditional_shape_slots_claimed":0,
        "actual_snow_source_instances":sources,"public_terrain_type_queries_or_all_snowline_transitions_accepted":False,
        "prior_conditional_inventory_sha256":digest(PRIOR / "current-conditional-family-inventory.json"),
        "runtime_bank_coverage_accepted":0,"quality_approvals":0}
    (HERE / "state-breadth-inventory.json").write_text(json.dumps(state,indent=2)+"\n")
    combined = json.loads((PRIOR / "current-combined-quality-reviews.json").read_text())
    assert not set(combined["models"]) & expected; combined["models"].update(reviewed["models"])
    scope = inventory(catalogue); report = audit(catalogue,combined,scope=scope)
    assert len(report["models"]) == 2966 and len(report["coverage_gaps"]) == 4 and not report["meets_objective"]
    assert sum(row["status"] == "individually-reviewed" for row in report["models"]) == 157
    assert not [row for row in report["models"] if row["score"] >= 8]
    (HERE / "current-combined-quality-reviews.json").write_text(json.dumps(combined,indent=2)+"\n")
    (HERE / "exact-current-catalogue-inventory.json").write_text(json.dumps(scope,indent=2)+"\n")
    (HERE / "current-full-catalogue-quality.json").write_text(json.dumps(report,indent=2)+"\n")
    write_ratings_csv(HERE / "current-full-catalogue-ratings.csv",report["models"])
    command = [sys.executable,"tools/assets/quality_audit.py","--catalogue","build-macos/breadth-original-river-bank-snow-initial-frozen-build/baseset/opentt3d-voxels.json",
        "--reviews",str(HERE / "current-combined-quality-reviews.json"),"--inventory",str(HERE / "exact-current-catalogue-inventory.json"),
        "--output",str(HERE / "required-eight-quality.json"),"--require-eight"]
    with (HERE / "required-eight.log").open("x") as log: result = subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 1
    (HERE / "required-eight-gate-receipt.json").write_text(json.dumps({"command":command,"exit_code":1,"required_eight_met":False,
        "quality_rows":2966,"individually_reviewed_rows":157,"coverage_gaps":4,"quality_approvals":0},indent=2)+"\n")
    value = {"reviewed_utc":datetime.now(timezone.utc).isoformat(),"individual_snow_model_screenings":20,"independent_actual_source_instance_screenings":20,
        "individual_model_scores":{name:row["score"] for name,row in reviewed["models"].items()},"earlier_bank_models_exact":80,
        "exact_catalogue_quality_rows":2966,"individually_reviewed_rows":157,"coverage_gaps":4,"runtime_bank_coverage_accepted":0,
        "quality_approvals":0,"required_eight_met":False,"canonical_art_or_bindings_changed":False,"recommended_release_changed":False}
    (HERE / "individual-decisions.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

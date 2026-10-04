"""Record individual sloped-owner screenings only after their actual images were inspected."""
from datetime import datetime,timezone
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FLAT = HERE.parent / "river-bank-breadth"
sys.path.insert(0,str(ROOT / "tools/assets"))
from inventory import inventory
from quality_audit import audit,definition_fingerprint,fingerprint,REVIEW_CHECKS,write_ratings_csv

COMMON = [
    "Unbound sloped volumes are not drawn in the saved worlds; canonical noninterference and tile picking do not establish live bank placement, layer ordering, bank-specific picking, visibility or ship clearance.",
    "The original-datum thin slope shell has no accepted extra doubled-terrain support/joins or LOD/height/neighbourhood boundaries. Object thickness must remain unchanged when that independent support is added.",
    "Strict model/backend acceptance fails seventeen complete views/thirty-four pixels, alongside the retained canonical world46/18/45/24-pixel failures. Neither fixed native pairs nor a low mismatch count relaxes any gate.",
    "The earlier display-helper source audit is retained/rejected: it cropped transparent borders and alpha-composited raw images. Fresh raw paste-only comparisons retain every source/native byte and still fail all32 owners; this evidence repair grants no quality promotion.",
    "The other160 conditional sloped slots remain unobserved/unmodelled, not declared intentionally absent. Other sea-level/snow/desert/grid/grass/parameter/custom/incomplete/absence selectors, source phases and palette/remap ownership remain required.",
    "The every-runtime-asset3D/every-model8/10 and sustained60fps/memory/platform/input/replay/network objectives remain unmet. An instance inherits neither a volume rating nor another climate/state's approval.",
]


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-byte-preservation",action="store_true")
    args = parser.parse_args()
    if (HERE / "individual-decisions.json").exists():
        if not args.refresh_byte_preservation: raise ValueError("Retain prior review decisions")
        retained = HERE / "retained-alpha-composited-audit"
        for name in ("current-quality-reviews.json","diagnostic-source-instance-records.json","current-conditional-family-inventory.json",
            "current-combined-quality-reviews.json","current-full-catalogue-quality.json","current-full-catalogue-ratings.csv",
            "required-eight-quality.json","required-eight.log","required-eight-gate-receipt.json","individual-decisions.json"):
            assert (retained / name).read_bytes() == (HERE / name).read_bytes()
    compiled = json.loads(gzip.decompress((HERE / "initial-native-controls/diagnostic-catalogue.json.gz").read_bytes()))
    sources = json.loads((HERE / "actual-source-index.json").read_text())
    sheets = json.loads((HERE / "individual-review-sheets/index.json").read_text())
    notes = json.loads((HERE / "review-observations.json").read_text())["models"]
    expected = {row["model"] for row in sheets}; assert len(expected) == 32 and set(notes) == expected
    reviewed = {"format":1,"models":{}}; instances = []; conditional = json.loads((HERE / "complete-conditional-family-inventory.json").read_text())
    for source in sources:
        climate = ("temperate","arctic","tropic","toyland")[source["climate"]]
        name = f"river_bank_slope_study_{climate}_{source['direction']}_edge{source['edge']:02d}"; note = notes[name]
        assert 3 <= note["score"] <= 5 and note["defect"] and note["individually_inspected_source_native_orbit_street"] is True
        sheet = next(row for row in sheets if row["model"] == name); run = (ROOT / sheet["registration"]).parent
        paths = [ROOT / sheet["sheet"],ROOT / source["source_pam"],ROOT / sheet["registration"],ROOT / sheet["native_view"],
            HERE / "source-native-audit.json",HERE / "review-observations.json",HERE / "initial-native-controls/verification.json",
            HERE / "registered-bytes.py",HERE / "registered-bytes-tests.log",
            HERE / "initial-native-controls/frozen-authored-source.json",HERE / "complete-conditional-family-inventory.json",
            run.parent / "console-review.log",run.parent / "save/smoke-state.sav"]
        paths.extend(run / ("model-voxel-"+name+f"-{view}.png") for view in range(8))
        evidence = [str(path.relative_to(ROOT)) for path in paths]; defects = [note["defect"],*COMMON]
        if source["source_state"] == "sea-level-observation":
            defects.insert(1,"The complete actual sea-level source includes an independently owned wave fringe. It stays in every comparison/original source, but is not modelled as blue bank voxels or accepted as a new bank/water runtime decomposition.")
        reviewed["models"][name] = {"score":note["score"],"fingerprint":fingerprint(compiled["models"][name],compiled["materials"]),
            "checks":{check:False for check in REVIEW_CHECKS},"defects":defects,"evidence":evidence,
            "evidence_sha256":{path:digest(ROOT / path) for path in evidence},
            "notes":[f"Individually inspected original/native/four-orbit/four-street sloped bank {note['score']}/10 screening, not aesthetic or runtime approval.",*defects]}
        instances.append({"source":source,"study_model":name,"representation":"unbound-diagnostic-source-instance","score":3,
            "fingerprint":definition_fingerprint({"source":source,"model_fingerprint":reviewed["models"][name]["fingerprint"]}),
            "checks":{check:False for check in REVIEW_CHECKS},"defects":defects,"evidence":evidence,
            "evidence_sha256":reviewed["models"][name]["evidence_sha256"],"runtime_bound":False,"quality_approved":False,
            "note":"Separate actual sloped source instance screening; no model score, runtime state coverage or approval is inherited."})
        state = next(row for row in conditional["states"] if row["climate"] == source["climate"] and row["offset"] == source["requested_offset"])
        state.update({"sloped_candidate_authored":True,"sloped_candidate_model":name,"sloped_candidate_fingerprint":reviewed["models"][name]["fingerprint"],
            "runtime_source_coverage_accepted":False,"quality_approved":False})
    assert len(reviewed["models"]) == len(instances) == 32
    conditional["reviewed_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "current-conditional-family-inventory.json").write_text(json.dumps(conditional,indent=2)+"\n")
    (HERE / "current-quality-reviews.json").write_text(json.dumps(reviewed,indent=2)+"\n")
    (HERE / "diagnostic-source-instance-records.json").write_text(json.dumps(instances,indent=2)+"\n")
    combined = json.loads((FLAT / "current-combined-quality-reviews.json").read_text())
    supplement = HERE / "earlier-flat-byte-preserving-source-native-audit.json"
    flat_note = "The prior immutable display-helper source audit did not establish uncropped/raw byte comparison. Its full-byte claim is rejected; the supplemental raw paste-only audit preserves every source/native RGBA byte and still fails48/48 models by5128 pixels/1860 additional silhouette differences. No original evidence or model was changed and no score/approval is promoted."
    for name,row in combined["models"].items():
        if name.startswith("river_bank_study_"):
            assert row["score"] < 8 and not any(row["checks"].values())
            row["defects"].append(flat_note); row["notes"].append(flat_note)
            evidence = str(supplement.relative_to(ROOT)); row["evidence"].append(evidence)
            row["evidence_sha256"][evidence] = digest(supplement)
    assert not set(combined["models"]) & expected; combined["models"].update(reviewed["models"])
    scope = inventory(compiled); report = audit(compiled,combined,scope=scope)
    assert len(report["models"]) == 2946 and len(report["coverage_gaps"]) == 4 and not report["meets_objective"]
    assert sum(row["status"] == "individually-reviewed" for row in report["models"]) == 137
    assert not [row for row in report["models"] if row["score"] >= 8]
    (HERE / "current-combined-quality-reviews.json").write_text(json.dumps(combined,indent=2)+"\n")
    (HERE / "exact-current-catalogue-inventory.json").write_text(json.dumps(scope,indent=2)+"\n")
    (HERE / "current-full-catalogue-quality.json").write_text(json.dumps(report,indent=2)+"\n")
    write_ratings_csv(HERE / "current-full-catalogue-ratings.csv",report["models"])
    command = [sys.executable,"tools/assets/quality_audit.py","--catalogue","build-macos/breadth-original-river-sloped-bank-initial-frozen-build/baseset/opentt3d-voxels.json",
        "--reviews",str(HERE / "current-combined-quality-reviews.json"),"--inventory",str(HERE / "exact-current-catalogue-inventory.json"),
        "--output",str(HERE / "required-eight-quality.json"),"--require-eight"]
    with (HERE / "required-eight.log").open("w" if args.refresh_byte_preservation else "x") as log: result = subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 1
    (HERE / "required-eight-gate-receipt.json").write_text(json.dumps({"command":command,"exit_code":result.returncode,"required_eight_met":False,
        "quality_rows":2946,"coverage_gaps":4,"quality_approvals":0},indent=2)+"\n")
    value = {"reviewed_utc":datetime.now(timezone.utc).isoformat(),"individually_screened_sloped_models":32,
        "individual_model_scores":{name:row["score"] for name,row in reviewed["models"].items()},"independent_actual_source_instance_screenings":32,
        "existing_flat_owners_unchanged":48,"exact_catalogue_quality_rows":2946,"individually_reviewed_rows":137,"coverage_gaps":4,
        "runtime_bank_coverage_accepted":0,"quality_approvals":0,"required_eight_met":False,"canonical_art_or_bindings_changed":False,
        "mixed_working_art_compiler_and_ratings_untouched":True,"recommended_release_unchanged":"opentt3d-dev-20261003.42",
        "full_raw_source_native_byte_preservation_repaired":args.refresh_byte_preservation}
    (HERE / "individual-decisions.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

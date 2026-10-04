"""Record separately inspected, explicitly sub-eight bank volumes and source instances."""
import argparse
from datetime import datetime,timezone
from functools import lru_cache
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from inventory import inventory
from quality_audit import audit,definition_fingerprint,fingerprint,REVIEW_CHECKS,write_ratings_csv

COMMON = [
    "Unbound bank volumes do not appear in the retained worlds; whole-world equality proves only canonical noninterference, not bank placement, ordering, GPU picking or runtime coverage.",
    "All source/native fidelity and complete backend acceptance remain unaccepted; regular stepped soil/crest profiles and approximate face paint remain visible.",
    "All sloped/sea-level/snow/desert/grass-grid-parameter/custom/incomplete/intentional-absence selectors, independent phases, extra doubled-terrain joins/LOD boundaries and actual ship clearances remain required.",
    "Catalogue-wide every-model8/10, sustained60fps/memory and platform/input/replay/network goals are unmet; no inherited score or approval is assigned to a source instance.",
]


@lru_cache(maxsize=None)
def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


@lru_cache(maxsize=5)
def load_catalogue(phase):
    return json.loads(gzip.decompress((HERE / (phase+"-native-controls/diagnostic-catalogue.json.gz")).read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-console-evidence",action="store_true")
    args = parser.parse_args()
    target = HERE / "individual-decisions.json"
    if target.exists() and not args.refresh_console_evidence: raise ValueError("Retain prior review decisions")
    if args.refresh_console_evidence:
        acknowledged = json.loads((HERE / "acknowledged-native-controls/verification.json").read_text())
        assert acknowledged["quiet_controls"] == acknowledged["actual_console_acknowledged_runs"] == acknowledged["actual_original_console_save_success_messages"] == 16
        retained = HERE / "retained-pre-console-rating"
        if retained.exists(): raise ValueError("Retain the previous console-evidence refresh")
        retained.mkdir()
        for name in ("individual-decisions.json","current-quality-reviews.json","diagnostic-source-instance-records.json",
            "exact-current-catalogue-inventory.json","current-combined-quality-reviews.json","current-full-catalogue-quality.json","current-full-catalogue-ratings.csv"):
            shutil.copy2(HERE / name,retained / name)
    compiled = load_catalogue("acknowledged" if args.refresh_console_evidence else "paint-repaired")
    observations = json.loads((HERE / "review-observations.json").read_text())
    sources = json.loads((HERE / "actual-source-index.json").read_text())
    review = {"format":1,"models":{}}; source_instances = []; scores = {}
    for climate,label in enumerate(("temperate","arctic","tropic","toyland")):
        notes = observations[label]; assert [note["edge"] for note in notes] == list(range(12))
        for note in notes:
            edge = note["edge"]; name = f"river_bank_study_{label}_flat_{edge:02d}"
            phase = "acknowledged" if args.refresh_console_evidence else "paint-repaired" if label == "toyland" else "snow-repaired" if label == "arctic" and edge in (5,6) else "revised"
            frozen = load_catalogue(phase)
            assert fingerprint(compiled["models"][name],compiled["materials"]) == fingerprint(frozen["models"][name],frozen["materials"])
            sheet = next(row for row in json.loads((HERE / (phase+"-detail-sheets/index.json")).read_text()) if row["model"] == name)
            source = next(row for row in sources if row["climate"] == climate and row["requested_offset"] == edge)
            run = HERE / (phase+"-native-controls") / f"breadth-original-river-bank-{phase}-{label}-vulkan-study/renderer3d-reference"
            paths = [ROOT / source["source_pam"],ROOT / sheet["sheet"],HERE / (phase+"-source-native-audit.json"),
                HERE / (phase+"-native-controls/verification.json"),HERE / (phase+"-native-controls/frozen-authored-source.json"),
                HERE / "review-observations.json",HERE / "complete-bank-family-inventory.json",run / ("model-voxel-"+name+"-native.json")]
            paths.extend(run / ("model-voxel-"+name+f"-{view}.png") for view in range(8))
            paths.append(run / ("model-voxel-"+name+"-native.png"))
            if args.refresh_console_evidence:
                paths.extend([run.parent / "console-review.log",run.parent / "save/smoke-state.sav",HERE / "console-evidence-gap.json"])
            evidence = [str(path.relative_to(ROOT)) for path in paths]
            defects = [note["defect"]]+COMMON
            assert note["score"] in (4,5)
            review["models"][name] = {"score":note["score"],"fingerprint":fingerprint(compiled["models"][name],compiled["materials"]),
                "checks":{check:False for check in REVIEW_CHECKS},"evidence":evidence,
                "evidence_sha256":{path:digest(ROOT / path) for path in evidence},"defects":defects,
                "notes":[f"Individually inspected original/native/four-orbit/four-street bank study: {note['score']}/10 provisional screening only, not aesthetic or runtime approval.",*defects]}
            scores[name] = note["score"]
            source_instances.append({"climate":climate,"edge":edge,"source":source,"study_model":name,
                "fingerprint":definition_fingerprint({"source":source,"study_model":name,"voxel":review["models"][name]["fingerprint"]}),
                "score":3,"representation":"unbound-diagnostic-source-instance","checks":{check:False for check in REVIEW_CHECKS},
                "defects":COMMON,"runtime_bound":False,"quality_approved":False,"evidence":evidence,
                "evidence_sha256":review["models"][name]["evidence_sha256"],
                "note":"Separate actual elevated-flat selector record. Neither the volume score nor other climate/state paint approvals are inherited."})
    assert len(review["models"]) == len(source_instances) == 48
    (HERE / "current-quality-reviews.json").write_text(json.dumps(review,indent=2)+"\n")
    (HERE / "diagnostic-source-instance-records.json").write_text(json.dumps(source_instances,indent=2)+"\n")
    combined = json.loads((ROOT / "assets/3d/quality_reviews.json").read_text())
    assert not combined["models"].keys() & review["models"].keys(); combined["models"].update(review["models"])
    scope = inventory(compiled); report = audit(compiled,combined,scope=scope)
    assert len(report["models"]) == 2914 and len(report["coverage_gaps"]) == 4 and not report["meets_objective"]
    assert sum(row["status"] == "individually-reviewed" for row in report["models"]) == 105
    assert not [row for row in report["models"] if row["score"] >= 8]
    (HERE / "exact-current-catalogue-inventory.json").write_text(json.dumps(scope,indent=2)+"\n")
    (HERE / "current-combined-quality-reviews.json").write_text(json.dumps(combined,indent=2)+"\n")
    (HERE / "current-full-catalogue-quality.json").write_text(json.dumps(report,indent=2)+"\n")
    write_ratings_csv(HERE / "current-full-catalogue-ratings.csv",report["models"])
    initial,revised,snow = [load_catalogue(phase) for phase in ("initial","revised","snow-repaired")]
    changes = {name:{"initial_fingerprint":fingerprint(initial["models"][name],initial["materials"]),
        "revised_fingerprint":fingerprint(revised["models"][name],revised["materials"]),
        "snow_repaired_fingerprint":fingerprint(snow["models"][name],snow["materials"]),
        "current_fingerprint":fingerprint(compiled["models"][name],compiled["materials"]),
        "initial_occupied":initial["models"][name]["occupied"],"current_occupied":compiled["models"][name]["occupied"]}
        for name in review["models"]}
    assert all(row["initial_fingerprint"] != row["current_fingerprint"] for row in changes.values())
    value = {"reviewed_utc":datetime.now(timezone.utc).isoformat(),"current_models":48,"individual_model_scores":scores,
        "changed_models":changes,"source_instances_separately_screened":48,"diagnostic_quality_rows":2914,
        "individual_reviews_in_exact_bank_scope":105,"full_defined_bank_source_instances_required":240,
        "sloped_source_instances_without_candidates":192,"quality_approvals":0,"coverage_gaps":4,"meets_objective":False,
        "runtime_bank_coverage_accepted":0,"canonical_artwork_or_bindings_changed":False,
        "actual_console_acknowledged_review_evidence":args.refresh_console_evidence,
        "preexisting_mixed_artwork_compiler_tests_and_csv_untouched":True,"recommended_release":"opentt3d-dev-20261003.42"}
    target.write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

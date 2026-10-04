"""Record eight individual sub-eight reviews without promoting original runtime coverage."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from inventory import inventory
from quality_audit import audit, definition_fingerprint, fingerprint, REVIEW_CHECKS, write_ratings_csv

DEFECTS = {
    "rock_sw":["The rear ledge and low front chip remain too regular; the central return still lacks the source's irregular narrow pillar and dark recessed paint."],
    "rock_se":["Six correctly distinct lobes remain simplified faceted blocks; the rear rock's broken crest and the downstream dark chip/face distributions are not source-faithful."],
    "rock_nw":["The broad downstream slab is still too faceted and misses the original square face, chipped lower corner and rear rock's sharply shaded return."],
    "rock_ne":["The rear-right mass and downstream wedge retain overly straight courses and simplified height/face transitions; original mottled dark paint is not reproduced."],
    "island_sw":["The fuller yellow cliff is a better volume study, but both cap contours, their near contact, cliff heights and pale-wall paint transitions remain approximate."],
    "island_se":["The pale-front/yellow-rear arrangement is recognizable, but the source cap spacing, wall heights and narrow intermediate side shades remain incorrect; street7 differs by three renderer pixels."],
    "island_nw":["The pale downstream cliff is too shallow and regular; its cap contour and the upper yellow island's original side/edge paint are not matched."],
    "island_ne":["The yellow cliff still reads shallower than the source, with simplified cap notches, gray return paint and vertical colour transitions."],
}
COMMON = [
    "Unbound original-datum studies are not runtime relief: independent animated water decomposition, exact extra doubled-terrain support and terrain/ship clearance remain unverified.",
    "Original source edge/transition paint includes seventeen undecided pixels across the eight sources; no hidden water or phase index is inferred.",
    "Cross-backend full-gallery/world acceptance fails. Per-owner LOD air boundaries, live custom/absence/order/phase states and sustained60fps/memory are not established.",
]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def catalogue(phase):
    return json.loads(gzip.decompress((HERE / (phase+"-native-controls/diagnostic-catalogue.json.gz")).read_bytes()))


def main():
    if (HERE / "individual-decisions.json").exists(): raise ValueError("Retain prior individual decisions")
    decisions = {}
    for phase in ("initial","revised"):
        compiled = catalogue(phase)
        rows = json.loads((HERE / (phase+"-sheets/index.json")).read_text())
        reviews = {"format":1,"models":{}}
        for row in rows:
            name = row["model"]
            run = HERE / (phase+"-native-controls") / f"breadth-original-river-relief-{phase}-temperate-vulkan-study/renderer3d-reference"
            label = "model-voxel-"+name
            evidence = [ROOT / row["source"]["portable_source"],ROOT / row["sheet"],
                HERE / (phase+"-native-controls/frozen-authored-source.json"),
                HERE / (phase+"-native-controls/verification.json"),run / (label+"-native.json")]
            evidence.extend(run / (label+f"-{view}.png") for view in range(8))
            evidence.append(run / (label+"-native.png"))
            paths = [str(path.relative_to(ROOT)) for path in evidence]
            defects = DEFECTS[name.removeprefix("river_relief_study_")]+COMMON
            if phase == "initial":
                defects = ["First retained arrangement underfills the observed rock silhouettes or skews/thins the island cap and wall profiles; superseded, not deleted."]+defects
            reviews["models"][name] = {"score":5,"fingerprint":fingerprint(compiled["models"][name],compiled["materials"]),
                "checks":{check:False for check in REVIEW_CHECKS},"evidence":paths,"evidence_sha256":{path:digest(ROOT / path) for path in paths},
                "defects":defects,"notes":["Individually inspected original/native/orbit/street relief study:5/10 provisional, not aesthetic approval or runtime coverage.",*defects]}
        assert len(reviews["models"]) == 8
        (HERE / (phase+"-quality-reviews.json")).write_text(json.dumps(reviews,indent=2)+"\n")
        combined = json.loads((ROOT / "assets/3d/quality_reviews.json").read_text())
        assert not combined["models"].keys() & reviews["models"].keys()
        combined["models"].update(reviews["models"])
        scope = inventory(compiled)
        report = audit(compiled,combined,scope=scope)
        assert len(report["models"]) == 2874 and len(report["coverage_gaps"]) == 4 and not report["meets_objective"]
        assert len([row for row in report["models"] if row["status"] == "individually-reviewed"]) == 65
        assert not [row for row in report["models"] if row["score"] >= 8]
        (HERE / (phase+"-combined-quality-reviews.json")).write_text(json.dumps(combined,indent=2)+"\n")
        (HERE / (phase+"-full-catalogue-quality.json")).write_text(json.dumps(report,indent=2)+"\n")
        write_ratings_csv(HERE / (phase+"-full-catalogue-ratings.csv"),report["models"])
        decisions[phase] = {"authored_relief_models":8,"individual_model_scores":{name:row["score"] for name,row in reviews["models"].items()},
            "full_quality_rows":len(report["models"]),"individual_reviews":65,"coverage_gaps":4,"approvals":0,"meets_objective":False,
            "runtime_bound":False,"all_six_acceptance_gates":False}
    initial,revised = catalogue("initial"),catalogue("revised")
    owners = []
    for row in json.loads((HERE / "climate-source-index.json").read_text()):
        name = row["study_model"]
        if name is None: continue
        value = {"source":row,"study_model":name,"voxel":fingerprint(revised["models"][name],revised["materials"])}
        owners.append({"climate":row["climate"],"slope":row["slope"],"study_model":name,"source":row,
            "fingerprint":definition_fingerprint(value),"score":3,"representation":"unbound-diagnostic-source-instance",
            "checks":{check:False for check in REVIEW_CHECKS},"defects":COMMON,"runtime_bound":False,"quality_approved":False,
            "note":"Equal source PAM bytes map this observed climate/selector to a retained study only. The source instance inherits no model score, coverage or approval."})
    assert len(owners) == 16
    (HERE / "diagnostic-source-instance-records.json").write_text(json.dumps(owners,indent=2)+"\n")
    changes = {name:{"initial_occupied":model["occupied"],"revised_occupied":revised["models"][name]["occupied"],
        "initial_fingerprint":fingerprint(model,initial["materials"]),
        "revised_fingerprint":fingerprint(revised["models"][name],revised["materials"])}
        for name,model in initial["models"].items() if name.startswith("river_relief_study_")}
    assert len(changes) == 8 and all(row["initial_fingerprint"] != row["revised_fingerprint"] for row in changes.values())
    value = {"reviewed_utc":datetime.now(timezone.utc).isoformat(),"phases":decisions,"changed_models":changes,
        "source_instances_separately_screened":16,"new_runtime_voxel_coverage":0,"canonical_artwork_or_bindings_changed":False,
        "prior_mixed_working_2998_row_csv_untouched":True,"recommended_release":"opentt3d-dev-20261003.42","geometry_approvals":0}
    (HERE / "individual-decisions.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({"individual_source_native_orbit_street_reviews":16,"current_models":8,"current_score":5,"full_catalogue_rows":2874,
        "source_instances":16,"coverage_gaps":4,"runtime_bound":False,"approvals":0,"meets_objective":False}))


if __name__ == "__main__":
    main()

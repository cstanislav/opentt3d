"""Refresh eight model reviews and independently screen all 16 supported instances."""
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "river-relief-breadth"
sys.path.insert(0,str(ROOT / "tools/assets"))
from inventory import inventory
from quality_audit import audit,definition_fingerprint,fingerprint,REVIEW_CHECKS,write_ratings_csv

DEFECTS = {
    "rock_sw":"Rear ledge, low chip and central narrow return remain simplified; regular side courses and mottled face paint do not match the source.",
    "rock_se":"Six independent dark lobes retain rounded/faceted block profiles, an unfaithful broken rear crest and regular stepped underside bands.",
    "rock_nw":"Broad downstream slab and rear return lack the source's square chipped face and sharp paint transitions; supported street undersides remain striped.",
    "rock_ne":"Rear-right mass and downstream wedge have overly straight courses and simplified mottled paint/height transitions; street silhouettes remain too regular.",
    "island_sw":"Yellow/pale cap contours, near contact and cliff shades remain approximate; the extra column support tilts caps and exposes regular underside steps in street studies.",
    "island_se":"Pale-front/yellow-rear caps remain too regular with incorrect spacing, wall heights and narrow side shades; supported street bands are not source-faithful.",
    "island_nw":"Pale downstream cliff remains shallow/regular; cap notches, yellow upper side paint and supported underside courses do not reproduce the original.",
    "island_ne":"Yellow cliff is shallower than the original; cap notches, gray returns and vertical transitions remain simplified; planar cap/piecewise support fidelity is unresolved.",
}
COMMON = [
    "Only diagnostic freezes bind relief/water. Canonical artwork and bindings are unchanged; remaining banks/terrain, theoretical inputs/heights/neighbourhoods/flags, zero-feature absences and custom families are incomplete.",
    "Seventeen pixels are semantically resolved and visible original water stays exact. Hidden lower authoring paint is retained, not a claim about unavailable hidden compiled-dither bytes or independent rendered phase completeness.",
    "Strict complete gallery, supported street and saved-world cross-backend comparisons fail without masks or tolerance; native equality is not aesthetic approval.",
    "Relief-specific live GPU picking, all-height terrain/ship clearance, ship traversal, independent phases, sustained60fps/memory and platform/input/replay/network acceptance remain open.",
]


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    if (HERE / "individual-supported-decisions.json").exists(): raise ValueError("Retain prior individual decisions")
    controls = HERE / "observer-separated-world-controls"
    report = json.loads((controls / "verification.json").read_text())
    assert report["quiet_world_controls"] == 40 and not report["strict_renderers_accepted"]
    compiled = json.loads(gzip.decompress((controls / "complete-opentt3d-voxels.json.gz").read_bytes()))
    previous = json.loads((PRIOR / "revised-quality-reviews.json").read_text())
    close = HERE / "close-world-controls"
    assert json.loads((close / "verification.json").read_text())["quiet_controls"] == 32
    reviews = {"format":1,"models":{}}
    for sheet in json.loads((HERE / "supported-model-sheets/index.json").read_text()):
        name = sheet["model"]; climate = "toyland" if sheet["climate"] == 3 else "temperate"
        paths = [sheet["sheet"],sheet["source"],sheet["original_native_registration"],sheet["supported_native_registration"],
            str((HERE / "resolved-source-paint.json").relative_to(ROOT)),str((controls / "verification.json").relative_to(ROOT)),
            str((close / "verification.json").relative_to(ROOT))]
        paths += [str((close / f"breadth-original-river-relief-close-observer-separated-{climate}-{sheet['slope']}-{backend}-complete/screenshot/smoke.png").relative_to(ROOT)) for backend in ("vulkan","opengl")]
        fp = fingerprint(compiled["models"][name],compiled["materials"])
        assert fp == previous["models"][name]["fingerprint"]
        defects = [DEFECTS[name.removeprefix("river_relief_study_")],*COMMON]
        reviews["models"][name] = {"score":5,"fingerprint":fp,"checks":{check:False for check in REVIEW_CHECKS},
            "evidence":paths,"evidence_sha256":{path:digest(ROOT / path) for path in paths},"defects":defects,
            "notes":["Individually reinspected source/native/supported orbit/street/saved-world study:5/10, not release approval.",*defects]}
    assert len(reviews["models"]) == 8
    (HERE / "supported-quality-reviews.json").write_text(json.dumps(reviews,indent=2)+"\n")
    companion = json.loads(gzip.decompress((controls / "complete-opentt3d-river-water.json.gz").read_bytes()))
    support = {3:[0.5,0,0,8],6:[0,0.5,0,8],9:[0,-0.5,8,8],12:[-0.5,0,8,8]}
    instances = []
    for source in companion["sources"]:
        slope,climate = source["slope"],source["climate"]
        name = compiled["bindings"]["river_relief"][str(slope)][str(climate)]
        value = {"climate":climate,"slope":slope,"model":name,"voxel":reviews["models"][name]["fingerprint"],
            "column_support":support[slope],"original_water_source":source}
        climate_name = ("temperate","arctic","tropic","toyland")[climate]
        instance_evidence = [str((controls / "verification.json").relative_to(ROOT)),
            str((controls / "actual-emitted-instances.json").relative_to(ROOT)),
            str((controls / "complete-opentt3d-river-water.json.gz").relative_to(ROOT))]
        for backend in ("vulkan","opengl"):
            run = controls / f"breadth-original-river-relief-world-observer-separated-{climate_name}-271828-{backend}-complete-classic"
            instance_evidence.extend(str(path.relative_to(ROOT)) for path in (run / "screenshot/smoke.png",
                run / "renderer3d-reference" / f"model-voxel-river-supported-{slope}-{climate}-native.json",
                run / "renderer3d-reference" / f"model-voxel-river-supported-{slope}-{climate}-native.png"))
        instances.append({"climate":climate,"slope":slope,"model":name,"score":5,
            "fingerprint":definition_fingerprint(value),"voxel_fingerprint":value["voxel"],
            "support_fingerprint":definition_fingerprint(support[slope]),"water_source_fingerprint":definition_fingerprint(source),
            "checks":{check:False for check in REVIEW_CHECKS},"defects":reviews["models"][name]["defects"],
            "evidence":instance_evidence,"evidence_sha256":{path:digest(ROOT / path) for path in instance_evidence},
            "diagnostic_bound_only":True,"inherited_model_approval":False,"quality_approved":False,
            "note":"Separate supported climate/slope instance review. Original columns/paint/air-boundary tests do not confer artwork, phase, live picking, ship, performance or runtime coverage acceptance."})
    assert len(instances) == 16 and len({row["fingerprint"] for row in instances}) == 16
    (HERE / "supported-instance-records.json").write_text(json.dumps(instances,indent=2)+"\n")
    combined = json.loads((ROOT / "assets/3d/quality_reviews.json").read_text())
    combined["models"].update(reviews["models"])
    scope = inventory(compiled); full = audit(compiled,combined,scope=scope)
    assert len(full["models"]) == 2874 and len(full["coverage_gaps"]) == 4 and not full["meets_objective"]
    assert not [row for row in full["models"] if row["score"] >= 8]
    (HERE / "full-supported-catalogue-quality.json").write_text(json.dumps(full,indent=2)+"\n")
    (HERE / "supported-combined-quality-reviews.json").write_text(json.dumps(combined,indent=2)+"\n")
    (HERE / "exact-supported-catalogue-inventory.json").write_text(json.dumps(scope,indent=2)+"\n")
    write_ratings_csv(HERE / "full-supported-catalogue-ratings.csv",full["models"])
    value = {"reviewed_utc":datetime.now(timezone.utc).isoformat(),"current_models":8,"unchanged_volume_fingerprints":8,
        "individual_model_scores":{name:row["score"] for name,row in reviews["models"].items()},"separate_supported_instances":16,
        "supported_instance_scores":5,"quality_rows":2874,"coverage_gaps":4,"quality_approvals":0,"meets_objective":False,
        "diagnostic_bound_only":True,"canonical_artwork_or_bindings_changed":False,"recommended_release":"opentt3d-dev-20261003.42"}
    (HERE / "individual-supported-decisions.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value))


if __name__ == "__main__": main()

"""Serialize explicit individual rejections; never infer approvals from generated sheets."""
from pathlib import Path
from collections import Counter
import datetime, hashlib, json, shutil, subprocess, sys

root = Path("build-macos")
prefix = "breadth-original-hq-medium-perimeter-owner"
out = Path("opentt3d/reviews/20261003/hq-larger-rejected")
decisions = json.loads((out / "individual-decisions.json").read_text())["decisions"]
sys.path.insert(0, "tools/assets")
from original_objects import validate_export
from quality_audit import fingerprint

digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
compiled_path = root / (prefix + "-catalogue.json")
compiled = json.loads(compiled_path.read_text())
baseline = json.loads((root / "breadth-original-hq-final-reviewed-frozen-build/baseset/opentt3d-voxels.json").read_text())
candidate_names = compiled["models"].keys() - baseline["models"].keys()
assert len(candidate_names) == len(decisions) == 84
assert {row["model"] for row in decisions} == candidate_names
assert all(fingerprint(model, baseline["materials"]) == fingerprint(compiled["models"][name], compiled["materials"])
           for name, model in baseline["models"].items())
freeze = root / (prefix + "-frozen-build")
frozen = json.loads((freeze / "manifest.json").read_text())
assert digest(compiled_path) == frozen["sha256"]["baseset/opentt3d-voxels.json"]
assert digest(Path("assets/3d/voxels.json")) == frozen["sha256"]["assets/3d/voxels.json"]
lookups = {}
source_owners = {}
for climate in ("temperate", "arctic", "tropic", "toyland"):
    study = root / (prefix + "-studies") / climate / "owners"
    exported = root / f"{prefix}-{climate}-vulkan/renderer3d-reference/objects.json"
    sources = json.loads(exported.read_text())
    assert validate_export(sources)["source_equivalent_layouts"] == 24
    index = json.loads((study / "index.json").read_text())
    for row in index:
        if row["model"] not in candidate_names:
            continue
        assert row["model"] not in lookups
        lookups[row["model"]] = study / row["sheet"]
        tile, = [tile for tile in sources if tile["object_id"] == 4 and tile["size_stage"] == row["size"] and tile["part"] == row["part"]]
        role = "ground" if row["category"] == "object_ground" else "body"
        layer = tile[role] if role == "ground" else tile[role][0]
        source_owners[row["model"]] = {"climate": climate, "size": row["size"], "part": row["part"], "role": role,
            "layout": row["layout"], "source_layer": layer, "source_export_sha256": digest(exported),
            "source_image_sha256": digest(exported.parent / layer["image"])}
    destination = out / (climate + "-original-layers.json")
    assert not destination.exists()
    shutil.copy2(exported, destination)
assert lookups.keys() == candidate_names

reviews = {"format": 1, "models": {}, "scope": "Explicit individual negative/provisional decisions for the quarantined1915-model candidate only. Source/orbit/street images were individually inspected, not bulk-approved. The six booleans mean acceptance, not mere viewing; all remain false. Eleven5/10 entries retain structural rejection scores for missing/misowned source geometry, not aesthetic approval. Released1831-model artwork/reviews remain unchanged."}
for decision in decisions:
    name = decision["model"]
    assert decision["score"] in (5, 6) and decision["defects"]
    destination = out / "owners" / (name + ".png")
    assert not destination.exists()
    destination.parent.mkdir(exist_ok=True)
    shutil.copy2(lookups[name], destination)
    path = str(destination)
    defects = decision["defects"] + [
        "No naturally selected saved/rendered size2..4 HQ world establishes this owner or its original upgrade state.",
        "Wider strict backend equality remains rejected; source shaping/paint and joined owner consistency are not accepted.",
    ]
    notes = [f"Individually inspected {source_owners[name]['climate']} size{source_owners[name]['size']} {source_owners[name]['role']} part{source_owners[name]['part']}, own registered source/native and four orbit/four street views; not approved."] + defects
    if decision["score"] == 5:
        notes.append("Five remains a conservative structural rejection score, not an aesthetic quality approval.")
    reviews["models"][name] = {"score": decision["score"], "fingerprint": fingerprint(compiled["models"][name], compiled["materials"]),
        "checks": {check: False for check in ("source", "orbit", "street", "world", "states", "consistency")},
        "inspection_completed": ["own-source", "registered-native", "orbit0..3", "street0..3"],
        "evidence": [path], "evidence_sha256": {path: digest(destination)}, "notes": notes, "defects": defects,
        "original_owner": source_owners[name]}
review_path = out / "prototype-quality-reviews.json"
assert not review_path.exists()
review_path.write_text(json.dumps(reviews, indent=2) + "\n")
for source, name in ((freeze / "assets/3d/voxels.json", "prototype-source.json"),
                     (freeze / "tools/assets/compile_voxels.py", "prototype-compiler-snapshot.py"),
                     (freeze / "tools/assets/test_hq_complete_voxels.py", "prototype-owner-tests-snapshot.py"),
                     (root / (prefix + "-asset-tests.log"), "candidate-220-asset-tests.log"),
                     (root / (prefix + "-strict-index.json"), "strict-backend-index.json"),
                     (root / "breadth-original-hq-medium-semantic-ground-union-preservation.json", "semantic-ground-union-preservation.json"),
                     (root / "breadth-original-hq-medium-review-cow-receipt.json", "catalogue-cow-receipt.json")):
    destination = out / name
    assert not destination.exists()
    shutil.copy2(source, destination)
for name in ("medium-north-source-owner-rejection.md", "medium-ground-fragment-rejection.md", "medium-perimeter-tip-rejection.md",
             "medium-owner-test-indentation-rejection.md", "medium-owner-test-indentation-rejected.py"):
    source = root / ("breadth-original-hq-" + name)
    destination = out / name
    assert not destination.exists()
    shutil.copy2(source, destination)

canonical = json.loads(Path("assets/3d/quality_reviews.json").read_text())
assert not (canonical["models"].keys() & reviews["models"].keys())
canonical["models"].update(reviews["models"])
combined = root / (prefix + "-combined-rejected-reviews.json")
assert not combined.exists()
combined.write_text(json.dumps(canonical, indent=2) + "\n")
old_csv = root / (prefix + "-pre-individual-screening-ratings.csv")
assert not old_csv.exists()
shutil.copy2("opentt3d/MODEL_RATINGS.csv", old_csv)
report = root / (prefix + "-individually-rejected-quality.json")
with (root / (prefix + "-individually-rejected-quality.log")).open("x") as log:
    result = subprocess.run(["python3", "tools/assets/quality_audit.py", "--catalogue", str(compiled_path), "--inventory", str(root / (prefix + "-inventory.json")),
        "--reviews", str(combined), "--output", str(report), "--csv", "opentt3d/MODEL_RATINGS.csv", "--require-eight"], stdout=log, stderr=subprocess.STDOUT)
assert result.returncode == 1 and report.is_file()
quality = json.loads(report.read_text())
assert not quality["meets_objective"] and all(row["score"] < 8 for row in quality["models"])
individual = [row for row in quality["models"] if row["status"] == "individually-reviewed"]
assert len(individual) == 141 and {row["model"] for row in individual} >= candidate_names
assert b"\r" not in Path("opentt3d/MODEL_RATINGS.csv").read_bytes()
summary = {"reviewed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "candidate_models": 1915,
    "prior_models_exact": 1831, "candidate_catalogue_sha256": digest(compiled_path),
    "prototype_source_sha256": digest(out / "prototype-source.json"), "prototype_individual_reviews": 84,
    "prototype_scores": dict(Counter(row["score"] for row in decisions)), "total_candidate_ledger_entries": len(quality["models"]),
    "total_individual_reviews": len(individual), "ledger_score_counts": quality["score_counts"],
    "final_approvals": 0, "require_eight_exit": result.returncode, "runtime_artwork_committed": False,
    "scope": reviews["scope"], "reproduce_combined_reviews": str(combined), "quality_report_sha256": digest(report)}
(out / "verification.json").write_text(json.dumps(summary, indent=2) + "\n")
evidence = {str(path): digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files": evidence, "scope": reviews["scope"]}, indent=2) + "\n")
print(json.dumps(summary))

"""Add twenty unresolved river-ground/climate rows, retaining every prior fingerprint/decision."""
from pathlib import Path
import csv, datetime, gzip, hashlib, json, shutil, subprocess, sys

sys.path.insert(0,"tools/assets")
from original_water import catalogue as water_catalogue
from quality_audit import original_water_rows

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/river-ground-quality-scope")
assert not out.exists()
out.mkdir(parents=True)
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
prior_root = Path("opentt3d/reviews/20261003/water-front-and-river-study")
old_scope = json.loads((prior_root / "candidate-inventory.json").read_text())
new_water = water_catalogue()
before = {row["model"]:row for row in original_water_rows(dict(old_scope["water_structures"],
    river_ground_source_selectors=new_water["river_ground_source_selectors"]),{"retained-renderer":"x"})
    if not row["model"].startswith("unresolved/river-ground/")}
after = {row["model"]:row for row in original_water_rows(new_water,{"retained-renderer":"x"})}
assert len(before) == 544 and len(after) == 564
assert all(row["fingerprint"] == after[name]["fingerprint"] for name,row in before.items())
assert before.keys() <= after.keys()
new_names = after.keys()-before.keys()
assert len(new_names) == 20 and all(name.startswith("unresolved/river-ground/") for name in new_names)
assert all(after[name]["score"] == 1 and after[name]["representation"] == "original-source-layer" and
           not after[name]["owners"] and not after[name]["checks"] for name in new_names)

scopes = (("canonical",Path("opentt3d/reviews/20261003/water-quality-scope"),"canonical",1831,2866,57),
          ("rejected-hq",Path("opentt3d/reviews/20261003/water-quality-scope"),"hq-rejected-candidate",1915,2950,141),
          ("rejected-hq-lock",prior_root,"candidate",1963,2998,189))
# Read exact frozen original inventories/catalogues; never compile working HQ art.
catalogues = {"canonical":root / "playable-release42-independent-extracted/OpenTT3D.app/Contents/Resources/baseset/opentt3d-voxels.json",
              "rejected-hq":root / "breadth-original-hq-medium-perimeter-owner-catalogue.json",
              "rejected-hq-lock":prior_root / "separate-rejected-hq-lock-catalogue.json.gz"}
review_paths = {"canonical":Path("assets/3d/quality_reviews.json"),
                "rejected-hq":root / "breadth-original-hq-medium-perimeter-owner-combined-rejected-reviews.json",
                "rejected-hq-lock":prior_root / "candidate-combined-reviews.json"}
summaries = []
for name,retained,stem,models,expected_rows,expected_reviews in scopes:
    inventory_path = retained / (stem+"-inventory.json")
    quality_path = retained / (stem+"-quality.json")
    original = json.loads(inventory_path.read_text())
    updated = dict(original,water_structures=new_water)
    path = catalogues[name]
    payload = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    catalogue = json.loads(payload)
    assert len(catalogue["models"]) == models and updated["voxel_bindings"] == catalogue["bindings"]
    assert original["voxel_models"] == updated["voxel_models"]
    inventory_out = out / (name+"-inventory.json")
    inventory_out.write_text(json.dumps(updated,indent=2)+"\n")
    report = out / (name+"-quality.json")
    ratings = out / (name+"-ratings.csv")
    with (out / (name+"-required-eight.log")).open("x") as log:
        result = subprocess.run(["python3","tools/assets/quality_audit.py","--catalogue","/dev/stdin",
            "--inventory",str(inventory_out),"--reviews",str(review_paths[name]),"--output",str(report),"--csv",str(ratings),"--require-eight"],
            input=payload,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 1
    audited = json.loads(report.read_text())
    assert len(audited["models"]) == expected_rows and not audited["meets_objective"] and len(audited["coverage_gaps"]) == 4
    assert not any(row["score"] >= 8 for row in audited["models"])
    assert sum(row["status"] == "individually-reviewed" for row in audited["models"]) == expected_reviews
    assert not any(row["status"] in ("stale-review","stale-evidence") for row in audited["models"])
    previous = {row["model"]:row for row in json.loads(quality_path.read_text())["models"]}
    current = {row["model"]:row for row in audited["models"]}
    assert current.keys()-previous.keys() == new_names and previous.keys() <= current.keys()
    for key,old_row in previous.items():
        row = current[key]
        for field in ("fingerprint","score","status","owners","checks","evidence","required_runtime_review"):
            assert old_row[field] == row[field], (name,key,field)
        for field in ("evidence_sha256","defects"):
            assert old_row.get(field) == row.get(field), (name,key,field)
    assert b"\r" not in ratings.read_bytes()
    with ratings.open(newline="") as stream:
        assert len(list(csv.DictReader(stream))) == expected_rows
    summaries.append({"scope":name,"authored_models":models,"ledger_entries":expected_rows,"individual_records":expected_reviews,
        "prior_rows_and_reviews_exact":len(previous),"new_unresolved_ground_rows":20,"require_eight_exit":1,"approvals":0,
        "catalogue_sha256":hashlib.sha256(payload).hexdigest(),"inventory_sha256":digest(inventory_out),"quality_sha256":digest(report),
        "ratings_sha256":digest(ratings),"prior_inventory":str(inventory_path),"prior_inventory_sha256":digest(inventory_path),
        "prior_quality":str(quality_path),"prior_quality_sha256":digest(quality_path),"review_input":str(review_paths[name]),"reviews_sha256":digest(review_paths[name])})
shutil.copy2("opentt3d/MODEL_RATINGS.csv",out / "prior-working-ratings.csv")
shutil.copy2(out / "rejected-hq-lock-ratings.csv","opentt3d/MODEL_RATINGS.csv")
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scopes":summaries,
    "original_water_owner_selector_rows":564,"old_water_rows_exact":544,"new_river_ground_rows":20,
    "runtime_geometry_bindings_and_recommended42_unchanged":True,"approvals":0,
    "scope":"Additive conservative quality scope:20 original CF_RIVER_SLOPE flat/sloped ground climate selectors remain unresolved, because selected ground can include raised artwork as well as independently animated water. No source classification is inferred from dynamic IDs, source size or ground draw role. All prior rows/fingerprints/ratings/checks/evidence/bindings are preserved; intentional original absences still forbid invented features. Zero structural or animation/ship/custom-family acceptance."}
(out / "verification.json").write_text(json.dumps(summary,indent=2)+"\n")
shutil.copy2(Path(__file__),out / "reproduce-quality-scopes.py")
print(json.dumps({"scopes":summaries,"approvals":0}))

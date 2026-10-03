"""Refresh all three ledgers against the observed selector source, without approvals/bindings."""
from pathlib import Path
import csv, datetime, gzip, hashlib, json, shutil, subprocess, sys

sys.path.insert(0,"tools/assets")
from original_water import catalogue as water_catalogue

root = Path("build-macos")
out = root / "breadth-original-river-selector-current-quality"
assert not out.exists()
out.mkdir()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
prior_root = Path("opentt3d/reviews/20261003/river-ground-quality-scope")
new_water = water_catalogue()
scopes = (("canonical",1831,2866,57,root / "playable-release42-independent-extracted/OpenTT3D.app/Contents/Resources/baseset/opentt3d-voxels.json",Path("assets/3d/quality_reviews.json")),
          ("rejected-hq",1915,2950,141,root / "breadth-original-hq-medium-perimeter-owner-catalogue.json",root / "breadth-original-hq-medium-perimeter-owner-combined-rejected-reviews.json"),
          ("rejected-hq-lock",1963,2998,189,Path("opentt3d/reviews/20261003/water-front-and-river-study/separate-rejected-hq-lock-catalogue.json.gz"),Path("opentt3d/reviews/20261003/water-front-and-river-study/candidate-combined-reviews.json")))
summaries = []
for name,models,expected_rows,individual,catalogue_path,reviews in scopes:
    previous_inventory = json.loads((prior_root / (name+"-inventory.json")).read_text())
    scope = dict(previous_inventory,water_structures=new_water)
    payload = gzip.decompress(catalogue_path.read_bytes()) if catalogue_path.suffix == ".gz" else catalogue_path.read_bytes()
    compiled = json.loads(payload)
    assert len(compiled["models"]) == models and compiled["bindings"] == scope["voxel_bindings"]
    inventory = out / (name+"-inventory.json")
    inventory.write_text(json.dumps(scope,indent=2)+"\n")
    report,ratings = out / (name+"-quality.json"),out / (name+"-ratings.csv")
    with (out / (name+"-required-eight.log")).open("x") as log:
        result = subprocess.run(["python3","tools/assets/quality_audit.py","--catalogue","/dev/stdin","--inventory",str(inventory),
            "--reviews",str(reviews),"--output",str(report),"--csv",str(ratings),"--require-eight"],input=payload,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 1
    current = json.loads(report.read_text())
    assert len(current["models"]) == expected_rows and not current["meets_objective"] and len(current["coverage_gaps"]) == 4
    assert not any(row["score"] >= 8 or row["status"] in ("stale-review","stale-evidence") for row in current["models"])
    assert sum(row["status"] == "individually-reviewed" for row in current["models"]) == individual
    prior = {row["model"]:row for row in json.loads((prior_root / (name+"-quality.json")).read_text())["models"]}
    actual = {row["model"]:row for row in current["models"]}
    assert actual.keys() == prior.keys()
    changed = []
    for key,row in actual.items():
        old = prior[key]
        for field in ("score","status","owners","checks","evidence","required_runtime_review","notes","defects","evidence_sha256"):
            assert old.get(field) == row.get(field),(name,key,field)
        if old["fingerprint"] != row["fingerprint"]:
            assert row["status"] != "individually-reviewed"
            assert key.startswith(("missing/lock/","original/lock/","original/water-slope/","unresolved/river-bank/","unresolved/river-ground/","procedural/","original/object/"))
            changed.append(key)
    assert b"\r" not in ratings.read_bytes()
    with ratings.open(newline="") as stream:
        assert len(list(csv.DictReader(stream))) == expected_rows
    summaries.append({"scope":name,"models":models,"ledger_entries":expected_rows,"individual_records":individual,
        "required_eight_exit":1,"approvals":0,"ratings_checks_and_evidence_exact":expected_rows,
        "updated_source_or_renderer_fingerprints":changed,"catalogue_sha256":hashlib.sha256(payload).hexdigest(),
        "inventory_sha256":digest(inventory),"quality_sha256":digest(report),"ratings_sha256":digest(ratings)})
shutil.copy2("opentt3d/MODEL_RATINGS.csv",out / "prior-working-ratings.csv")
shutil.copy2(out / "rejected-hq-lock-ratings.csv","opentt3d/MODEL_RATINGS.csv")
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scopes":summaries,"approvals":0,
    "scope":"Read-only source/renderer fingerprint refresh after actual callback observation hooks. Every prior model/row/rating/defect/check/evidence/binding stays unchanged; original water and other renderer-coupled pending fingerprints follow the changed source bytes. Observed source/absence/strict world equality establishes no raised volume, terrain/water decomposition, animation, ships or 8/10 acceptance. Working CSV remains the rejected HQ+lock scope, not release artwork."}
(out / "verification.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"scopes":[{key:row[key] for key in ("scope","models","ledger_entries","individual_records","required_eight_exit","approvals")} for row in summaries]}))

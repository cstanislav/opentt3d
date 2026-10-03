"""Seal individually inspected negative lock studies and prove changed lamps stale reviews."""
from pathlib import Path
from collections import Counter
import datetime, hashlib, json, shutil, subprocess, sys

sys.path.insert(0,"tools/assets")
from quality_audit import fingerprint

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/lock-studies-rejected")
freeze = root / "breadth-original-lock-authored-study-frozen-build"
repaired = root / "breadth-original-lock-open-lamp-frozen-build"
compiled = json.loads((freeze / "baseset/opentt3d-voxels.json").read_text())
new_compiled = json.loads((repaired / "baseset/opentt3d-voxels.json").read_text())
names = {name for name in compiled["models"] if name.startswith("lock_study_")}
decisions = json.loads((root / "breadth-original-lock-individual-rejections.json").read_text())["decisions"]
assert len(names) == len(decisions) == 48 and {row["model"] for row in decisions} == names
assert Counter(row["score"] for row in decisions) == {5:28,6:20}
index = {row["model"]:row for row in json.loads((root / "breadth-original-lock-authored-study-sheets/index.json").read_text())}
assert index.keys() == names
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()


def copy(source,target):
    assert not target.exists(), target
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert digest(source) == digest(target)


strict = json.loads((root / "breadth-original-lock-authored-study-strict.json").read_text())
assert strict["images"] == 432 and len(strict["differences"]) == 8 and sum(row["changed_pixels"] for row in strict["differences"]) == 8
assert not any(row["name"].endswith("-native") for row in strict["differences"])
failed_models = {row["name"].removeprefix("model-voxel-").rsplit("-",1)[0] for row in strict["differences"]}
reviews = {"format":1,"models":{},"scope":"Individually inspected first frozen unbound48-model lock studies only; negative/provisional scores, no runtime coverage or acceptance. Native equality is not wider-backend acceptance; changed lamp artwork invalidates its prior individual decision."}
for decision in decisions:
    name = decision["model"]
    row = index[name]
    sheet = out / "owners" / (name+".png")
    copy(Path(row["sheet"]),sheet)
    assert digest(sheet) == row["sheet_sha256"]
    for evidence,expected in row["evidence_sha256"].items():
        assert digest(Path(evidence)) == expected
    defects = decision["defects"] + [
        "No runtime lock binding or actual joined saved/rendered wall family establishes this unbound study's original ownership.",
        "Doubled-terrain support without object inflation, source-continuous independent water phases, complete custom fallback and real ship clearance remain unproved.",
    ]
    if name in failed_models:
        defects.append("Its street silhouette differs by one pixel across backends; strict renderer equality is rejected.")
    reviews["models"][name] = {"score":decision["score"],"fingerprint":fingerprint(compiled["models"][name],compiled["materials"]),
        "checks":{check:False for check in ("source","orbit","street","world","states","consistency")},
        "inspection_completed":["actual-own-source","registered-native","orbit0..3","street0..3"],
        "evidence":[str(sheet)],"evidence_sha256":{str(sheet):digest(sheet)},"defects":defects,
        "notes":[f"Individually inspected original part{row['part']} direction{row['direction']} {row['face']} elevation{row['elevation']}; unbound study, not approved."]+defects,
        "original_owner":row["source"],"runtime_bound":False}
(out / "prototype-quality-reviews.json").write_text(json.dumps(reviews,indent=2)+"\n")
for source,name in ((freeze / "authored-source.json","first-authored-source.json"),(freeze / "compiler-snapshot.py","experimental-compiler-snapshot.py"),
    (freeze / "manifest.json","first-frozen-build-manifest.json"),(repaired / "authored-source.json","lamp-open-candidate-source.json"),
    (repaired / "manifest.json","lamp-open-candidate-manifest.json")):
    copy(source,out / name)
for name in ("breadth-original-lock-individual-rejections.json","breadth-original-lock-authored-study-original-controls.py",
    "breadth-original-lock-authored-study-controls.log","breadth-original-lock-authored-study-runs.json","breadth-original-lock-authored-study-strict.json",
    "breadth-original-lock-authored-study-strict-rejection.md","breadth-original-lock-authored-study-sheets.py","breadth-original-lock-authored-study-sheets.log",
    "breadth-original-lock-open-lamp-controls.log","breadth-original-lock-open-lamp-runs.json","breadth-original-lock-open-lamp-strict.json",
    "breadth-original-lock-open-lamp-verification.json"):
    copy(root / name,out / name)
for name in ("model-voxel-lock_study_lower_se_rear_sea-native-preview.png","model-voxel-lock_study_lower_se_rear_sea-0-preview.png"):
    copy(root / "breadth-original-lock-open-lamp-vulkan/renderer3d-reference" / name,out / "lamp-open-previews" / name)
for mode in ("breadth-original-lock-authored-study","breadth-original-lock-open-lamp"):
    for backend in ("vulkan","opengl"):
        for name in ("result.json","run.log","screenshot/smoke.png"):
            copy(root / f"{mode}-{backend}" / name,out / "native-controls" / f"{mode}-{backend}" / name)

baseline = json.loads((root / "breadth-original-hq-medium-perimeter-owner-catalogue.json").read_text())
prior_reviews = json.loads((root / "breadth-original-hq-medium-perimeter-owner-combined-rejected-reviews.json").read_text())
assert not (prior_reviews["models"].keys() & names)
prior_reviews["models"].update(reviews["models"])
combined_reviews = root / "breadth-original-lock-first-study-combined-reviews.json"
assert not combined_reviews.exists()
combined_reviews.write_text(json.dumps(prior_reviews,indent=2)+"\n")
summaries = []
for mode,catalogue in (("first-rejected",compiled),("lamp-open-unapproved",new_compiled)):
    merged = json.loads((root / "breadth-original-hq-medium-perimeter-owner-catalogue.json").read_text())
    offset = len(merged["materials"])
    merged["materials"].extend(catalogue["materials"])
    assert len(merged["materials"]) <= 65535
    for name in sorted(names):
        model = json.loads(json.dumps(catalogue["models"][name]))
        for run in model["runs"]:
            run[4] += offset
        merged["models"][name] = model
    assert len(merged["models"]) == 1979 and merged["bindings"] == baseline["bindings"]
    assert all(fingerprint(model,baseline["materials"]) == fingerprint(merged["models"][name],merged["materials"]) for name,model in baseline["models"].items())
    prefix = f"breadth-original-lock-{mode}-combined"
    path = root / (prefix+"-catalogue.json")
    assert not path.exists()
    path.write_text(json.dumps(merged,separators=(",",":"))+"\n")
    inventory = root / (prefix+"-inventory.json")
    with (root / (prefix+"-inventory.log")).open("x") as log:
        subprocess.run(["python3","tools/assets/inventory.py","--catalogue",str(path),"--output",str(inventory)],check=True,stdout=log,stderr=subprocess.STDOUT)
    report = root / (prefix+"-quality.json")
    csv = root / (prefix+"-ratings.csv")
    with (root / (prefix+"-quality.log")).open("x") as log:
        result = subprocess.run(["python3","tools/assets/quality_audit.py","--catalogue",str(path),"--inventory",str(inventory),
            "--reviews",str(combined_reviews),"--output",str(report),"--csv",str(csv),"--require-eight"],stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 1
    quality = json.loads(report.read_text())
    assert len(quality["models"]) == 2978 and not quality["meets_objective"] and not any(row["score"] >= 8 for row in quality["models"])
    stale = {row["model"] for row in quality["models"] if row["status"] == "stale-review"}
    assert stale == (set() if mode == "first-rejected" else {name for name in names if "_lower_" in name and name.endswith("_sea")})
    assert sum(row["status"] == "individually-reviewed" for row in quality["models"]) == (189 if mode == "first-rejected" else 181)
    for suffix in ("inventory.json","quality.json","ratings.csv","quality.log"):
        copy(root / (prefix+"-"+suffix),out / (mode+"-"+suffix))
    summaries.append({"scope":mode,"models":1979,"runtime_bindings_unchanged":True,"ledger_entries":2978,
        "individual_records":189 if mode == "first-rejected" else 181,"stale_changed_lamps":len(stale),
        "require_eight_exit":result.returncode,"approvals":0,"catalogue_sha256":digest(path),"quality_sha256":digest(report)})
summary = {"reviewed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"individual_first_study_records":48,
    "scores":dict(Counter(row["score"] for row in decisions)),"all_acceptance_checks":False,"approvals":0,
    "native_pairs_exact":48,"strict_wider_differences":8,"strict_wider_pixels":8,"quality_scopes":summaries,
    "released1831_models_and_bindings_unchanged":True,"scope":reviews["scope"]}
(out / "verification.json").write_text(json.dumps(summary,indent=2)+"\n")
copy(Path(__file__),out / "reproduce-individual-rejections.py")
files = {str(path):digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files":files,"scope":reviews["scope"]},indent=2)+"\n")
print(json.dumps(summary))

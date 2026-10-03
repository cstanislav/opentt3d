"""Seal individual repair-study defects, failed rendering hypotheses and actual river sources."""
from pathlib import Path
import datetime, gzip, hashlib, json, shutil, subprocess, sys

sys.path.insert(0,"tools/assets")
from inventory import inventory
from quality_audit import fingerprint

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/water-front-and-river-study")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()


def copy(source,target):
    assert not target.exists(), target
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert digest(source) == digest(target)


for name,count in (("breadth-original-river-selected-source-working-assets.log",252),
                   ("breadth-original-river-selected-source-clean-tests.log",236),
                   ("breadth-original-lock-front-profile-harness-tests.log",99)):
    assert f"Ran {count} tests" in (root / name).read_text() and "\nOK\n" in (root / name).read_text()
assert "100% tests passed, 0 tests failed out of 213" in (root / "breadth-original-lock-projection-restored-native-tests.log").read_text()
for name in ("src/renderer3d/gl_backend.cpp","src/renderer3d/shaders/vk_world.vert"):
    assert Path(name).read_bytes() == (root / "breadth-original-lock-projection-original-snapshot" / name).read_bytes()
    assert Path(name).read_bytes() == subprocess.check_output(["git","show",f"HEAD:{name}"])
assert not subprocess.check_output(["git","diff","--name-only","--","src"],text=True).strip()

freeze = root / "breadth-original-lock-front-profile-frozen-build"
compiled = json.loads((freeze / "baseset/opentt3d-voxels.json").read_text())
first = json.loads((root / "breadth-original-lock-authored-study-frozen-build/baseset/opentt3d-voxels.json").read_text())
names = {name for name in compiled["models"] if name.startswith("lock_study_")}
changed = {name for name in names if fingerprint(compiled["models"][name],compiled["materials"]) != fingerprint(first["models"][name],first["materials"])}
assert len(names) == 48 and len(changed) == 28
decisions = json.loads((root / "breadth-original-lock-front-profile-decisions.json").read_text())["decisions"]
assert len(decisions) == 28 and {row["model"] for row in decisions} == changed
assert all(row["score"] == 6 and row["defects"] for row in decisions)
index = {row["model"]:row for row in json.loads((root / "breadth-original-lock-front-profile-sheets/index.json").read_text())}
assert index.keys() == names
old_reviews = json.loads(Path("opentt3d/reviews/20261003/lock-studies-rejected/prototype-quality-reviews.json").read_text())
decisions_by_name = {row["model"]:row for row in decisions}
strict = json.loads((root / "breadth-original-lock-front-profile-strict.json").read_text())
assert strict["images"] == 432 and len(strict["differences"]) == 8 and sum(row["changed_pixels"] for row in strict["differences"]) == 8
assert not any(row["name"].endswith("-native") for row in strict["differences"])
failed_models = {row["name"].removeprefix("model-voxel-").rsplit("-",1)[0] for row in strict["differences"]}
reviews = {"format":1,"models":{},"scope":"Defect-bearing unbound lock repair studies only;28 explicit re-inspections and20 unchanged original conservative decisions with exact images. No inherited acceptance or runtime coverage."}
for name in sorted(names):
    row = index[name]
    sheet = out / "owners" / (name+".png")
    copy(Path(row["sheet"]),sheet)
    for source,expected in row["evidence_sha256"].items():
        assert digest(Path(source)) == expected
    value = fingerprint(compiled["models"][name],compiled["materials"])
    if name in changed:
        defects = decisions_by_name[name]["defects"] + [
            "Unbound study: actual joined wall/terrain support, complete original fallback, independent animated water phases and real ship passage/clearance remain unproved."
        ]
        if name in failed_models:
            defects.append("Its street silhouette still differs by one pixel across backends; strict acceptance remains rejected.")
    else:
        prior = old_reviews["models"][name]
        assert prior["fingerprint"] == value and prior["score"] == 6
        assert not any(prior["checks"].values())
        defects = prior["defects"]
    reviews["models"][name] = {"score":6,"fingerprint":value,
        "checks":{check:False for check in ("source","orbit","street","world","states","consistency")},
        "evidence":[str(sheet)],"evidence_sha256":{str(sheet):digest(sheet)},"defects":defects,
        "notes":[f"Original part{row['part']} direction{row['direction']} {row['face']} elevation{row['elevation']}: {'explicitly re-inspected after repair' if name in changed else 'unchanged conservative review and exact nine-view evidence'}; unbound, not approved."]+defects,
        "original_owner":row["source"],"runtime_bound":False,"new_source_native_orbit_street_inspection":name in changed}
(out / "prototype-quality-reviews.json").write_text(json.dumps(reviews,indent=2)+"\n")

baseline = json.loads((root / "breadth-original-hq-medium-perimeter-owner-catalogue.json").read_text())
merged = json.loads((root / "breadth-original-hq-medium-perimeter-owner-catalogue.json").read_text())
assert len(baseline["models"]) == 1915 and not (baseline["models"].keys() & names)
offset = len(merged["materials"])
merged["materials"].extend(compiled["materials"])
assert len(merged["materials"]) <= 65535
for name in names:
    model = json.loads(json.dumps(compiled["models"][name]))
    for run in model["runs"]:
        run[4] += offset
    merged["models"][name] = model
assert len(merged["models"]) == 1963 and merged["bindings"] == baseline["bindings"]
assert all(fingerprint(model,baseline["materials"]) == fingerprint(merged["models"][name],merged["materials"]) for name,model in baseline["models"].items())
serialised = json.dumps(merged,separators=(",",":"))+"\n"
catalogue_hash = hashlib.sha256(serialised.encode()).hexdigest()
archive = out / "separate-rejected-hq-lock-catalogue.json.gz"
archive.write_bytes(gzip.compress(serialised.encode(),mtime=0))
assert hashlib.sha256(gzip.decompress(archive.read_bytes())).hexdigest() == catalogue_hash
scope = inventory(merged)
(out / "candidate-inventory.json").write_text(json.dumps(scope,indent=2)+"\n")
combined = json.loads((root / "breadth-original-hq-medium-perimeter-owner-combined-rejected-reviews.json").read_text())
assert not (combined["models"].keys() & names)
combined["models"].update(reviews["models"])
(out / "candidate-combined-reviews.json").write_text(json.dumps(combined,indent=2)+"\n")
with (out / "candidate-required-eight.log").open("x") as log:
    # Keep a byte-exact compressed catalogue instead of another80MiB duplicate.
    result = subprocess.run(["python3","tools/assets/quality_audit.py","--catalogue","/dev/stdin",
        "--inventory",str(out / "candidate-inventory.json"),"--reviews",str(out / "candidate-combined-reviews.json"),
        "--output",str(out / "candidate-quality.json"),"--csv",str(out / "candidate-ratings.csv"),"--require-eight"],
        input=serialised,text=True,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode == 1
quality = json.loads((out / "candidate-quality.json").read_text())
assert len(quality["models"]) == 2978 and not quality["meets_objective"] and not any(row["score"] >= 8 for row in quality["models"])
assert sum(row["status"] == "individually-reviewed" for row in quality["models"]) == 189
assert not any(row["status"] == "stale-review" for row in quality["models"])
copy(Path("opentt3d/MODEL_RATINGS.csv"),out / "prior-working-ratings.csv")
shutil.copy2(out / "candidate-ratings.csv","opentt3d/MODEL_RATINGS.csv")

for name in ("breadth-original-lock-front-profile-controls.log","breadth-original-lock-front-profile-runs.json",
    "breadth-original-lock-front-profile-verification.json","breadth-original-lock-front-profile-strict.json",
    "breadth-original-lock-front-profile-preservation.json","breadth-original-lock-front-profile-decisions.json",
    "breadth-original-lock-authored-study-controls.py","breadth-original-lock-authored-study-sheets.py",
    "breadth-original-lock-canonical-projection-controls.py","breadth-original-lock-canonical-projection-build.log",
    "breadth-original-lock-canonical-projection-native-tests.log","breadth-original-lock-canonical-projection-controls.log",
    "breadth-original-lock-canonical-projection-runs.json","breadth-original-lock-canonical-projection-verification.json",
    "breadth-original-lock-canonical-projection-paired-strict.json","breadth-original-lock-canonical-projection-vulkan-prior-strict.json",
    "breadth-original-lock-canonical-projection-opengl-prior-strict.json","breadth-original-lock-canonical-projection-rejection.md",
    "breadth-original-lock-projection-restored-build.log","breadth-original-lock-projection-restored-native-tests.log",
    "breadth-original-lock-front-profile-harness-tests.log","breadth-original-lock-raster-software-clip-command.log",
    "breadth-original-lock-raster-software-clip-strict.json","breadth-original-river-selected-source-verification.json",
    "breadth-original-river-selected-source-audit.py","breadth-original-river-selected-source-focused-tests.log",
    "breadth-original-river-selected-source-working-assets.log","breadth-original-river-selected-source-clean-tests.log",
    "breadth-original-river-selected-source-clean-test-receipt.json","breadth-original-river-selected-source-clean-tests.py"):
    copy(root / name,out / name)
for source,target in ((freeze / "authored-source.json",out / "authored-source.json"),
    (freeze / "compiler-snapshot.py",out / "experimental-compiler-snapshot.py"),(freeze / "manifest.json",out / "front-profile-frozen-manifest.json"),
    (root / "breadth-original-lock-canonical-projection-frozen-build/manifest.json",out / "rejected-projection-frozen-manifest.json")):
    copy(source,target)
for path in (root / "breadth-original-lock-canonical-projection-frozen-build/source-snapshot").rglob("*"):
    if path.is_file():
        copy(path,out / "rejected-projection-source" / path.relative_to(root / "breadth-original-lock-canonical-projection-frozen-build/source-snapshot"))
for name in ("tools/assets/live_water.py","tools/assets/test_live_river.py"):
    copy(Path(name),out / "source-snapshot" / name)
for mode in ("breadth-original-lock-front-profile","breadth-original-lock-canonical-projection"):
    for backend in ("vulkan","opengl"):
        for name in ("result.json","run.log","screenshot/smoke.png"):
            copy(root / f"{mode}-{backend}" / name,out / "native-controls" / f"{mode}-{backend}" / name)
for name in ("result.json","run.log"):
    copy(root / "breadth-original-lock-raster-software-clip-opengl" / name,out / "native-controls/software-clip-opengl" / name)

river = json.loads((root / "breadth-original-river-selected-source-verification.json").read_text())
assert river["callback_source_states_exact"] == 19 and river["new_native_controls"] == 0
image_map = {(Path(row["portable_image"]).parts[-2],row["sha256"]):Path(row["portable_image"])
             for row in json.loads(Path("opentt3d/reviews/20261003/water-live-selectors/source-file-map.json").read_text())}
river_files = {}
for climate,selection in river["selected_sources"].items():
    for source in selection["selected_ground_sources"]:
        image = image_map[climate,source["source_image_sha256"]]
        assert digest(image) == source["source_image_sha256"]
        target = out / "river-sources" / climate / image.name
        if not target.exists():
            copy(image,target)
        river_files[str(target)] = source["source_image_sha256"]
(out / "river-source-files.json").write_text(json.dumps(river_files,indent=2)+"\n")
summary = {"sealed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"changed_studies_reinspected":28,
    "unchanged_original_decisions_and_views_exact":20,"lock_studies":48,"scores":{"6":48},"approvals":0,
    "all_acceptance_checks":False,"strict_wider_different_images":8,"strict_wider_different_pixels":8,
    "temperate_worlds_strict_exact":2,"incidental_river_source_states_exact":19,"incidental_river_tiles":9,
    "river_feature_offsets_or_absences_resolved":False,"runtime_cpp_sources_restored_exact":True,
    "runtime_build_binary_sha256":digest(root / "opentt3d"),"runtime_working_catalogue_sha256":digest(root / "baseset/opentt3d-voxels.json"),
    "runtime_build_is_exact_tag_or_approved_artwork":False,"native_tests":213,"working_asset_tests":252,
    "isolated_committed_artwork_tests":236,"harness_tests":99,"candidate_models":1963,"candidate_ledger_entries":2978,
    "individual_records":189,"required_eight_exit":1,"candidate_catalogue_uncompressed_sha256":catalogue_hash,
    "recommended_release_unchanged":"opentt3d-dev-20261003.42","scope":reviews["scope"]}
(out / "verification.json").write_text(json.dumps(summary,indent=2)+"\n")
copy(Path(__file__),out / "reproduce-portable-evidence.py")
files = {str(path):digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files":files,"scope":reviews["scope"]},indent=2)+"\n")
print(json.dumps(summary))

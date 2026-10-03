"""Seal natural sources, strict preservation, rejected origin study and reversible compaction."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess
from PIL import Image

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/river-natural-selector-breadth")
assert not (out / "evidence-sha256.json").exists()
out.mkdir(parents=True,exist_ok=True)
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()


def copy(source,target):
    assert not target.exists(),target
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert digest(source) == digest(target)


natural = json.loads((root / "breadth-original-river-natural-selector-verification.json").read_text())
matrix = json.loads((root / "breadth-original-river-natural-selector-matrix.json").read_text())
wide = json.loads((root / "breadth-original-river-selector-wide-selector-matrix.json").read_text())
assert natural["quiet_native_controls"] == 40 and natural["strict_world_images"] == 20 and natural["strict_world_changed_pixels"] == 0
assert natural["ground_owner_states_exact_per_base_set"] == 1466 and natural["bank_owner_states_exact_per_base_set"] == 2783
assert matrix["ground_selector_climates_observed_per_base_set"] == 20 and matrix["bank_input_selector_climates_observed_per_base_set"] == {"classic":80,"opengfx":80}
assert matrix["actual_absent_edge_features"] == 0 and matrix["original_source_heights_observed"] == list(range(0,57,8))
assert wide["prior_common_owner_states_exact"] == 1353 and wide["new_wider_owner_states"] == 1614
assert "100% tests passed, 0 tests failed out of 213" in (root / "breadth-original-lock-raster-origin-restored-native-tests.log").read_text()
harness = (root / "breadth-original-river-natural-final-harness-tests.log").read_text()
assert "Ran 104 tests" in harness and "\nOK\n" in harness
quality = json.loads((root / "breadth-original-river-natural-quality-preservation.json").read_text())
assert quality["src_delta_empty"] and quality["working_candidate_csv_untouched"] and all(row["quality_report_word_exact"] for row in quality["scopes"])
assert not subprocess.check_output(["git","diff","--name-only","--","src"],text=True).strip()
origin = json.loads((root / "breadth-original-lock-raster-origin-retry2-verification.json").read_text())
assert origin["comparisons"][-1]["exit_code"] == 0 and origin["comparisons"][-1]["different_pixels"] == 0
assert origin["world_comparisons"][-1]["different_pixels"] == 7
restored = json.loads((root / "breadth-original-lock-raster-origin-restoration.json").read_text())
assert restored["original_source_restored_byte_exact"] and not restored["accepted_renderer_repair"]
assert digest(Path(restored["file"])) == restored["sha256"]

fixtures = [(climate,root / ("breadth-original-river-natural-survey-"+climate)) for climate in ("temperate","arctic","tropic","toyland")]
fixtures.append(("tropic",root / "breadth-original-river-natural-survey-tropic-seed161803"))
for climate,fixture in fixtures:
    payload = json.loads((fixture / "fixture.json").read_text())
    assert digest(fixture / payload["save"]) == payload["save_sha256"]
    target = out / "public-surveys" / fixture.name
    for name in ("fixture.json","run.log","command-acknowledgements.json","openttd.cfg",payload["save"]):
        copy(fixture / name,target / name)
    for path in (fixture / "ai").rglob("*"):
        if path.is_file(): copy(path,target / path.relative_to(fixture))
for family,directory in (("classic","breadth-original-river-selector1831-frozen-build"),
                         ("opengfx","breadth-original-river-selector-opengfx1831-frozen-build")):
    copy(root / directory / "manifest.json",out / (family+"-frozen-manifest.json"))

all_outputs,source_map = set(),[]
for family,filename in (("natural","breadth-original-river-natural-selector-runs.json"),("wide","breadth-original-river-selector-wide-runs.json")):
    runs = json.loads((root / filename).read_text())
    assert len(runs) == (40 if family == "natural" else 8) and all(row["exit_code"] == 0 for row in runs)
    for row in runs:
        output = Path(row["output"])
        all_outputs.add(output.name)
        target = out / "native-controls" / output.name
        for name in ("result.json","run.log","screenshot/smoke.png"):
            copy(output / name,target / name)
        assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
        directory = output / "renderer3d-reference"
        selectors = directory / "river-selectors.json"
        assert selectors.exists() == row["tracing"]
        if not row["tracing"]: continue
        copy(selectors,target / "river-selectors.json")
        if (directory / "water-live.json").exists(): copy(directory / "water-live.json",target / "water-live.json")
        for source in json.loads(selectors.read_text())["observations"]:
            assert not source["absent"]
            image = directory / source["source_image"]
            value = digest(image)
            destination = out / "sources" / family / row.get("family","classic") / row["climate"] / (value+".pam")
            if not destination.exists(): copy(image,destination)
            source_map.append({"scope":family,"base_set_family":row.get("family","classic"),"climate":row["climate"],"seed":row.get("seed",314159),
                "backend":row["backend"],"tile":source["tile"],"feature":source["feature"],"requested_offset":source["requested_offset"],
                "resolved_offset":source["resolved_offset"],"selected_sprite":source["selected_sprite"],"source_height":source["source_height"],
                "original_image":str(image),"portable_image":str(destination),"sha256":value})
assert sum(row["scope"] == "natural" for row in source_map) == 16996
assert sum(row["scope"] == "wide" for row in source_map) == 5934
(out / "source-file-map.json").write_text(json.dumps(source_map,indent=2)+"\n")

for row in json.loads((root / "breadth-original-lock-raster-origin-retry2-runs.json").read_text()):
    assert row["exit_code"] == 0
    output = Path(row["output"])
    all_outputs.add(output.name)
    for name in ("result.json","run.log","screenshot/smoke.png"):
        copy(output / name,out / "raster-study/native-controls" / output.name / name)
failed = root / "breadth-original-lock-raster-origin-opengl-default"
for path in failed.rglob("*"):
    if path.is_file() and not any(part in ("lang","baseset") for part in path.relative_to(failed).parts):
        copy(path,out / "retained-failures/full-suite-timeout" / path.relative_to(failed))
copy(root / "breadth-original-lock-raster-origin-frozen-build/manifest.json",out / "raster-study/frozen-manifest.json")
for prefix,destination in (("breadth-original-lock-raster-origin-frozen-build/source-snapshot","raster-study/diagnostic-source"),
                           ("breadth-original-lock-raster-origin-original-snapshot","raster-study/pre-edit-source")):
    for path in (root / prefix).rglob("*"):
        if path.is_file(): copy(path,out / destination / path.relative_to(root / prefix))

compaction_rows,total_compacted,total_saved = [],0,0
for path in sorted(root.glob("review-compaction-*.json")):
    evidence = json.loads(path.read_text())
    # Only the current controls and the two explicitly scoped compaction operations.
    previous = path.name in ("review-compaction-20261003T214157175234Z.json","review-compaction-20261003T214904499862Z.json")
    chosen = [row for row in evidence["images"] if Path(row["image"]).parts[0] in all_outputs]
    if not previous and not chosen: continue
    assert not evidence["preserved_errors"]
    copy(path,out / "compaction" / path.name)
    for row in evidence["images"] if previous else chosen:
        png = root / row["image"]
        with Image.open(png) as image:
            assert image.mode == "RGBA"
            assert hashlib.sha256(image.info["opentt3d_pam_header"].encode("ascii")+image.tobytes()).hexdigest() == row["pam_sha256"]
        value = dict(row,pam_reconstruction_sha256_exact=True,png_sha256=digest(png))
        if row in chosen:
            target = out / "lossless-native-captures" / Path(row["image"]).parts[0] / png.name
            copy(png,target)
            value["portable_png"] = str(target)
        else:
            value["preserved_local_png"] = str(png)
        compaction_rows.append(value)
        total_compacted += 1
        total_saved += row["raw_bytes"]-row["png_bytes"]
(out / "compaction/reconstruction-verification.json").write_text(json.dumps(compaction_rows,indent=2)+"\n")
assert sum("portable_png" in row for row in compaction_rows) == 1524

for path in (root / "breadth-original-river-natural-source-sheets-registered").iterdir():
    copy(path,out / "registered-source-sheets" / path.name)
for pattern in ("breadth-original-river-natural-*.py","breadth-original-river-natural-*.log","breadth-original-river-natural-*.json",
                "breadth-original-river-selector-wide-*.py","breadth-original-river-selector-wide-*.log","breadth-original-river-selector-wide-*.json",
                "breadth-original-lock-raster-origin-*.py","breadth-original-lock-raster-origin-*.log","breadth-original-lock-raster-origin-*.json",
                "breadth-original-lock-silhouette-localize*.cpp","breadth-original-lock-silhouette-localize*.py",
                "breadth-original-lock-silhouette-localize*.log","breadth-original-lock-silhouette-localize*.json"):
    for path in root.glob(pattern):
        target = out / "reports-and-reproduce" / path.name
        if not target.exists(): copy(path,target)
for name in ("src/water_cmd.cpp","src/script/api/script_tile.cpp","src/renderer3d/camera.hpp","src/renderer3d/geometry.hpp",
             "src/renderer3d/voxel_geometry.hpp","src/renderer3d/sprite_textures.cpp","tools/assets/quality_audit.py",
             "tools/assets/live_river_selectors.py","tools/assets/compact_reviews.py","tools/opentt3d/fixture_rivers.py",
             "tools/opentt3d/test_fixture_rivers.py","tools/opentt3d/fixtures/rivers/main.nut","tools/opentt3d/fixtures/rivers/info.nut"):
    copy(Path(name),out / "source-snapshot" / name)
summary = {"sealed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"quiet_river_controls":48,"original_public_surveys":5,
    "natural_ground_owner_states_exact_per_base_set":1466,"natural_bank_owner_states_exact_per_base_set":2783,
    "ground_selector_climates_observed_per_base_set":20,"bank_input_selector_climates_observed_per_base_set":80,
    "original_source_heights":list(range(0,57,8)),"strict_tracing_world_images":20,"strict_tracing_world_changed_pixels":0,
    "paired_original_source_map_records":len(source_map),"native_source_sheets":8,"complete_registered_source_states_displayed":200,
    "actual_absent_bank_feature_executions":0,"raster_study_native_controls":3,"raster_study_lock_images_exact":432,
    "raster_study_changed_world_pixels":7,"raster_study_paired_world_differences_prior":22,"raster_study_paired_world_differences_after":19,
    "accepted_renderer_repair":False,"restored_runtime_source_byte_exact":True,"native_tests":213,"harness_tests":104,
    "quality_scopes_word_exact":3,"quality_ledger_entries":[2866,2950,2998],"current_individual_records":[57,141,189],
    "approved_models":0,"coverage_gaps":4,"lossless_generated_images_reconstructed":total_compacted,
    "portable_lossless_native_images":1524,"lossless_compaction_recovered_bytes":total_saved,"masks":False,"tolerance":0,
    "runtime_artwork_or_bindings_changed":False,"canonical_models":1831,"recommended_release_unchanged":"opentt3d-dev-20261003.42",
    "scope":"Natural source-selector/height breadth plus a strictly unaccepted raster-origin study, not new runtime 3D coverage or approvals. All original sprite pixels/headers/metadata, saved worlds, failures, rejected studies and conservative model quality are retained. No forced graphics, duplicate callback, raised-water ownership, complete custom-family/phase/ship/performance/platform/input/replay/network or every-model8/10 acceptance; full catalogue goal remains open. Sealing time is not stopping time."}
(out / "verification.json").write_text(json.dumps(summary,indent=2)+"\n")
files = {str(path):digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files":files,"scope":summary["scope"]},indent=2)+"\n")
print(json.dumps(summary))

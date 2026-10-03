"""Seal actual feature selectors, complete originals, failures and strict world controls."""
from pathlib import Path
import datetime, hashlib, json, shutil, sys
from PIL import Image

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/river-live-feature-selectors")
assert not (out / "evidence-sha256.json").exists()
out.mkdir(parents=True,exist_ok=True)
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()


def copy(source,target):
    assert not target.exists(), target
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert digest(source) == digest(target)


classic = json.loads((root / "breadth-original-river-selector-classic-verification.json").read_text())
world = json.loads((root / "breadth-original-river-selector-classic-world-verification.json").read_text())
alternate = json.loads((root / "breadth-original-river-selector-opengfx-verification.json").read_text())
assert classic["total_owner_states_exact"] == 1353 and world["changed_pixels"] == alternate["changed_pixels"] == 0
assert alternate["observed_ground_owner_states_exact"] == 454 and alternate["observed_edge_source_owners"] == 899
assert alternate["absence_expectation_rejected"] and not alternate["actual_absence_control_established"]
for name,count in (("breadth-original-river-selector-working-assets.log",266),
                   ("breadth-original-river-selector-clean-tests.log",250),
                   ("breadth-original-river-selector-harness-tests.log",99)):
    assert f"Ran {count} tests" in (root / name).read_text() and "\nOK\n" in (root / name).read_text()
assert "100% tests passed, 0 tests failed out of 213" in (root / "breadth-original-river-selector-native-tests.log").read_text()
delta = json.loads((root / "breadth-original-river-selector-presentation-delta.json").read_text())
assert len(delta["files"]) == 5 and all(row["original_after_removing_only_read_only_diagnostics_byte_exact"] for row in delta["files"])
for row in delta["files"]:
    assert digest(Path(row["file"])) == row["current_sha256"]
quality = json.loads((root / "breadth-original-river-selector-current-quality/verification.json").read_text())
assert [row["ledger_entries"] for row in quality["scopes"]] == [2866,2950,2998]
assert all(row["required_eight_exit"] == 1 and row["approvals"] == 0 for row in quality["scopes"])
for path in (root / "breadth-original-river-selector-current-quality").iterdir():
    copy(path,out / "quality-scopes" / path.name)

all_runs = []
for family,filename in (("classic","breadth-original-river-selector-runs.json"),
                        ("opengfx","breadth-original-river-selector-opengfx-runs.json"),
                        ("opengfx-prior","breadth-original-river-selector-opengfx-prior-runs.json")):
    rows = json.loads((root / filename).read_text())
    assert all(row["exit_code"] == 0 for row in rows)
    for row in rows:
        all_runs.append((family,row))
assert len(all_runs) == 40
source_files = []
for family,row in all_runs:
    output = Path(row["output"])
    control = out / "native-controls" / output.name
    for name in ("result.json","run.log","screenshot/smoke.png"):
        copy(output / name,control / name)
    assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
    directory = output / "renderer3d-reference"
    manifest = directory / "river-selectors.json"
    assert manifest.exists() == row["tracing"]
    if not row["tracing"]:
        continue
    copy(manifest,control / "river-selectors.json")
    copy(directory / "water-live.json",control / "water-live.json")
    for source in json.loads(manifest.read_text())["observations"]:
        if source["absent"]:
            assert "source_image" not in source
            continue
        image = directory / source["source_image"]
        value = digest(image)
        target = out / "sources" / family / row["climate"] / (value+".pam")
        if not target.exists():
            copy(image,target)
        source_files.append({"family":family,"climate":row["climate"],"backend":row["backend"],"tile":source["tile"],
            "feature":source["feature"],"requested_offset":source["requested_offset"],"resolved_offset":source["resolved_offset"],
            "selected_sprite":source["selected_sprite"],"original_image":str(image),"portable_image":str(target),"sha256":value})
assert len(source_files) == 5412
(out / "source-file-map.json").write_text(json.dumps(source_files,indent=2)+"\n")

applied = json.loads((root / "breadth-original-river-selector-compaction-apply.log").read_text())
assert applied["converted"] == 160 and applied["preserved_errors"] == 0
compact = Path(applied["manifest"])
compaction = json.loads(compact.read_text())
assert len(compaction["images"]) == 160 and not compaction["preserved_errors"]
compact_rows = []
for row in compaction["images"]:
    png = root / row["image"]
    assert png.name.startswith("model-world-atlas-") and not (root / row["original"]).exists()
    with Image.open(png) as picture:
        assert picture.mode == "RGBA"
        header = picture.info["opentt3d_pam_header"].encode("ascii")
        assert hashlib.sha256(header+picture.tobytes()).hexdigest() == row["pam_sha256"]
    target = out / "lossless-native-atlases" / Path(row["image"]).parts[0] / png.name
    copy(png,target)
    compact_rows.append(dict(row,portable_png=str(target),portable_png_sha256=digest(target),pam_reconstruction_sha256_exact=True))
(out / "lossless-atlas-reconstruction.json").write_text(json.dumps(compact_rows,indent=2)+"\n")
copy(compact,out / compact.name)

for name in ("breadth-original-river-selector-build.log","breadth-original-river-selector-native-tests.log",
    "breadth-original-river-selector-controls.py","breadth-original-river-selector-controls.log","breadth-original-river-selector-runs.json",
    "breadth-original-river-selector-controls-verification.json","breadth-original-river-selector-classic-audit.py",
    "breadth-original-river-selector-classic-audit.log","breadth-original-river-selector-classic-verification.json",
    "breadth-original-river-selector-classic-world-audit.py","breadth-original-river-selector-classic-world-audit-syntax-corrected.log",
    "breadth-original-river-selector-classic-world-verification.json","breadth-original-river-selector-alternate-controls.py",
    "breadth-original-river-selector-opengfx-controls.log","breadth-original-river-selector-opengfx-runs.json",
    "breadth-original-river-selector-opengfx-controls-verification.json","breadth-original-river-selector-alternate-prior-controls.py",
    "breadth-original-river-selector-opengfx-prior-controls.log","breadth-original-river-selector-opengfx-prior-runs.json",
    "breadth-original-river-selector-alternate-audit.py","breadth-original-river-selector-opengfx-audit-actual-sources.log",
    "breadth-original-river-selector-opengfx-verification.json","breadth-original-river-selector-current-quality.py",
    "breadth-original-river-selector-current-quality.log","breadth-original-river-selector-focused-final-tests.log",
    "breadth-original-river-selector-original-source-tests.log","breadth-original-river-selector-working-assets.log",
    "breadth-original-river-selector-clean-tests.py","breadth-original-river-selector-clean-tests.log",
    "breadth-original-river-selector-clean-test-receipt.json","breadth-original-river-selector-harness-tests.log",
    "breadth-original-river-selector-boundary.log","breadth-original-river-selector-presentation-delta.py",
    "breadth-original-river-selector-presentation-delta.log","breadth-original-river-selector-presentation-delta.json",
    "breadth-original-river-selector-compaction-plan.log","breadth-original-river-selector-compaction-apply.log",
    "breadth-original-river-selector-source-sheets.py","breadth-original-river-selector-source-sheets.log"):
    copy(root / name,out / name)
for name in ("breadth-original-river-selector-classic-world-audit-syntax-rejected.py",
    "breadth-original-river-selector-classic-world-audit-syntax-rejected.log","breadth-original-river-selector-world-audit-syntax-rejection.md",
    "breadth-original-river-selector-alternate-absence-assumption-rejected.py","breadth-original-river-selector-alternate-absence-assumption-rejected.log",
    "breadth-original-river-selector-alternate-absence-rejection.md","breadth-original-river-selector-patch-context-rejection.md"):
    copy(root / name,out / "retained-failures" / name)
for directory,name in ((root / "breadth-original-river-selector1831-frozen-build","classic-diagnostic"),
                       (root / "breadth-original-river-selector-opengfx1831-frozen-build","opengfx-diagnostic"),
                       (root / "breadth-original-river-selector-opengfx-prior1831-frozen-build","opengfx-prior")):
    copy(directory / "manifest.json",out / (name+"-frozen-manifest.json"))
for path in (root / "breadth-original-river-selector1831-frozen-build/source-snapshot").rglob("*"):
    if path.is_file():
        copy(path,out / "source-snapshot" / path.relative_to(root / "breadth-original-river-selector1831-frozen-build/source-snapshot"))
for path in (root / "breadth-original-river-selector-original-snapshot").rglob("*"):
    if path.is_file():
        copy(path,out / "pre-edit-source-snapshot" / path.relative_to(root / "breadth-original-river-selector-original-snapshot"))
for name in ("tools/assets/live_river_selectors.py","tools/assets/test_live_river_selectors.py","tools/assets/original_water.py",
             "tools/assets/quality_audit.py","tools/assets/inventory.py","tools/assets/compact_reviews.py","tools/opentt3d/check_boundary.py",
             "src/slope_type.h","src/newgrf_canal.h"):
    copy(Path(name),out / "source-snapshot" / name)
for path in (root / "breadth-original-river-selector-source-sheets").iterdir():
    copy(path,out / "classic-source-sheets" / path.name)
summary = {"sealed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"quiet_native_controls":40,
    "classic_owner_states_exact":1353,"opengfx_owner_states_exact":1353,"paired_source_records_exact":5412,
    "strict_world_images":32,"strict_world_changed_pixels":0,"masks":False,"tolerance":0,
    "classic_flat_bank_inputs_per_climate":12,"observed_ground_selector_climates_per_base_set":8,
    "observed_bank_input_selector_climates_per_base_set":56,"actual_absent_edge_control_established":False,
    "rejected_absence_expectation_retained":True,"native_tests":213,"working_asset_tests":266,
    "isolated_committed_artwork_tests":250,"harness_tests":99,"original_runtime_after_diagnostic_removal_exact":5,
    "losslessly_preserved_atlases":160,"compaction_saved_bytes":applied["saved_bytes"],"original_sprite_sources_untouched":True,
    "runtime_artwork_or_bindings_changed":False,"models":1831,"candidate_ledger_entries":2998,
    "approved_models":0,"recommended_release_unchanged":"opentt3d-dev-20261003.42",
    "scope":"Actual original river feature/callback input/output source observations and strict original-world preservation only. No source-driven forced selector, duplicate callback, missing/invented bank, relief/water ownership decomposition, model/runtime binding, complete custom-family or animation/ships/performance/8/10 approval. The full catalogue-wide goal remains open; sealing time is not stopping time."}
(out / "verification.json").write_text(json.dumps(summary,indent=2)+"\n")
copy(Path(__file__),out / "reproduce-portable-evidence.py")
files = {str(path):digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files":files,"scope":summary["scope"]},indent=2)+"\n")
print(json.dumps(summary))

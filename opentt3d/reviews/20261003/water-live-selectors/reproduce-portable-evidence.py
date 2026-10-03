"""Seal actual lock callbacks, original public saves and strict observer preservation."""
from pathlib import Path
import datetime, hashlib, json, shutil

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/water-live-selectors")
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def copy(source, destination):
    assert not destination.exists(), destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    assert digest(source) == digest(destination)


verification = json.loads((root / "breadth-original-lock-live-source-verification.json").read_text())
assert verification["quiet_native_controls"] == 64 and verification["public_saved_locks"] == 32
assert verification["selected_wall_owner_states_exact"] == 192 and verification["selected_independent_water_owner_states_exact"] == 96
assert verification["geometry_approvals"] == 0 and not verification["exact_tag_binary"]
preservation = json.loads((root / "breadth-original-water-observer-preservation-verification.json").read_text())
assert len(preservation["runs"]) == 16 and preservation["all_worlds_strict_exact"]
on_off = json.loads((root / "breadth-original-water-observer-on-off-verification.json").read_text())
assert len(on_off["comparisons"]) == 8 and on_off["all_worlds_strict_exact"]
for name, count in (("breadth-original-lock-live-state-strict-all-asset-tests.log", 243),
                    ("breadth-original-lock-clean-asset-tests.log", 227),
                    ("breadth-original-lock-resource-complete-harness-tests.log", 99)):
    assert f"Ran {count} tests" in (root / name).read_text() and "\nOK\n" in (root / name).read_text()
assert "100% tests passed, 0 tests failed out of 213" in (root / "breadth-original-water-observer-compiled-native-tests.log").read_text()
names = ("breadth-original-lock-live-source-verification.json", "breadth-original-lock-live-source-runs.json",
    "breadth-original-water-observer-preservation-verification.json", "breadth-original-water-observer-preservation-runs.json",
    "breadth-original-water-observer-on-off-verification.json", "breadth-original-lock-live-state-strict-all-asset-tests.log",
    "breadth-original-lock-clean-asset-tests.log", "breadth-original-lock-clean-asset-test-receipt.json",
    "breadth-original-water-live-strict-reconciliation.json", "breadth-original-water-live-strict-reconcile.py",
    "breadth-original-lock-clean-asset-tests.py", "breadth-original-lock-slope-guard-rejection.md",
    "breadth-original-lock-resource-complete-harness-tests.log", "breadth-original-water-observer-compiled-native-tests.log",
    "breadth-original-water-observer-boundary.log", "breadth-original-water-observer-real-native-build.log",
    "breadth-original-water-observer-native-build.log", "breadth-original-water-observer-native-tests.log",
    "breadth-original-water-observer-build-target-rejection.md", "breadth-original-lock-external-app-data-rejection.md",
    "breadth-original-lock-live-source-controls.py", "breadth-original-water-observer-preservation-controls.py",
    "breadth-original-water-observer-on-off-compare.py", "breadth-original-water-observer-freeze.py")
for name in names:
    copy(root / name, out / name)
for path in (root / "breadth-original-lock-slope-guard-rejected").iterdir():
    copy(path, out / "retained-slope-guard-rejection" / path.name)
copy(root / "breadth-original-water-observer1831-frozen-build/manifest.json", out / "observer-local-build-manifest.json")
for path in (root / "breadth-original-water-observer1831-frozen-build/source-snapshot").rglob("*"):
    if path.is_file():
        copy(path, out / "source-snapshot" / path.relative_to(root / "breadth-original-water-observer1831-frozen-build/source-snapshot"))
for name in ("tools/assets/live_water.py", "tools/assets/test_live_water.py", "tools/opentt3d/test_fixture_locks.py"):
    copy(Path(name), out / "source-snapshot" / name)
for path in (root / "breadth-original-lock-live-source-sheets").iterdir():
    copy(path, out / "source-sheets" / path.name)
copy(root / "breadth-original-lock-live-source-sheets.py", out / "reproduce-source-sheets.py")

sources = {}
for climate in ("temperate", "arctic", "tropic", "toyland"):
    fixture = root / ("breadth-original-lock-temperate-natural-resources-fixture" if climate == "temperate" else f"breadth-original-lock-{climate}-natural-fixture")
    row = json.loads((fixture / "fixture.json").read_text())
    assert len(row["locks"]) == 8 and digest(fixture / "save/lock-fixture.sav") == row["save_sha256"]
    for name in ("fixture.json", "command-acknowledgements.json", "run.log", "openttd.cfg", "save/lock-fixture.sav"):
        copy(fixture / name, out / "public-fixtures" / climate / name)
for run in json.loads((root / "breadth-original-lock-live-source-runs.json").read_text()):
    assert run["exit_code"] == 0
    directory = Path(run["output"])
    target = out / "live-controls" / directory.name
    for name in ("run.log", "result.json", "renderer3d-reference/water-live.json"):
        copy(directory / name, target / name)
    selected = json.loads((directory / "renderer3d-reference/water-live.json").read_text())
    assert not selected["geometry_approved"]
    for row in selected["observations"]:
        image = directory / "renderer3d-reference" / row["source_image"]
        key = (run["climate"], digest(image))
        if key not in sources:
            destination = out / "sources" / run["climate"] / row["source_image"]
            copy(image, destination)
            sources[key] = {"portable_image": str(destination), "sha256": key[1], "original_images": []}
        sources[key]["original_images"].append(str(image))
    if run["elevation"] == 0 and run["direction"] == 0:
        copy(directory / "screenshot/smoke.png", target / "smoke.png")
for run in preservation["runs"]:
    assert run["exit_code"] == 0
    directory = Path(run["output"])
    for name in ("run.log", "result.json", "screenshot/smoke.png"):
        copy(directory / name, out / "preservation-controls" / directory.name / name)
for report in preservation["comparisons"] + on_off["comparisons"]:
    assert report["exit_code"] == 0 and report["different_pixels"] == 0
    copy(Path(report["report"]), out / "strict-comparisons" / Path(report["report"]).name)
for name in ("breadth-original-lock-temperate-natural-fixture", "breadth-original-lock-temperate-natural-data-fixture"):
    for file in ("run.log", "openttd.cfg"):
        copy(root / name / file, out / "retained-startup-failures" / name / file)
    copy(root / (name+"-command.log"), out / "retained-startup-failures" / (name+"-command.log"))
(out / "source-file-map.json").write_text(json.dumps(list(sources.values()), indent=2) + "\n")
copy(Path(__file__), out / "reproduce-portable-evidence.py")
summary = {"sealed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "public_saved_locks": 32, "live_native_controls": 64, "preservation_native_controls": 16,
    "wall_owner_states_exact": 192, "water_owner_states_exact": 96, "world_comparisons_strict_exact": 16,
    "unique_original_source_pams": len(sources), "compiled_native_tests": 213, "working_asset_tests": 243,
    "isolated_committed_artwork_asset_tests": 227, "harness_tests": 99,
    "geometry_approvals": 0, "recommended_release_unchanged": "opentt3d-dev-20261003.42",
    "local_observer_binary_sha256": verification["binary_sha256"], "catalogue_sha256": verification["loaded_catalogue_sha256"],
    "scope": "Portable original/public-command sources and opt-in read-only observer preservation only; no geometry, runtime model, phase, fleet, performance, platform, release or visual-quality approval."}
(out / "verification.json").write_text(json.dumps(summary, indent=2) + "\n")
files = {str(path): digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files": files, "scope": summary["scope"]}, indent=2) + "\n")
print(json.dumps(dict(summary, portable_files=len(files))))

"""Reconcile incidental river ground callbacks already captured in the 64 lock controls."""
from pathlib import Path
import datetime, hashlib, json, sys

sys.path.insert(0,"tools/assets")
from live_water import selected_river_sources

root = Path("build-macos")
out = root / "breadth-original-river-selected-source-verification.json"
assert not out.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
runs_path = root / "breadth-original-lock-live-source-runs.json"
runs = json.loads(runs_path.read_text())
assert len(runs) == 64 and all(row["exit_code"] == 0 for row in runs)
selected, proofs = {}, {}
for index,climate in enumerate(("temperate","arctic","tropic","toyland")):
    fixture = root / ("breadth-original-lock-temperate-natural-resources-fixture" if climate == "temperate" else f"breadth-original-lock-{climate}-natural-fixture")
    saved = json.loads((fixture / "fixture.json").read_text())
    assert digest(fixture / "save/lock-fixture.sav") == saved["save_sha256"]
    backends = {}
    for backend in ("vulkan","opengl"):
        rows = []
        for run in runs:
            if run["climate"] != climate or run["backend"] != backend:
                continue
            directory = Path(run["output"]) / "renderer3d-reference"
            observations = directory / "water-live.json"
            proofs[str(observations)] = digest(observations)
            for row in json.loads(observations.read_text())["observations"]:
                if row["kind"] != "sloped-river":
                    continue
                image = directory / row["source_image"]
                row["source_image_sha256"] = digest(image)
                proofs[str(image)] = row["source_image_sha256"]
                rows.append(row)
        backends[backend] = selected_river_sources(rows,saved,index)
    assert backends["vulkan"] == backends["opengl"], climate
    selected[climate] = backends["vulkan"]
assert [len(selected[climate]["selected_ground_sources"]) for climate in selected] == [4,7,4,4]
assert [selected[climate]["observed_slopes"] for climate in selected] == [[3],[6],[6],[3]]
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"selected_sources":selected,
    "callback_source_states_exact":19,"observed_tiles":sum(row["observed_tiles"] for row in selected.values()),
    "reused_successful_original_controls":64,"new_native_controls":0,"run_manifest_sha256":digest(runs_path),
    "validator_sha256":digest(Path("tools/assets/live_water.py")),"tests_sha256":digest(Path("tools/assets/test_live_river.py")),
    "original_evidence_sha256":proofs,"geometry_approvals":0,"feature_offsets_resolved":False,
    "conditional_absences_verified":False,"complete_river_family_verified":False,
    "scope":"Read-only reconciliation of incidental actual sloped-river callbacks already present in the 64 frozen observer controls. Nineteen selected ground source states on nine saved tiles match exact bytes/metadata/provenance across backends. Only original SW/SE slopes are observed, in different climates. Ground records cannot identify bank vs water features/offsets, repeated layer order, flat-state absence, animated phases, ship passage, full custom-family coverage, volumes or quality. No new native execution or source selection was forced."}
assert summary["observed_tiles"] == 9
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"source_states_exact":19,"saved_tiles":9,"feature_offsets_resolved":False,"approved":False}))

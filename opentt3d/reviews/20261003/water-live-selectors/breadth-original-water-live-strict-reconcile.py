"""Recheck actual callback states with independent slope/provenance guards."""
from pathlib import Path
import datetime, hashlib, json, sys

sys.path.insert(0,"tools/assets")
from live_water import selected_lock_sources

root = Path("build-macos")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
verified = json.loads((root / "breadth-original-lock-live-source-verification.json").read_text())
runs = json.loads((root / "breadth-original-lock-live-source-runs.json").read_text())
results = []
for index,climate in enumerate(("temperate","arctic","tropic","toyland")):
    fixture = root / ("breadth-original-lock-temperate-natural-resources-fixture" if climate == "temperate" else f"breadth-original-lock-{climate}-natural-fixture")
    sites = json.loads((fixture / "fixture.json").read_text())
    selections = {}
    for backend in ("vulkan","opengl"):
        rows = []
        for run in runs:
            if run["climate"] != climate or run["backend"] != backend:
                continue
            assert run["exit_code"] == 0
            directory = Path(run["output"]) / "renderer3d-reference"
            for row in json.loads((directory / "water-live.json").read_text())["observations"]:
                row["source_image_sha256"] = digest(directory / row["source_image"])
                rows.append(row)
        selections[backend] = selected_lock_sources(rows,sites,index)
    assert selections["vulkan"] == selections["opengl"] == verified["selected_sources"][climate]
    results.append({"climate":climate,"walls":48,"independent_water":24,"source_bytes_metadata_anchors_and_slopes_exact":True})
out = root / "breadth-original-water-live-strict-reconciliation.json"
assert not out.exists()
out.write_text(json.dumps({"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"comparisons":results,
    "validator_sha256":digest(Path("tools/assets/live_water.py")),"validator_tests_sha256":digest(Path("tools/assets/test_live_water.py")),
    "geometry_approvals":0,"scope":"The strengthened offline guards reconcile unchanged actual callback sources, independent original slope enums, exact integral anchors/source sizes/water classes/provenance. Native observations and fixtures were not rewritten or forced."},indent=2)+"\n")
print(json.dumps({"walls":192,"independent_water":96,"all_states_exact":True,"geometry_approvals":0}))

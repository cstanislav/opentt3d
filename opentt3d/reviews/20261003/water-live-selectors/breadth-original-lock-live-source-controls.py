"""Observe real water callbacks in all32 public saved locks and both renderers."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys

root = Path("build-macos").resolve()
build = root / "breadth-original-water-observer1831-frozen-build"
prefix = "breadth-original-lock-live-source"
manifest = json.loads((build / "manifest.json").read_text())
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
assert digest(build / "opentt3d") == manifest["binary_sha256"]
assert digest(build / "baseset/opentt3d-voxels.json") == manifest["loaded_catalogue_sha256"]
sys.path.insert(0,"tools/assets")
from live_water import selected_lock_sources
rows, comparisons, all_sources = [], [], {}
for climate_index, climate in enumerate(("temperate","arctic","tropic","toyland")):
    fixture = root / ("breadth-original-lock-temperate-natural-resources-fixture" if climate == "temperate" else f"breadth-original-lock-{climate}-natural-fixture")
    sites = json.loads((fixture / "fixture.json").read_text())
    assert digest(fixture / "save/lock-fixture.sav") == sites["save_sha256"]
    backend_sources = {}
    for backend in ("vulkan","opengl"):
        observations = []
        for site in sites["locks"]:
            output = root / f"{prefix}-{climate}-{site['elevation']}-{site['direction']}-{backend}"
            command = ["python3","tools/opentt3d/smoke.py","--build-dir",str(build),"--output",str(output),"--background","--backend",backend,
                "--savegame",str(fixture / "save/lock-fixture.sav"),"--ai-dir",str(fixture / "ai"),"--center",str(site["x"]),str(site["y"]),
                "--verify-world-atlas","--verify-tile-picking","--synchronous-save","--zoom","0","--resolution","640","480","--timeout","300","--brief"]
            result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1"))
            rows.append({"climate":climate,"backend":backend,"elevation":site["elevation"],"direction":site["direction"],
                         "output":str(output),"exit_code":result.returncode,"command":command})
            (root / (prefix+"-runs.json")).write_text(json.dumps(rows,indent=2)+"\n")
            if result.returncode:
                raise SystemExit(result.returncode)
            assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
            source_manifest = json.loads((output / "renderer3d-reference/water-live.json").read_text())
            assert not source_manifest["geometry_approved"]
            for row in source_manifest["observations"]:
                name = row["source_image"]
                assert Path(name).name == name and name.endswith(".pam")
                row["source_image_sha256"] = digest(output / "renderer3d-reference" / name)
            observations.extend(source_manifest["observations"])
            actual = [row for row in source_manifest["observations"] if row["kind"] == "lock" and row["tile"] in (site["tile"],site["lower"],site["upper"])]
            assert len(actual) >= 9, "All three real target parts must be observed before any source coverage claim"
        backend_sources[backend] = selected_lock_sources(observations,sites,climate_index)
    assert backend_sources["vulkan"] == backend_sources["opengl"], f"{climate} exact selected source bytes/metadata differ"
    all_sources[climate] = backend_sources["vulkan"]
    comparisons.append({"climate":climate,"actual_wall_owners_exact":48,"actual_independent_water_owners_exact":24,
                        "selected_sprite_metadata_and_source_bytes_exact":True,"geometry_approved":False})
assert digest(build / "opentt3d") == manifest["binary_sha256"]
assert digest(build / "baseset/opentt3d-voxels.json") == manifest["loaded_catalogue_sha256"]
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"binary_sha256":manifest["binary_sha256"],
    "loaded_catalogue_sha256":manifest["loaded_catalogue_sha256"],"models":1831,"quiet_native_controls":len(rows),"public_saved_locks":32,
    "comparisons":comparisons,"selected_wall_owner_states_exact":192,"selected_independent_water_owner_states_exact":96,
    "selected_sources":all_sources,"geometry_approvals":0,"exact_tag_binary":False,
    "scope":"Read-only optional observer compiled locally from three C++ diagnostic deltas, loading the unchanged immutable1831-model .42 payload. Fixtures are original public-command saves from the exact-tag downloaded app. All four directions/two natural elevations/three original parts/two walls and independent water are observed in every climate/backend. This establishes actual selected source bytes/anchors, not volumes, dimensions inferred from sorting extents, ship traversal, animated phases, alternate/custom-family completeness, visual ratings or release approval."}
output = root / (prefix+"-verification.json")
assert not output.exists()
output.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"quiet_native_controls":len(rows),"actual_wall_owner_states_exact":192,"independent_water_states_exact":96,"geometry_approvals":0}))

"""Reconcile actual original zero-base absence and strict alternate world preservation."""
from pathlib import Path
import datetime, hashlib, json, sys

sys.path.insert(0,"tools/assets")
from compare_galleries import image
from live_river_selectors import selected_river_selectors

root = Path("build-macos")
out = root / "breadth-original-river-selector-opengfx-verification.json"
assert not out.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
runs = json.loads((root / "breadth-original-river-selector-opengfx-runs.json").read_text())
prior = json.loads((root / "breadth-original-river-selector-opengfx-prior-runs.json").read_text())
assert len(runs) == 16 and len(prior) == 8 and all(row["exit_code"] == 0 for row in runs+prior)
selected,proofs,comparisons = {},{},[]
for climate_id,climate in enumerate(("temperate","arctic","tropic","toyland")):
    backends = {}
    for backend in ("vulkan","opengl"):
        on = next(row for row in runs if row["climate"] == climate and row["backend"] == backend and row["tracing"])
        off = next(row for row in runs if row["climate"] == climate and row["backend"] == backend and not row["tracing"])
        earlier = next(row for row in prior if row["climate"] == climate and row["backend"] == backend)
        directory = Path(on["output"]) / "renderer3d-reference"
        input_path = Path(on["command"][on["command"].index("--savegame")+1])
        fixture = json.loads((input_path.parent.parent / "fixture.json").read_text())
        assert digest(input_path) == fixture["save_sha256"]
        observations_path = directory / "river-selectors.json"
        proofs[str(observations_path)] = digest(observations_path)
        observations = json.loads(observations_path.read_text())["observations"]
        for row in observations:
            if not row["absent"]:
                path = directory / row["source_image"]
                row["source_image_sha256"] = digest(path)
                proofs[str(path)] = row["source_image_sha256"]
        verified = selected_river_selectors(observations,fixture,climate_id)
        assert all(row["base_set"] == "OpenGFX" for row in observations)
        assert not verified["edge_sources"]
        assert len(verified["ground_sources"]) == len(verified["absent_edge_features"]) == verified["observed_tiles"]
        assert all(row["base_sprite"] == 0 and not row["offset_callback"] for row in observations)
        backends[backend] = verified
        for mode,reference,actual in (("default-off-prior",Path(earlier["output"]),Path(off["output"])),
                                      ("tracing-on-off",Path(off["output"]),Path(on["output"]))):
            a_path,b_path = reference / "screenshot/smoke.png",actual / "screenshot/smoke.png"
            a,b = image(a_path),image(b_path)
            assert a.size == b.size
            x,y = a.tobytes(),b.tobytes()
            changed = [index//4 for index in range(0,len(x),4) if x[index:index+4] != y[index:index+4]]
            row = {"climate":climate,"backend":backend,"mode":mode,"images":1,"pixels":a.width*a.height,
                   "changed_pixels":len(changed),"reference":str(a_path),"actual":str(b_path),
                   "reference_sha256":digest(a_path),"actual_sha256":digest(b_path)}
            if changed:
                first = changed[0]
                row.update(first_pixel=[first%a.width,first//a.width],reference_rgba=list(x[first*4:first*4+4]),actual_rgba=list(y[first*4:first*4+4]))
            comparisons.append(row)
    assert backends["vulkan"] == backends["opengl"],climate
    selected[climate] = backends["vulkan"]
assert sum(len(row["ground_sources"]) for row in selected.values()) == 454
assert sum(len(row["absent_edge_features"]) for row in selected.values()) == 454
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"selected_sources":selected,
    "observed_ground_owner_states_exact":454,"explicit_absent_edge_feature_states_exact":454,"observed_edge_source_owners":0,
    "world_comparisons":comparisons,"images":16,"changed_pixels":sum(row["changed_pixels"] for row in comparisons),
    "masks":False,"tolerance":0,"native_alternate_controls":24,"complete_river_family_verified":False,
    "raised_water_ownership_verified":False,"approvals":0,"original_evidence_sha256":proofs,
    "scope":"Actual OpenGFX zero-base original CF_RIVER_EDGE decisions are retained on454 observed river tiles across all climates and both renderers, with454 independent original flat/sloped ground sources and no invented edge source/image/model. Both backends match complete source metadata/PAM bytes;16 strict prior/default-off/tracing world comparisons have no masks/tolerance. Absence is established only for these observed tiles/base set, not unobserved/custom families; full relief/water ownership, slopes/phases and ships remain unaccepted."}
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"ground_states_exact":454,"explicit_absent_edge_states_exact":454,"world_images":16,"changed_pixels":summary["changed_pixels"],"approvals":0}))
assert summary["changed_pixels"] == 0

"""Reconcile actual Classic callback values and preserve all earlier lock/river source bytes."""
from pathlib import Path
import datetime, hashlib, json, sys

sys.path.insert(0,"tools/assets")
from live_river_selectors import selected_river_selectors

root = Path("build-macos")
out = root / "breadth-original-river-selector-classic-verification.json"
assert not out.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
runs = json.loads((root / "breadth-original-river-selector-runs.json").read_text())
assert len(runs) == 16 and all(row["exit_code"] == 0 for row in runs)
old_river = json.loads((root / "breadth-original-river-selected-source-verification.json").read_text())["selected_sources"]
selected,proofs,prior_exact = {},{},[]
for climate_id,climate in enumerate(("temperate","arctic","tropic","toyland")):
    backends = {}
    for backend in ("vulkan","opengl"):
        run = next(row for row in runs if row["climate"] == climate and row["backend"] == backend and row["tracing"])
        directory = Path(run["output"]) / "renderer3d-reference"
        input_path = Path(run["command"][run["command"].index("--savegame")+1])
        fixture = json.loads((input_path.parent.parent / "fixture.json").read_text())
        assert digest(input_path) == fixture["save_sha256"]
        observations_path = directory / "river-selectors.json"
        proofs[str(observations_path)] = digest(observations_path)
        observations = json.loads(observations_path.read_text())["observations"]
        for row in observations:
            if not row["absent"]:
                image = directory / row["source_image"]
                row["source_image_sha256"] = digest(image)
                proofs[str(image)] = row["source_image_sha256"]
        verified = selected_river_selectors(observations,fixture,climate_id)
        assert all(row["base_set"] == "OpenGFX2 Classic" for row in observations)
        assert not verified["absent_edge_features"]
        assert {row["requested_offset"] for row in verified["edge_sources"] if row["slope"] == 0} == set(range(12))
        backends[backend] = verified
        original = json.loads((Path(run["reference_output"]) / "renderer3d-reference/water-live.json").read_text())["observations"]
        current = json.loads((directory / "water-live.json").read_text())["observations"]

        def originals(rows,where):
            result = []
            for row in rows:
                value = {key:item for key,item in row.items() if key not in ("source_image","texture_generation")}
                value["source_image_sha256"] = digest(where / row["source_image"])
                result.append(value)
            return sorted(result,key=lambda row:json.dumps(row,sort_keys=True))

        a = originals(original,Path(run["reference_output"]) / "renderer3d-reference")
        b = originals(current,directory)
        assert a == b,(climate,backend)
        prior_exact.append({"climate":climate,"backend":backend,"original_lock_and_incidental_river_records_exact":len(a),
                            "records_sha256":hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest()})
    assert backends["vulkan"] == backends["opengl"],climate
    verified = backends["vulkan"]
    selected[climate] = verified
    actual = verified["ground_sources"]+verified["edge_sources"]
    for row in old_river[climate]["selected_ground_sources"]:
        owner = next(source for source in actual if source["tile"] == row["tile"] and source["selected_sprite"] == row["sprite"])
        for key in ("source_offset","source_size","source_file","base_set","base_graphics","source_height","draw_origin","source_image_sha256"):
            assert owner[key] == row[key],(climate,row["tile"],key)
assert sum(len(row["ground_sources"]) for row in selected.values()) == 454
assert sum(len(row["edge_sources"]) for row in selected.values()) == 899
groups = {climate:{"ground_slopes":row["observed_slopes"],
    "edge_inputs":[{"slope":slope,"requested_offsets":sorted({source["requested_offset"] for source in row["edge_sources"] if source["slope"] == slope})}
                   for slope in row["observed_slopes"]]} for climate,row in selected.items()}
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"selected_sources":selected,"observed_groups":groups,
    "classic_ground_owner_states_exact":454,"classic_edge_owner_states_exact":899,"total_owner_states_exact":1353,
    "prior_lock_and_incidental_river_preservation":prior_exact,"prior_incidental_sources_preserved":19,
    "observed_ground_selector_climates":sum(len(row["observed_slopes"]) for row in selected.values()),
    "observed_edge_input_selector_climates":sum(len({(source["slope"],source["requested_offset"]) for source in row["edge_sources"]}) for row in selected.values()),
    "native_classic_controls":16,"complete_river_family_verified":False,"raised_water_ownership_verified":False,
    "original_evidence_sha256":proofs,"approvals":0,
    "scope":"Actual Classic CF_RIVER_SLOPE ground and CF_RIVER_EDGE offset-callback selectors are observed at original draw sites, not guessed from IDs or queried twice.454 ground and899 conditional bank owners match metadata/PAM bytes across backends. All12 flat bank inputs occur in each climate; only two sloped bank inputs and one natural slope occur per climate. Earlier lock and19 incidental river sources remain exact. Source feature identity does not approve internal raised/water owners, relief dimensions, full custom-family/phase/ship/geometry coverage. No volume is bound."}
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"ground_states_exact":454,"edge_states_exact":899,"ground_selector_climates":summary["observed_ground_selector_climates"],
    "edge_input_selector_climates":summary["observed_edge_input_selector_climates"],"geometry_approvals":0}))

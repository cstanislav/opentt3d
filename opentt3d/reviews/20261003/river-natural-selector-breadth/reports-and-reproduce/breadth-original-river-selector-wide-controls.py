"""Observe natural river slopes from a wider saved-world camera, never force a selector."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys

sys.path.insert(0,"tools/assets")
from live_river_selectors import selected_river_selectors

root = Path("build-macos").resolve()
build = root / "breadth-original-river-selector1831-frozen-build"
manifest = json.loads((build / "manifest.json").read_text())
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
assert digest(build / "opentt3d") == manifest["binary_sha256"]
assert digest(build / "baseset/opentt3d-voxels.json") == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
prior = json.loads((root / "breadth-original-river-selector-runs.json").read_text())
rows,selected,proofs = [],{},{}
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
for climate_id,climate in enumerate(("temperate","arctic","tropic","toyland")):
    backends = {}
    for backend in ("vulkan","opengl"):
        reference = next(row for row in prior if row["climate"] == climate and row["backend"] == backend and row["tracing"])
        command = list(reference["command"])
        output = root / f"breadth-original-river-selector-wide-{climate}-{backend}"
        assert not output.exists()
        command[command.index("--output")+1] = str(output)
        centre = command.index("--center")
        command[centre+1:centre+3] = ["64","64"]
        command[command.index("--zoom")+1] = "5"
        save = Path(command[command.index("--savegame")+1])
        fixture = json.loads((save.parent.parent / "fixture.json").read_text())
        assert digest(save) == fixture["save_sha256"]
        result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1",OPENTT3D_GL_RASTER_Y_DOWN="0"))
        row = {"climate":climate,"backend":backend,"output":str(output),"exit_code":result.returncode,
            "command":command,"source_fixture_sha256":fixture["save_sha256"],"camera_change_only":True,"tracing":True}
        rows.append(row)
        (root / "breadth-original-river-selector-wide-runs.json").write_text(json.dumps(rows,indent=2)+"\n")
        assert result.returncode == 0,row
        assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
        subprocess.run([python,"tools/assets/compact_reviews.py",str(root),"--validation-manifest",
            str(root / "breadth-original-river-selector-wide-runs.json"),"--apply"],check=True)
        directory = output / "renderer3d-reference"
        observations = json.loads((directory / "river-selectors.json").read_text())["observations"]
        proofs[str(directory / "river-selectors.json")] = digest(directory / "river-selectors.json")
        for source in observations:
            if source["absent"]:
                continue
            source["source_image_sha256"] = digest(directory / source["source_image"])
            proofs[str(directory / source["source_image"])] = source["source_image_sha256"]
        backends[backend] = selected_river_selectors(observations,fixture,climate_id)
    assert backends["vulkan"] == backends["opengl"],climate
    selected[climate] = backends["vulkan"]
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"native_quiet_controls":8,
    "source_binary_manifest_sha256":digest(build / "manifest.json"),"selected_sources":selected,"original_evidence_sha256":proofs,
    "ground_owner_states_exact":sum(len(row["ground_sources"]) for row in selected.values()),
    "bank_owner_states_exact":sum(len(row["edge_sources"]) for row in selected.values()),
    "observed_ground_selector_climates":sum(len(row["observed_slopes"]) for row in selected.values()),
    "observed_bank_input_selector_climates":sum(len({(source["slope"],source["requested_offset"]) for source in row["edge_sources"]}) for row in selected.values()),
    "approvals":0,"complete_river_family_verified":False,
    "scope":"Wider ordinary zoom5/central128x128 saved-world cameras select natural river flat/slope/edge sources through original draw callbacks; no tile type, slope, height, state, callback, absence or source ID is forced. Both backends retain exact metadata/PAM bytes. This expands observed source-selector breadth only, not all hypothetical river patterns/heights/custom families, repeated draw order/animation, relief/water ownership, models, ships, smooth60fps or visual approval. The observer/1831-model artwork are the prior frozen diagnostic; no new runtime source/artwork is compiled or bound."}
(root / "breadth-original-river-selector-wide-verification.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({key:summary[key] for key in ("native_quiet_controls","ground_owner_states_exact","bank_owner_states_exact","observed_ground_selector_climates","observed_bank_input_selector_climates","approvals")}))

"""Compare the alternate source path to the earlier observer binary, not another base set."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess

root = Path("build-macos").resolve()
old = root / "breadth-original-water-observer1831-frozen-build"
resources = root / "breadth-original-river-selector-opengfx1831-frozen-build"
out = root / "breadth-original-river-selector-opengfx-prior1831-frozen-build"
assert not out.exists()
out.mkdir()
(out / "opentt3d").symlink_to(old / "opentt3d")
for name in ("baseset","lang","ai","game"):
    (out / name).symlink_to(resources / name,target_is_directory=True)
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
manifest = {"frozen_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"binary_sha256":digest(out / "opentt3d"),
    "catalogue_sha256":digest(out / "baseset/opentt3d-voxels.json"),"alternate_resource_manifest_sha256":digest(resources / "manifest.json"),
    "prior_source_manifest_sha256":digest(old / "manifest.json"),"exact_tag_binary":False,"models":1831,"approvals":0,
    "scope":"Earlier compiled lock-source observer binary, not the exact-tag application, leased with the identical alternate OpenGFX8.0/1831-model resources. This establishes a same-base-set prior default-off world comparison only; no new geometry or full-state/family/phase/ship quality approval."}
assert manifest["binary_sha256"] == "a0d839f679976de4121710850241208819f4470f6e66de061c18f0aa232272d7"
assert manifest["catalogue_sha256"] == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
(out / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
source = json.loads((root / "breadth-original-river-selector-opengfx-runs.json").read_text())
assert len(source) == 16 and all(row["exit_code"] == 0 for row in source)
rows = []
for reference in source:
    if reference["tracing"]:
        continue
    command = list(reference["command"])
    output = root / f"breadth-original-river-selector-opengfx-prior-{reference['climate']}-{reference['backend']}"
    command[command.index("--build-dir")+1] = str(out)
    command[command.index("--output")+1] = str(output)
    result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
    row = {"climate":reference["climate"],"backend":reference["backend"],"output":str(output),"exit_code":result.returncode,
           "command":command,"tracing":False,"base_set":"OpenGFX"}
    rows.append(row)
    (root / "breadth-original-river-selector-opengfx-prior-runs.json").write_text(json.dumps(rows,indent=2)+"\n")
    assert result.returncode == 0,row
    assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
    assert not (output / "renderer3d-reference/river-selectors.json").exists()
print(json.dumps({"quiet_prior_alternate_runs":8,"models":1831,"geometry_approvals":0}))

"""Observe real alternate-base-set river absence without removing/inventing any source."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess

root = Path("build-macos").resolve()
old = root / "breadth-original-river-selector1831-frozen-build"
out = root / "breadth-original-river-selector-opengfx1831-frozen-build"
assert not out.exists()
out.mkdir()
for name in ("opentt3d","lang","ai","game"):
    (out / name).symlink_to(old / name,target_is_directory=name != "opentt3d")
(out / "baseset").mkdir()
for source in (old / "baseset").iterdir():
    (out / "baseset" / source.name).symlink_to(source.resolve(),target_is_directory=source.is_dir())
alternate = root / "baseset/opengfx-8.0.tar"
assert alternate.is_file()
(out / "baseset/opengfx-8.0.tar").symlink_to(alternate)
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
manifest = {"frozen_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"binary_sha256":digest(out / "opentt3d"),
    "catalogue_sha256":digest(out / "baseset/opentt3d-voxels.json"),"alternate_archive_sha256":digest(alternate),
    "alternate_archive_bytes":alternate.stat().st_size,"alternate_archive_source":str(alternate),
    "diagnostic_source_manifest_sha256":digest(old / "manifest.json"),"exact_tag_binary":False,"models":1831,"approvals":0,
    "scope":"Same local read-only selector diagnostic/immutable1831-model.42 assets with a separately leased retained OpenGFX8.0 archive; no archive/source replacement or forced feature absence. Actual original base-set selection/zero-base river edge decisions must be observed. Not an exact-tag app, new upstream download verification, complete-family/relief/animation/ships or geometry approval."}
assert manifest["catalogue_sha256"] == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
(out / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
prior = json.loads((root / "breadth-original-lock-live-source-runs.json").read_text())
rows = []
for tracing in (False,True):
    for climate in ("temperate","arctic","tropic","toyland"):
        for backend in ("vulkan","opengl"):
            reference = next(row for row in prior if row["climate"] == climate and row["backend"] == backend and row["elevation"] == 0 and row["direction"] == 0)
            command = list(reference["command"])
            output = root / f"breadth-original-river-selector-opengfx-{climate}-{backend}-{'on' if tracing else 'off'}"
            command[command.index("--build-dir")+1] = str(out)
            command[command.index("--output")+1] = str(output)
            command.extend(("--graphics","OpenGFX"))
            result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1" if tracing else "0"))
            row = {"climate":climate,"backend":backend,"tracing":tracing,"output":str(output),"exit_code":result.returncode,
                   "command":command,"base_set":"OpenGFX","source_fixture_from":reference["output"]}
            rows.append(row)
            (root / "breadth-original-river-selector-opengfx-runs.json").write_text(json.dumps(rows,indent=2)+"\n")
            assert result.returncode == 0,row
            assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
            assert (output / "renderer3d-reference/river-selectors.json").is_file() == tracing
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"quiet_native_runs":16,
    "trace_on_runs":8,"trace_off_runs":8,"approvals":0,"scope":manifest["scope"]}
(root / "breadth-original-river-selector-opengfx-controls-verification.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary))

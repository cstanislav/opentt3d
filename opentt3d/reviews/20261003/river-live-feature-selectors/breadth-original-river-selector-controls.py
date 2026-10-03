"""Freeze the read-only selector diagnostic with unchanged1831-model release assets."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess

root = Path("build-macos").resolve()
out = root / "breadth-original-river-selector1831-frozen-build"
assert not out.exists()
out.mkdir()
old = root / "breadth-original-water-observer1831-frozen-build"
for name in ("baseset","lang","ai","game"):
    (out / name).symlink_to(old / name,target_is_directory=True)
shutil.copy2(root / "opentt3d",out / "opentt3d")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
files = ("src/water_cmd.cpp","src/renderer3d/world_capture.h","src/renderer3d/world_capture.cpp",
         "src/renderer3d/sprite_textures.hpp","src/renderer3d/reference_export.cpp")
assert set(subprocess.check_output(["git","diff","--name-only","--","src"],text=True).splitlines()) == set(files)
for name in files:
    target = out / "source-snapshot" / name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(name,target)
manifest = {"frozen_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"binary_sha256":digest(out / "opentt3d"),
    "catalogue_sha256":digest(out / "baseset/opentt3d-voxels.json"),"source_sha256":{name:digest(Path(name)) for name in files},
    "build_log_sha256":digest(root / "breadth-original-river-selector-build.log"),
    "head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"models":1831,"exact_tag_binary":False,
    "approvals":0,"scope":"Read-only default-off actual river draw-selector diagnostic compiled locally, loading immutable1831-model.42 artwork. Capture current input/output offsets, feature flags and real absent bases without resolving callbacks again or modifying draws, terrain, palettes, model dimensions, simulation/RNG. Not an exact-tag application, runtime geometry increment, source relief/animation/full-family/ship or quality approval."}
assert manifest["catalogue_sha256"] == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
assert len(json.loads((out / "baseset/opentt3d-voxels.json").read_text())["models"]) == 1831
(out / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
prior = json.loads((root / "breadth-original-lock-live-source-runs.json").read_text())
rows = []
for tracing in (False,True):
    for climate in ("temperate","arctic","tropic","toyland"):
        for backend in ("vulkan","opengl"):
            reference = next(row for row in prior if row["climate"] == climate and row["backend"] == backend and row["elevation"] == 0 and row["direction"] == 0)
            command = list(reference["command"])
            output = root / f"breadth-original-river-selector-{climate}-{backend}-{'on' if tracing else 'off'}"
            command[command.index("--build-dir")+1] = str(out)
            command[command.index("--output")+1] = str(output)
            result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1" if tracing else "0"))
            row = {"climate":climate,"backend":backend,"tracing":tracing,"output":str(output),"exit_code":result.returncode,
                   "command":command,"reference_output":reference["output"]}
            rows.append(row)
            (root / "breadth-original-river-selector-runs.json").write_text(json.dumps(rows,indent=2)+"\n")
            assert result.returncode == 0,row
            assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
            assert (output / "renderer3d-reference/river-selectors.json").is_file() == tracing
            assert (output / "renderer3d-reference/water-live.json").is_file() == tracing
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"quiet_native_runs":16,
    "trace_on_runs":8,"trace_off_runs":8,"source_selector_manifests":8,"approvals":0,"scope":manifest["scope"]}
(root / "breadth-original-river-selector-controls-verification.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary))

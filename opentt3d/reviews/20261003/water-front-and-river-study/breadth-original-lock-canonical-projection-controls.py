"""Test explicit projection arithmetic on unchanged rejected art, never change pixels to fit."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess

root = Path("build-macos").resolve()
out = root / "breadth-original-lock-canonical-projection-frozen-build"
assert not out.exists()
out.mkdir()
old = root / "breadth-original-lock-authored-study-frozen-build"
for name in ("baseset","lang","ai","game"):
    (out / name).symlink_to(old / name,target_is_directory=True)
shutil.copy2(root / "opentt3d",out / "opentt3d")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
paths = ("src/renderer3d/gl_backend.cpp","src/renderer3d/shaders/vk_world.vert")
changed = subprocess.check_output(["git","diff","--name-only","--","src"],text=True).splitlines()
assert set(changed) == set(paths), changed
for name in paths:
    target = out / "source-snapshot" / name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(name,target)
manifest = {"frozen_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "binary_sha256":digest(out / "opentt3d"),"catalogue_sha256":digest(out / "baseset/opentt3d-voxels.json"),
    "source_sha256":{name:digest(Path(name)) for name in paths},
    "build_log_sha256":digest(root / "breadth-original-lock-canonical-projection-build.log"),
    "head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
    "exact_tag_binary":False,"models":1879,"runtime_bindings_changed":False,"geometry_approvals":0,
    "scope":"Local unaccepted explicit-column projection arithmetic diagnostic on the unchanged first48 lock studies and unchanged1831 released models/bindings. No camera/geometry/precision tolerance/mask changed. Source original/rejected views remain retained. This is not .42 or a runtime lock replacement."}
old_manifest = json.loads((old / "manifest.json").read_text())
assert manifest["catalogue_sha256"] == old_manifest["catalogue_sha256"]
(out / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
fixture = root / "breadth-original-lock-temperate-natural-resources-fixture"
rows = []
for backend in ("vulkan","opengl"):
    output = root / f"breadth-original-lock-canonical-projection-{backend}"
    command = ["python3","tools/opentt3d/smoke.py","--build-dir",str(out),"--output",str(output),"--background","--backend",backend,
        "--savegame",str(fixture / "save/lock-fixture.sav"),"--ai-dir",str(fixture / "ai"),"--center","101","4",
        "--gallery-voxel-prefix","lock_study_","--gallery-voxel-overview","--verify-world-atlas","--verify-tile-picking",
        "--synchronous-save","--resolution","640","480","--timeout","600","--brief"]
    result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
    rows.append({"backend":backend,"output":str(output),"exit_code":result.returncode,"command":command})
    (root / "breadth-original-lock-canonical-projection-runs.json").write_text(json.dumps(rows,indent=2)+"\n")
    assert result.returncode == 0
    assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
comparisons = []
for mode,reference,actual in (("paired",root / "breadth-original-lock-canonical-projection-vulkan",root / "breadth-original-lock-canonical-projection-opengl"),
    ("vulkan-prior",root / "breadth-original-lock-authored-study-vulkan",root / "breadth-original-lock-canonical-projection-vulkan"),
    ("opengl-prior",root / "breadth-original-lock-authored-study-opengl",root / "breadth-original-lock-canonical-projection-opengl")):
    report = root / f"breadth-original-lock-canonical-projection-{mode}-strict.json"
    result = subprocess.run([python,"tools/assets/compare_galleries.py",str(reference / "renderer3d-reference"),str(actual / "renderer3d-reference"),
        "--pattern","model-voxel-lock_study_*","--output",str(report)])
    assert result.returncode in (0,1)
    compared = json.loads(report.read_text())
    assert compared["images"] == 432
    comparisons.append({"mode":mode,"report":str(report),"sha256":digest(report),"exit_code":result.returncode,
        "different_images":len(compared["differences"]),"different_pixels":sum(row.get("changed_pixels",0) for row in compared["differences"])})
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"comparisons":comparisons,
    "paired_strict_exact":comparisons[0]["exit_code"] == 0,"scope":manifest["scope"],"approvals":0}
(root / "breadth-original-lock-canonical-projection-verification.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary))
if not summary["paired_strict_exact"]:
    raise SystemExit(1)

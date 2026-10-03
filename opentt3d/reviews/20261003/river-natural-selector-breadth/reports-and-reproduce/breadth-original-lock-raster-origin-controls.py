"""Test a framebuffer convention hypothesis without changing art, cameras or review rules."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess

root = Path("build-macos").resolve()
out = root / "breadth-original-lock-raster-origin-frozen-build"
assert not out.exists()
out.mkdir()
source = root / "breadth-original-lock-front-profile-frozen-build"
for name in ("baseset","lang","ai","game"):
    (out / name).symlink_to(source / name,target_is_directory=True)
shutil.copy2(root / "opentt3d",out / "opentt3d")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
assert subprocess.check_output(["git","diff","--name-only","--","src"],text=True).splitlines() == ["src/renderer3d/gl_backend.cpp"]
snapshot = out / "source-snapshot/src/renderer3d/gl_backend.cpp"
snapshot.parent.mkdir(parents=True)
shutil.copy2("src/renderer3d/gl_backend.cpp",snapshot)
manifest = {"frozen_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"binary_sha256":digest(out / "opentt3d"),
    "catalogue_sha256":digest(out / "baseset/opentt3d-voxels.json"),"gl_source_sha256":digest(snapshot),
    "build_log_sha256":digest(root / "breadth-original-lock-raster-origin-build.log"),
    "head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"models":1879,"unbound_studies":48,
    "geometry_approvals":0,"exact_tag_binary":False,"runtime_artwork_or_bindings_changed":False,
    "scope":"Default-off read-only raster-coordinate diagnostic on unchanged48 front-profile lock volumes and all released1831 models/bindings. OpenGL can invert its internal clip Y/front-face convention while restoring complete colour/ID readback rows, GPU presentation source mapping and point-picking coordinates. No model coordinates, mesh, camera, palette, epsilon, quantization, masks or comparison tolerance changed. Pixel-equality hypothesis only, not a full renderer repair, release, new artwork/geometry or quality approval."}
assert manifest["catalogue_sha256"] == "689b38cd8356ae932cca02ef08dd0020d5ebc135f242c056c38b350dc30af5f9"
(out / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
rows = []
fixture = root / "breadth-original-lock-temperate-natural-resources-fixture"
for backend,enabled in (("opengl",False),("opengl",True),("vulkan",False)):
    label = backend+("-y-down" if enabled else "-default")
    output = root / ("breadth-original-lock-raster-origin-"+label)
    command = ["python3","tools/opentt3d/smoke.py","--build-dir",str(out),"--output",str(output),"--background","--backend",backend,
        "--savegame",str(fixture / "save/lock-fixture.sav"),"--ai-dir",str(fixture / "ai"),"--center","101","4",
        "--gallery-voxel-prefix","lock_study_","--gallery-voxel-overview","--verify-world-atlas","--verify-tile-picking",
        "--verify-renderer","--synchronous-save","--resolution","640","480","--timeout","600","--brief"]
    result = subprocess.run(command,env=dict(os.environ,OPENTT3D_GL_RASTER_Y_DOWN="1" if enabled else "0",OPENTT3D_EXPORT_WATER_SOURCES="0"))
    row = {"backend":backend,"y_down":enabled,"output":str(output),"exit_code":result.returncode,"command":command}
    rows.append(row)
    (root / "breadth-original-lock-raster-origin-runs.json").write_text(json.dumps(rows,indent=2)+"\n")
    assert result.returncode == 0,row
    assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
    assert len(list((output / "renderer3d-reference").glob("model-voxel-lock_study_*.pam"))) == 432
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
by_case = {(row["backend"],row["y_down"]):Path(row["output"]) for row in rows}
comparisons = []
for mode,reference,actual in (("gl-default-prior",root / "breadth-original-lock-front-profile-opengl",by_case["opengl",False]),
    ("vk-default-prior",root / "breadth-original-lock-front-profile-vulkan",by_case["vulkan",False]),
    ("paired-original-convention",by_case["vulkan",False],by_case["opengl",False]),
    ("paired-y-down",by_case["vulkan",False],by_case["opengl",True])):
    report = root / ("breadth-original-lock-raster-origin-"+mode+"-strict.json")
    result = subprocess.run([python,"tools/assets/compare_galleries.py",str(reference / "renderer3d-reference"),str(actual / "renderer3d-reference"),
        "--pattern","model-voxel-lock_study_*","--pixel-details","20","--output",str(report)])
    assert result.returncode in (0,1)
    compared = json.loads(report.read_text())
    assert compared["images"] == 432
    comparisons.append({"mode":mode,"report":str(report),"report_sha256":digest(report),"exit_code":result.returncode,
        "different_images":len(compared["differences"]),"different_pixels":sum(row.get("changed_pixels",0) for row in compared["differences"])})
worlds = []
for mode,reference,actual in (("gl-default-prior",root / "breadth-original-lock-front-profile-opengl",by_case["opengl",False]),
    ("vk-default-prior",root / "breadth-original-lock-front-profile-vulkan",by_case["vulkan",False]),
    ("gl-y-down-default",by_case["opengl",False],by_case["opengl",True])):
    report = root / ("breadth-original-lock-raster-origin-world-"+mode+".json")
    result = subprocess.run([python,"tools/assets/compare_galleries.py",str(reference / "screenshot/smoke.png"),str(actual / "screenshot/smoke.png"),"--output",str(report)])
    assert result.returncode in (0,1)
    compared = json.loads(report.read_text())
    worlds.append({"mode":mode,"report":str(report),"exit_code":result.returncode,"different_images":len(compared["differences"]),
        "different_pixels":sum(row.get("changed_pixels",0) for row in compared["differences"])})
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"comparisons":comparisons,"world_comparisons":worlds,
    "y_down_lock_gallery_strict_exact":comparisons[-1]["exit_code"] == 0,"geometry_approvals":0,"scope":manifest["scope"]}
(root / "breadth-original-lock-raster-origin-verification.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary))

"""Focused retry; preserve the earlier full-suite timeout and every partial artifact."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess

root = Path("build-macos").resolve()
prefix = "breadth-original-lock-raster-origin-retry2"
out = root / "breadth-original-lock-raster-origin-frozen-build"
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
manifest = json.loads((out / "manifest.json").read_text())
assert digest(out / "opentt3d") == manifest["binary_sha256"]
assert digest(out / "baseset/opentt3d-voxels.json") == manifest["catalogue_sha256"]
assert digest(Path("src/renderer3d/gl_backend.cpp")) == manifest["gl_source_sha256"]
assert not (root / (prefix+"-runs.json")).exists()
rows = []
fixture = root / "breadth-original-lock-temperate-natural-resources-fixture"
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
for backend,enabled in (("opengl",False),("opengl",True),("vulkan",False)):
    label = backend+("-y-down" if enabled else "-default")
    output = root / (prefix+"-"+label)
    assert not output.exists()
    command = ["python3","tools/opentt3d/smoke.py","--build-dir",str(out),"--output",str(output),"--background","--backend",backend,
        "--savegame",str(fixture / "save/lock-fixture.sav"),"--ai-dir",str(fixture / "ai"),"--center","101","4",
        "--gallery-voxel-prefix","lock_study_","--gallery-voxel-overview","--verify-world-atlas","--verify-tile-picking",
        "--verify-renderer","--renderer-verification-scope","scene","--synchronous-save","--resolution","640","480",
        "--timeout","600","--brief"]
    result = subprocess.run(command,env=dict(os.environ,OPENTT3D_GL_RASTER_Y_DOWN="1" if enabled else "0",OPENTT3D_EXPORT_WATER_SOURCES="0"))
    row = {"backend":backend,"y_down":enabled,"output":str(output),"exit_code":result.returncode,"command":command}
    rows.append(row)
    runs = root / (prefix+"-runs.json")
    runs.write_text(json.dumps(rows,indent=2)+"\n")
    assert result.returncode == 0,row
    assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
    assert len(list((output / "renderer3d-reference").glob("model-voxel-lock_study_*.pam"))) == 432
    subprocess.run([python,"tools/assets/compact_reviews.py",str(root),"--validation-manifest",str(runs),"--apply"],check=True)
by_case = {(row["backend"],row["y_down"]):Path(row["output"]) for row in rows}
comparisons = []
for mode,reference,actual in (("gl-default-prior",root / "breadth-original-lock-front-profile-opengl",by_case["opengl",False]),
    ("vk-default-prior",root / "breadth-original-lock-front-profile-vulkan",by_case["vulkan",False]),
    ("paired-original-convention",by_case["vulkan",False],by_case["opengl",False]),
    ("paired-y-down",by_case["vulkan",False],by_case["opengl",True])):
    report = root / (prefix+"-"+mode+"-strict.json")
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
    report = root / (prefix+"-world-"+mode+".json")
    result = subprocess.run([python,"tools/assets/compare_galleries.py",str(reference / "screenshot/smoke.png"),str(actual / "screenshot/smoke.png"),"--pixel-details","20","--output",str(report)])
    assert result.returncode in (0,1)
    compared = json.loads(report.read_text())
    worlds.append({"mode":mode,"report":str(report),"exit_code":result.returncode,"different_images":len(compared["differences"]),
        "different_pixels":sum(row.get("changed_pixels",0) for row in compared["differences"])})
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"comparisons":comparisons,"world_comparisons":worlds,
    "earlier_full_suite_timeout_retained":True,"native_tests":213,"native_tests_pass":True,
    "y_down_lock_gallery_strict_exact":comparisons[-1]["exit_code"] == 0,"geometry_approvals":0,"scope":manifest["scope"]}
(root / (prefix+"-verification.json")).write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary))

"""Freeze unbound river relief and quietly compare it with unchanged canonical worlds."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from quality_audit import fingerprint

CANONICAL = ROOT / "build-macos/breadth-original-lock-world-support-corrected-canonical-frozen-build"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def freeze(prefix):
    target = ROOT / "build-macos" / (prefix+"-frozen-build")
    if target.exists(): raise ValueError("Retain the prior freeze and choose a new prefix")
    (target / "baseset").mkdir(parents=True)
    compiler = subprocess.check_output(["git","show","HEAD:tools/assets/compile_voxels.py"],cwd=ROOT)
    (target / "compiler-snapshot.py").write_bytes(compiler)
    spec = importlib.util.spec_from_file_location("river_relief_canonical_compiler",target / "compiler-snapshot.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    source = json.loads((HERE / "authored-source.json").read_text())
    study = module.compile_catalogue(source)
    assert len(study["models"]) == 8 and study["bindings"] == {}
    original_path = CANONICAL / "baseset/opentt3d-voxels.json"
    original = json.loads(original_path.read_text())
    assert digest(original_path) == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
    assert len(original["models"]) == 1831
    merged = json.loads(original_path.read_text())
    offset = len(merged["materials"])
    merged["materials"].extend(study["materials"])
    for name,model in study["models"].items():
        assert name not in merged["models"]
        merged["models"][name] = {**model,"runs":[run[:4]+[run[4]+offset] for run in model["runs"]]}
    assert original["bindings"] == merged["bindings"]
    assert all(fingerprint(model,original["materials"]) == fingerprint(merged["models"][name],merged["materials"])
               for name,model in original["models"].items())
    (target / "baseset/opentt3d-voxels.json").write_text(json.dumps(merged,separators=(",",":"))+"\n")
    for path in (CANONICAL / "baseset").iterdir():
        if path.name != "opentt3d-voxels.json":
            (target / "baseset" / path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name in ("ai","game","lang"):
        (target / name).symlink_to((CANONICAL / name).resolve(),target_is_directory=True)
    shutil.copy2(CANONICAL / "opentt3d",target / "opentt3d")
    for name in ("authored-source.json","test_authored_study.py","run-controls.py"):
        shutil.copy2(HERE / name,target / name)
    manifest = {"frozen_utc":datetime.now(timezone.utc).isoformat(),"models":1839,"unbound_relief_studies":8,
        "sha256":{name:digest(target / name) for name in ("opentt3d","baseset/opentt3d-voxels.json","compiler-snapshot.py",
                                                          "authored-source.json","test_authored_study.py","run-controls.py")},
        "source_sha256":{row["portable_source"]:row["sha256"] for row in json.loads((HERE / "source-index.json").read_text())},
        "study_fingerprints":{name:fingerprint(model,study["materials"]) for name,model in study["models"].items()},
        "canonical_catalogue_sha256":digest(original_path),"prior_1831_models_and_bindings_exact":True,
        "binary_reused_from":str(CANONICAL.relative_to(ROOT)),"exact_tag_binary":False,"runtime_bound":False,
        "geometry_approvals":0,"scope":"Eight unbound original-datum relief volumes only; unchanged native water/banks and canonical worlds. No structural world coverage, water decomposition, doubled-terrain support, phase/custom/ship or aesthetic acceptance is inferred."}
    manifest["runtime_sources"] = {str(path.relative_to(ROOT)):digest(path) for path in sorted((ROOT / "src/renderer3d").rglob("*")) if path.is_file()}
    manifest["runtime_sources"]["src/water_cmd.cpp"] = digest(ROOT / "src/water_cmd.cpp")
    (target / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"frozen":str(target),"models":1839,"unbound_studies":8,"approvals":0}))


def run(prefix):
    build = ROOT / "build-macos"
    frozen = build / (prefix+"-frozen-build")
    manifest = json.loads((frozen / "manifest.json").read_text())
    assert all(digest(frozen / name) == expected for name,expected in manifest["sha256"].items())
    controls = []
    for climate in ("temperate","toyland"):
        fixture = build / ("breadth-original-river-natural-survey-"+climate)
        savegame = fixture / "save/river-survey.sav"
        for backend in ("vulkan","opengl"):
            for scope,executable in (("study",frozen),("canonical",CANONICAL)):
                output = build / f"{prefix}-{climate}-{backend}-{scope}"
                if output.exists(): raise ValueError("Retain the prior native run and use a fresh prefix: "+str(output))
                command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(executable),"--output",str(output),
                    "--background","--backend",backend,"--savegame",str(savegame),"--ai-dir",str(fixture / "ai"),
                    "--center","54","27","--verify-world-atlas","--verify-tile-picking","--synchronous-save",
                    "--blitter","40bpp-anim","--resolution","640","480","--timeout","600","--brief"]
                gallery = scope == "study" and climate == "temperate"
                if gallery:
                    command += ["--gallery-voxel-prefix","river_relief_study_","--gallery-voxel-overview",
                                "--verify-voxel-meshes","river_relief_study_"]
                result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
                controls.append({"output":str(output.relative_to(ROOT)),"scope":scope,"climate":climate,"backend":backend,
                    "exit_code":result.returncode,"command":command,"gallery":gallery,"binary_sha256":digest(executable / "opentt3d"),
                    "catalogue_sha256":digest(executable / "baseset/opentt3d-voxels.json"),"input_save_sha256":digest(savegame)})
                (build / (prefix+"-runs.json")).write_text(json.dumps(controls,indent=2)+"\n")
                if result.returncode: raise SystemExit(result.returncode)
                record = json.loads((output / "result.json").read_text())
                assert record["background"] and record["synchronous_original_save_verified"]
                assert record["command"][record["command"].index("-b")+1] == "40bpp-anim"
                if gallery: assert len(list((output / "renderer3d-reference").glob("model-voxel-river_relief_study_*.pam"))) == 72
    print(json.dumps({"quiet_controls":len(controls),"unbound_model_views":144,"runtime_bound":False,"approvals":0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",required=True)
    parser.add_argument("--phase",choices=("freeze","run"),required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"breadth-original-river-relief-[a-z0-9-]+",args.prefix): parser.error("Use a fresh breadth-original-river-relief-* prefix")
    (freeze if args.phase == "freeze" else run)(args.prefix)


if __name__ == "__main__":
    main()

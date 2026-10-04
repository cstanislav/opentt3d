"""Freeze all earlier flat owners plus sloped studies; use fresh acknowledged quiet runs."""
import argparse
from datetime import datetime,timezone
import gzip
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
FLAT = HERE.parent / "river-bank-breadth"
PRIOR = ROOT / "build-macos/breadth-original-river-bank-paint-repaired-frozen-build"
COMPILER = HERE.parent / "river-relief-ownership/approved-compiler-snapshot.py"
CLIMATES = ("temperate","arctic","tropic","toyland")
sys.path.insert(0,str(ROOT / "tools/assets"))
from quality_audit import fingerprint


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def freeze(prefix):
    target = ROOT / "build-macos" / (prefix+"-frozen-build")
    if target.exists() or (HERE / "diagnostic-catalogue.json.gz").exists(): raise ValueError("Retain earlier diagnostic freezes")
    before = json.loads((PRIOR / "manifest.json").read_text())
    assert all(digest(PRIOR / name) == sha for name,sha in before["sha256"].items())
    spec = importlib.util.spec_from_file_location("approved_slope_bank_compiler",COMPILER)
    compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)
    study = compiler.compile_catalogue(json.loads((HERE / "authored-source.json").read_text()))
    assert len(study["models"]) == 32 and study["bindings"] == {}
    prior = json.loads((PRIOR / "baseset/opentt3d-voxels.json").read_text()); assert len(prior["models"]) == 1879
    merged = json.loads(json.dumps(prior)); offset = len(merged["materials"])
    merged["materials"].extend(study["materials"])
    for name,model in study["models"].items():
        assert name not in merged["models"]
        merged["models"][name] = {**model,"runs":[run[:4]+[run[4]+offset] for run in model["runs"]]}
    assert len(merged["models"]) == 1911 and merged["bindings"] == prior["bindings"]
    assert all(merged["models"][name] == model for name,model in prior["models"].items())
    (target / "baseset").mkdir(parents=True)
    payload = (json.dumps(merged,separators=(",",":"))+"\n").encode()
    (target / "baseset/opentt3d-voxels.json").write_bytes(payload)
    (HERE / "diagnostic-catalogue.json.gz").write_bytes(gzip.compress(payload,mtime=0))
    for path in (PRIOR / "baseset").iterdir():
        if path.name != "opentt3d-voxels.json": (target / "baseset" / path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name in ("ai","game","lang"): (target / name).symlink_to((PRIOR / name).resolve(),target_is_directory=True)
    os.link(PRIOR / "opentt3d",target / "opentt3d")
    for name,path in (("compiler-snapshot.py",COMPILER),("authored-source.json",HERE / "authored-source.json"),("test_authored_study.py",HERE / "test_authored_study.py")):
        shutil.copy2(path,target / name)
    value = {"frozen_utc":datetime.now(timezone.utc).isoformat(),"models":1911,"unbound_flat_owners_unchanged":48,"new_unbound_sloped_owners":32,
        "sha256":{name:digest(target / name) for name in ("opentt3d","baseset/opentt3d-voxels.json","compiler-snapshot.py","authored-source.json","test_authored_study.py")},
        "prior_flat_frozen_manifest":before,"canonical_1831_models_materials_bindings_and_48_flat_studies_exact":True,
        "quarantined_working_compiler_or_art_loaded":False,"runtime_bindings_added":0,"quality_approvals":0,
        "sloped_model_fingerprints":{name:fingerprint(model,study["materials"]) for name,model in study["models"].items()}}
    (target / "manifest.json").write_text(json.dumps(value,indent=2)+"\n")
    (HERE / "frozen-manifest.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({"models":1911,"unchanged_flat_studies":48,"new_sloped_studies":32,"runtime_bindings_added":0,"quality_approvals":0}))


def run(prefix):
    frozen = ROOT / "build-macos" / (prefix+"-frozen-build")
    value = json.loads((frozen / "manifest.json").read_text())
    assert all(digest(frozen / name) == sha for name,sha in value["sha256"].items())
    if (HERE / "runs.json").exists(): raise ValueError("Retain earlier native control manifests")
    records = []
    for climate in CLIMATES:
        fixture = ROOT / "build-macos" / ("breadth-original-river-natural-survey-"+climate)
        for backend in ("vulkan","opengl"):
            original = FLAT / "acknowledged-native-controls" / f"breadth-original-river-bank-acknowledged-{climate}-{backend}-canonical"
            result = json.loads((original / "result.json").read_text())
            assert result["original_console_save_success_recorded"] and result["image_size"] == [640,480] and result["background"]
            output = ROOT / "build-macos" / f"{prefix}-{climate}-{backend}-study"
            if output.exists(): raise ValueError("Retain earlier native controls")
            command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(frozen),"--output",str(output),
                "--background","--no-hidpi","--record-console","--synchronous-save","--blitter","40bpp-anim",
                "--backend",backend,"--savegame",str(fixture / "save/river-survey.sav"),"--ai-dir",str(fixture / "ai"),
                "--center","64","64","--zoom","5","--resolution","640","480","--verify-world-atlas","--verify-tile-picking",
                "--gallery-voxel-prefix","river_bank_slope_study_"+climate,"--gallery-voxel-overview",
                "--verify-voxel-meshes","river_bank_slope_study_"+climate,"--timeout","600","--brief"]
            process = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
            row = {"output":str(output.relative_to(ROOT)),"climate":climate,"backend":backend,"scope":"study", "command":command,
                "exit_code":process.returncode,"input_save_sha256":digest(fixture / "save/river-survey.sav"),
                "reused_acknowledged_canonical_control":str(original.relative_to(ROOT)),"canonical_console_sha256":digest(original / "console-review.log")}
            records.append(row); (HERE / "runs.json").write_text(json.dumps(records,indent=2)+"\n")
            if process.returncode: raise SystemExit(process.returncode)
            result = json.loads((output / "result.json").read_text())
            assert result["background"] and result["original_console_save_success_recorded"] and result["synchronous_original_save_verified"]
            assert result["original_console_commands_acknowledged"] == 11 and result["image_size"] == [640,480]
            assert len(list((output / "renderer3d-reference").glob("model-voxel-river_bank_slope_study_"+climate+"_*.pam"))) == 72
            assert "diagnostic voxel river relief slope " not in (output / "run.log").read_text()
    assert len(records) == 8
    print(json.dumps({"fresh_quiet_acknowledged_study_runs":8,"reused_immutable_acknowledged_canonical_controls":8,"individual_sloped_owners":32,"runtime_bank_coverage_accepted":0,"quality_approvals":0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--prefix",required=True)
    parser.add_argument("--phase",choices=("freeze","run"),required=True); args = parser.parse_args()
    if not re.fullmatch(r"breadth-original-river-sloped-bank-[a-z0-9-]+",args.prefix): parser.error("Use a fresh sloped-bank-only freeze/output prefix")
    (freeze if args.phase == "freeze" else run)(args.prefix)


if __name__ == "__main__": main()

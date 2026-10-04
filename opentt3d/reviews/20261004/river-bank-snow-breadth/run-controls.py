"""Isolate new snow volumes and retain quiet acknowledged original-world controls."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREFIX = "breadth-original-river-bank-snow-initial"
FROZEN = ROOT / "build-macos" / (PREFIX+"-frozen-build")
PRIOR = ROOT / "build-macos/breadth-original-river-sloped-bank-initial-frozen-build"
COMPILER = HERE.parent / "river-relief-ownership/approved-compiler-snapshot.py"
sys.path.insert(0,str(ROOT / "tools/assets"))
from quality_audit import fingerprint


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def freeze():
    if FROZEN.exists() or (HERE / "diagnostic-catalogue.json.gz").exists(): raise ValueError("Retain prior snow freezes")
    before = json.loads((PRIOR / "manifest.json").read_text())
    assert all(digest(PRIOR / name) == sha for name,sha in before["sha256"].items())
    spec = importlib.util.spec_from_file_location("approved_snow_compiler",COMPILER)
    compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)
    study = compiler.compile_catalogue(json.loads((HERE / "authored-source.json").read_text()))
    assert len(study["models"]) == 20 and study["bindings"] == {}
    prior = json.loads((PRIOR / "baseset/opentt3d-voxels.json").read_text()); assert len(prior["models"]) == 1911
    merged = json.loads(json.dumps(prior)); offset = len(merged["materials"])
    merged["materials"].extend(study["materials"])
    for name,model in study["models"].items():
        assert name not in merged["models"]
        merged["models"][name] = {**model,"runs":[run[:4]+[run[4]+offset] for run in model["runs"]]}
    assert len(merged["models"]) == 1931 and merged["bindings"] == prior["bindings"]
    assert all(merged["models"][name] == model for name,model in prior["models"].items())
    (FROZEN / "baseset").mkdir(parents=True)
    payload = (json.dumps(merged,separators=(",",":"))+"\n").encode()
    (FROZEN / "baseset/opentt3d-voxels.json").write_bytes(payload)
    (HERE / "diagnostic-catalogue.json.gz").write_bytes(gzip.compress(payload,mtime=0))
    for path in (PRIOR / "baseset").iterdir():
        if path.name != "opentt3d-voxels.json": (FROZEN / "baseset" / path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name in ("ai","game","lang"): (FROZEN / name).symlink_to((PRIOR / name).resolve(),target_is_directory=True)
    os.link(PRIOR / "opentt3d",FROZEN / "opentt3d")
    for name,path in (("compiler-snapshot.py",COMPILER),("authored-source.json",HERE / "authored-source.json"),("test_authored_study.py",HERE / "test_authored_study.py")):
        shutil.copy2(path,FROZEN / name)
    value = {"frozen_utc":datetime.now(timezone.utc).isoformat(),"models":1931,"canonical_models_exact":1831,"earlier_unbound_banks_exact":80,
        "new_unbound_snow_owners":20,"sha256":{name:digest(FROZEN / name) for name in ("opentt3d","baseset/opentt3d-voxels.json","compiler-snapshot.py","authored-source.json","test_authored_study.py")},
        "prior_sloped_frozen_manifest":before,"canonical_and_earlier_bank_models_materials_bindings_exact":True,
        "quarantined_working_art_or_compiler_loaded":False,"runtime_bindings_added":0,"quality_approvals":0,
        "snow_model_fingerprints":{name:fingerprint(model,study["materials"]) for name,model in study["models"].items()}}
    (FROZEN / "manifest.json").write_text(json.dumps(value,indent=2)+"\n")
    (HERE / "frozen-manifest.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps({"models":1931,"new_snow_models":20,"earlier_bank_owners_exact":80,"quality_approvals":0}))


def run():
    manifest = json.loads((FROZEN / "manifest.json").read_text())
    assert all(digest(FROZEN / name) == sha for name,sha in manifest["sha256"].items())
    if (HERE / "runs.json").exists(): raise ValueError("Retain prior snow review runs")
    fixture = ROOT / "build-macos/breadth-original-river-natural-survey-arctic"; records = []
    for backend in ("vulkan","opengl"):
        canonical = HERE.parent / "river-bank-breadth/acknowledged-native-controls" / f"breadth-original-river-bank-acknowledged-arctic-{backend}-canonical"
        original = json.loads((canonical / "result.json").read_text())
        assert original["original_console_save_success_recorded"] and original["image_size"] == [640,480] and original["background"]
        output = ROOT / "build-macos" / (PREFIX+"-arctic-"+backend+"-study")
        if output.exists(): raise ValueError("Retain prior native snow reviews")
        command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(FROZEN),"--output",str(output),"--background","--no-hidpi",
            "--record-console","--synchronous-save","--blitter","40bpp-anim","--backend",backend,
            "--savegame",str(fixture / "save/river-survey.sav"),"--ai-dir",str(fixture / "ai"),"--center","64","64","--zoom","5",
            "--resolution","640","480","--verify-world-atlas","--verify-tile-picking","--gallery-voxel-prefix","river_bank_snow_study_arctic_",
            "--gallery-voxel-overview","--verify-voxel-meshes","river_bank_snow_study_arctic_","--timeout","600","--brief"]
        process = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
        row = {"output":str(output.relative_to(ROOT)),"climate":"arctic","backend":backend,"scope":"study","command":command,
            "exit_code":process.returncode,"input_save_sha256":digest(fixture / "save/river-survey.sav"),
            "reused_acknowledged_canonical_control":str(canonical.relative_to(ROOT)),"canonical_console_sha256":digest(canonical / "console-review.log")}
        records.append(row); (HERE / "runs.json").write_text(json.dumps(records,indent=2)+"\n")
        if process.returncode: raise SystemExit(process.returncode)
        result = json.loads((output / "result.json").read_text())
        assert result["background"] and result["image_size"] == [640,480] and result["original_console_commands_acknowledged"] == 11
        assert result["synchronous_original_save_verified"] and result["original_console_save_success_recorded"]
        assert len(list((output / "renderer3d-reference").glob("model-voxel-river_bank_snow_study_arctic_*.pam"))) == 180
    print(json.dumps({"fresh_acknowledged_quiet_study_runs":2,"reused_immutable_acknowledged_canonical_controls":2,"models":20,"model_images":360,"quality_approvals":0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--phase",choices=("freeze","run"),required=True); args = parser.parse_args()
    (freeze if args.phase == "freeze" else run)()


if __name__ == "__main__": main()

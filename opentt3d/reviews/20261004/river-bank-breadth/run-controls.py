"""Freeze new unbound bank volumes and render each climate without touching canonical art."""
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
CANONICAL = ROOT / "build-macos/breadth-original-river-relief-world-observer-separated-canonical-frozen-build"
COMPILER = ROOT / "opentt3d/reviews/20261004/river-relief-ownership/approved-compiler-snapshot.py"
CLIMATES = ("temperate","arctic","tropic","toyland")
sys.path.insert(0,str(ROOT / "tools/assets"))
from quality_audit import fingerprint


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def freeze(prefix,phase):
    source_path = HERE / ("authored-source.json" if phase == "initial" else phase+"-authored-source.json")
    catalogue_path = HERE / ("diagnostic-catalogue.json.gz" if phase == "initial" else phase+"-diagnostic-catalogue.json.gz")
    manifest_path = HERE / ("frozen-manifest.json" if phase == "initial" else phase+"-frozen-manifest.json")
    if catalogue_path.exists() or manifest_path.exists(): raise ValueError("Retain previous portable diagnostic catalogues")
    target = ROOT / "build-macos" / (prefix+"-frozen-build")
    if target.exists(): raise ValueError("Retain earlier diagnostic catalogues")
    (target / "baseset").mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("approved_bank_compiler",COMPILER)
    compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)
    source = json.loads(source_path.read_text())
    study = compiler.compile_catalogue(source)
    assert len(study["models"]) == 48 and study["bindings"] == {}
    canonical = json.loads((CANONICAL / "baseset/opentt3d-voxels.json").read_text())
    assert len(canonical["models"]) == 1831 and "river_relief" not in canonical["bindings"]
    merged = json.loads(json.dumps(canonical)); offset = len(merged["materials"])
    merged["materials"].extend(study["materials"])
    for name,model in study["models"].items():
        assert name not in merged["models"]
        merged["models"][name] = {**model,"runs":[run[:4]+[run[4]+offset] for run in model["runs"]]}
    assert all(merged["models"][name] == model for name,model in canonical["models"].items())
    assert merged["bindings"] == canonical["bindings"]
    payload = (json.dumps(merged,separators=(",",":"))+"\n").encode()
    (target / "baseset/opentt3d-voxels.json").write_bytes(payload)
    catalogue_path.write_bytes(gzip.compress(payload,mtime=0))
    for path in (CANONICAL / "baseset").iterdir():
        if path.name != "opentt3d-voxels.json": (target / "baseset" / path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name in ("ai","game","lang"): (target / name).symlink_to((CANONICAL / name).resolve(),target_is_directory=True)
    os.link(CANONICAL / "opentt3d",target / "opentt3d")
    for name,path in (("compiler-snapshot.py",COMPILER),("authored-source.json",source_path),("test_authored_study.py",HERE / "test_authored_study.py")):
        shutil.copy2(path,target / name)
    value = {"frozen_utc":datetime.now(timezone.utc).isoformat(),"models":1879,"unbound_bank_models":48,
        "sha256":{name:digest(target / name) for name in ("opentt3d","baseset/opentt3d-voxels.json","compiler-snapshot.py","authored-source.json","test_authored_study.py")},
        "canonical_manifest":json.loads((CANONICAL / "manifest.json").read_text()),"canonical_1831_models_materials_and_bindings_exact":True,
        "compiler_quarantined_clip_any_loaded":False,"runtime_bindings":0,"geometry_approvals":0,
        "model_fingerprints":{name:fingerprint(model,study["materials"]) for name,model in study["models"].items()}}
    (target / "manifest.json").write_text(json.dumps(value,indent=2)+"\n")
    manifest_path.write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({"models":1879,"unbound_bank_models":48,"runtime_bindings":0,"quality_approvals":0}))


def run(prefix,phase,climates,frozen_prefix=None,record_console=False):
    study = ROOT / "build-macos" / ((frozen_prefix or prefix)+"-frozen-build")
    value = json.loads((study / "manifest.json").read_text())
    assert all(digest(study / name) == sha for name,sha in value["sha256"].items())
    records = []
    for climate in climates:
        fixture = ROOT / "build-macos" / ("breadth-original-river-natural-survey-"+climate)
        for backend in ("vulkan","opengl"):
            for scope,frozen in (("canonical",CANONICAL),("study",study)):
                output = ROOT / "build-macos" / f"{prefix}-{climate}-{backend}-{scope}"
                if output.exists(): raise ValueError("Retain previous native controls")
                command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(frozen),"--output",str(output),
                    "--background","--no-hidpi","--backend",backend,"--savegame",str(fixture / "save/river-survey.sav"),
                    "--ai-dir",str(fixture / "ai"),"--center","64","64","--zoom","5","--verify-world-atlas","--verify-tile-picking",
                    "--synchronous-save","--blitter","40bpp-anim","--resolution","640","480","--timeout","600","--brief"]
                if scope == "study": command += ["--gallery-voxel-prefix","river_bank_study_"+climate,"--gallery-voxel-overview","--verify-voxel-meshes","river_bank_study_"+climate]
                if record_console: command.append("--record-console")
                result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
                records.append({"output":str(output.relative_to(ROOT)),"climate":climate,"backend":backend,"scope":scope,"command":command,
                    "exit_code":result.returncode,"input_save_sha256":digest(fixture / "save/river-survey.sav"),"gallery":scope == "study"})
                (HERE / (prefix+"-runs.json")).write_text(json.dumps(records,indent=2)+"\n")
                if result.returncode: raise SystemExit(result.returncode)
                record = json.loads((output / "result.json").read_text())
                assert record["background"] and record["synchronous_original_save_verified"] and record["image_size"] == [640,480]
                if record_console:
                    assert record["original_console_save_success_recorded"] and record["original_console_commands_acknowledged"] >= 9
                    assert "Map successfully saved to '" in (output / "console-review.log").read_text()
                assert "diagnostic voxel river relief slope " not in (output / "run.log").read_text()
                if scope == "study": assert len(list((output / "renderer3d-reference").glob("model-voxel-river_bank_study_"+climate+"_flat_*.pam"))) == 108
    assert len(records) == len(climates)*4
    print(json.dumps({"quiet_controls":len(records),"individual_bank_models":48,"gallery_climates":list(climates),"runtime_bound":False,"quality_approvals":0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",required=True); parser.add_argument("--phase",choices=("freeze","run"),required=True)
    parser.add_argument("--revision",choices=("initial","revised","snow-repaired","paint-repaired"),default="initial")
    parser.add_argument("--climates",nargs="+",choices=CLIMATES,default=CLIMATES)
    parser.add_argument("--frozen-prefix",help="Reuse only a retained, hash-verified immutable diagnostic build for fresh run outputs")
    parser.add_argument("--record-console",action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"breadth-original-river-bank-[a-z0-9-]+",args.prefix): parser.error("Use a fresh breadth-original-river-bank-* prefix")
    if args.frozen_prefix and not re.fullmatch(r"breadth-original-river-bank-[a-z0-9-]+",args.frozen_prefix): parser.error("Use a retained bank-only freeze")
    if args.phase == "freeze": freeze(args.prefix,args.revision)
    else: run(args.prefix,args.revision,tuple(dict.fromkeys(args.climates)),args.frozen_prefix,args.record_console)


if __name__ == "__main__": main()

"""Freeze diagnostic relief/water owners and test saved worlds plus complete fallbacks."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "river-relief-breadth"
RESOURCES = ROOT / "build-macos/breadth-original-lock-world-support-corrected-canonical-frozen-build"
SCOPES = ("canonical","complete","missing-owner","missing-water","changed-source")
CLIMATES = ("temperate","arctic","tropic","toyland")


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def freeze(prefix):
    canonical = json.loads(gzip.decompress((PRIOR / "canonical-catalogue.json.gz").read_bytes()))
    study = json.loads(gzip.decompress((PRIOR / "revised-native-controls/diagnostic-catalogue.json.gz").read_bytes()))
    bindings = {str(slope):{str(climate):f"river_relief_study_{'island' if climate == 3 else 'rock'}_{label}"
                           for climate in range(4)} for slope,label in ((3,"sw"),(6,"se"),(9,"nw"),(12,"ne"))}
    water = json.loads((HERE / "water-source-study/authored-river-water.json").read_text())
    for scope in SCOPES:
        target = ROOT / "build-macos" / (prefix+"-"+scope+"-frozen-build")
        if target.exists(): raise ValueError("Retain previous diagnostic freezes")
        (target / "baseset").mkdir(parents=True)
        catalogue = json.loads(json.dumps(canonical if scope == "canonical" else study))
        companion = json.loads(json.dumps(water))
        if scope != "canonical":
            catalogue["bindings"]["river_relief"] = json.loads(json.dumps(bindings))
            if scope == "missing-owner": del catalogue["bindings"]["river_relief"]["9"]
            if scope == "missing-water": companion["sources"] = [row for row in companion["sources"] if row["slope"] != 9]
            if scope == "changed-source":
                for row in companion["sources"]:
                    if row["slope"] == 9: row["pixels"][row["size"][0]+32][0] ^= 1
            (target / "baseset/opentt3d-river-water.json").write_text(json.dumps(companion,separators=(",",":"))+"\n")
        (target / "baseset/opentt3d-voxels.json").write_text(json.dumps(catalogue,separators=(",",":"))+"\n")
        for path in (RESOURCES / "baseset").iterdir():
            if path.name != "opentt3d-voxels.json": (target / "baseset" / path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
        for name in ("ai","game","lang"): (target / name).symlink_to((RESOURCES / name).resolve(),target_is_directory=True)
        shutil.copy2(ROOT / "build-macos/opentt3d",target / "opentt3d")
        manifest = {"frozen_utc":datetime.now(timezone.utc).isoformat(),"scope":scope,"models":len(catalogue["models"]),
            "bound_diagnostic_relief_states":sum(len(row) for row in catalogue["bindings"].get("river_relief",{}).values()),
            "sha256":{name:digest(target / name) for name in ("opentt3d","baseset/opentt3d-voxels.json")},
            "runtime_sources":{str(path.relative_to(ROOT)):digest(path) for path in (ROOT / "src/renderer3d").iterdir() if path.is_file()},
            "canonical_model_fingerprints_preserved":True,"geometry_approvals":0,"recommended_release":"opentt3d-dev-20261003.42"}
        if scope != "canonical": manifest["sha256"]["baseset/opentt3d-river-water.json"] = digest(target / "baseset/opentt3d-river-water.json")
        (target / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        (HERE / (prefix+"-"+scope+"-frozen-manifest.json")).write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"frozen_diagnostic_scopes":len(SCOPES),"geometry_approvals":0}))


def run(prefix):
    build = ROOT / "build-macos"
    for scope in SCOPES:
        frozen = build / (prefix+"-"+scope+"-frozen-build")
        value = json.loads((frozen / "manifest.json").read_text())
        assert all(digest(frozen / name) == sha for name,sha in value["sha256"].items())
    controls = []
    plan = [(climate,271828,backend,scope,"OpenGFX2 Classic")
            for climate in CLIMATES for backend in ("vulkan","opengl") for scope in ("canonical","complete")]
    plan += [("tropic",161803,backend,scope,"OpenGFX2 Classic") for backend in ("vulkan","opengl") for scope in ("canonical","complete")]
    plan += [(climate,271828,backend,scope,"OpenGFX2 Classic") for climate in ("temperate","toyland")
             for backend in ("vulkan","opengl") for scope in ("missing-owner","missing-water","changed-source")]
    plan += [(climate,271828,backend,scope,"OpenGFX") for climate in ("temperate","toyland")
             for backend in ("vulkan","opengl") for scope in ("canonical","complete")]
    assert len(plan) == 40
    for climate,seed,backend,scope,graphics in plan:
        fixture = build / ("breadth-original-river-natural-survey-"+climate+("-seed161803" if seed == 161803 else ""))
        savegame = fixture / "save/river-survey.sav"
        frozen = build / (prefix+"-"+scope+"-frozen-build")
        output = build / f"{prefix}-{climate}-{seed}-{backend}-{scope}-{'classic' if graphics == 'OpenGFX2 Classic' else 'alternate'}"
        if output.exists(): raise ValueError("Retain previous native runs; choose a fresh prefix")
        command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(frozen),"--output",str(output),
            "--background","--backend",backend,"--graphics",graphics,"--savegame",str(savegame),"--ai-dir",str(fixture / "ai"),
            "--center","64","64","--zoom","5","--verify-world-atlas","--verify-tile-picking","--synchronous-save",
            "--blitter","40bpp-anim","--resolution","640","480","--timeout","600","--brief"]
        gallery = scope == "complete" and graphics == "OpenGFX2 Classic" and seed == 271828
        if gallery: command += ["--gallery-voxel-prefix","river_relief_study_","--gallery-voxel-overview","--verify-voxel-meshes","river_relief_study_"]
        result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1"))
        controls.append({"climate":climate,"seed":seed,"backend":backend,"scope":scope,"graphics":graphics,"gallery":gallery,
            "output":str(output.relative_to(ROOT)),"command":command,"input_save_sha256":digest(savegame),"exit_code":result.returncode})
        (HERE / (prefix+"-runs.json")).write_text(json.dumps(controls,indent=2)+"\n")
        if result.returncode: raise SystemExit(result.returncode)
        record = json.loads((output / "result.json").read_text())
        assert record["background"] and record["synchronous_original_save_verified"]
        log = (output / "run.log").read_text()
        expected = scope == "complete" and graphics == "OpenGFX2 Classic"
        assert ("diagnostic voxel river relief slope " in log) == expected
        if gallery:
            assert "20 supported river diagnostic LOD views" in log and "20 supported river LOD rebuild views" in log
            assert len(list((output / "renderer3d-reference").glob("model-voxel-river-supported-*.pam"))) == 36
    print(json.dumps({"quiet_controls":len(controls),"all_four_climate_slopes_in_saved_worlds_pending_audit":True,"geometry_approvals":0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",required=True); parser.add_argument("--phase",choices=("freeze","run"),required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"breadth-original-river-relief-world-[a-z0-9-]+",args.prefix): parser.error("Choose a fresh breadth-original-river-relief-world-* prefix")
    (freeze if args.phase == "freeze" else run)(args.prefix)


if __name__ == "__main__": main()

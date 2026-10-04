"""Quietly retain real river source components and exact tracing-on/off controls."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CANONICAL = ROOT / "build-macos/breadth-original-lock-world-support-corrected-canonical-frozen-build"
PREFIX = "breadth-original-river-ownership-components-wide"


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    build = ROOT / "build-macos"
    frozen = build / (PREFIX+"-frozen-build")
    if frozen.exists(): raise ValueError("Retain the previous native run")
    frozen.mkdir()
    for name in ("baseset","ai","game","lang"):
        (frozen / name).symlink_to((CANONICAL / name).resolve(),target_is_directory=True)
    # Reuse the immutable component-observer binary, not a concurrently rebuilt
    # developer executable or the mixed working catalogue.
    observer = build / "breadth-original-river-ownership-components-corrected-frozen-build/opentt3d"
    shutil.copy2(observer,frozen / "opentt3d")
    manifest = {"frozen_utc":datetime.now(timezone.utc).isoformat(),"binary_sha256":digest(frozen / "opentt3d"),
                "catalogue_sha256":digest(frozen / "baseset/opentt3d-voxels.json"),"runtime_bound":False,"approvals":0,
                "binary_reused_from":str(observer.relative_to(ROOT)),
                "source_sha256":{name:digest(ROOT / name) for name in (
                    "src/renderer3d/sprite_textures.cpp","src/renderer3d/sprite_textures.hpp","src/renderer3d/reference_export.cpp")}}
    assert manifest["catalogue_sha256"] == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
    (frozen / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (HERE / "components-frozen-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    controls = []
    for climate in ("temperate","arctic","tropic","toyland"):
        fixture = build / ("breadth-original-river-natural-survey-"+climate)
        savegame = fixture / "save/river-survey.sav"
        for backend in ("vulkan","opengl"):
            for traced in (True,False):
                output = build / f"{PREFIX}-{climate}-{backend}-{'on' if traced else 'off'}"
                if output.exists(): raise ValueError("Retain previous native controls")
                command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(frozen),"--output",str(output),
                    "--background","--backend",backend,"--savegame",str(savegame),"--ai-dir",str(fixture / "ai"),
                    "--center","64","64","--zoom","5","--verify-world-atlas","--verify-tile-picking","--synchronous-save","--blitter","40bpp-anim",
                    "--resolution","640","480","--timeout","600","--brief"]
                result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1" if traced else "0"))
                controls.append({"climate":climate,"backend":backend,"traced":traced,"output":str(output.relative_to(ROOT)),
                    "exit_code":result.returncode,"input_save_sha256":digest(savegame),"command":command})
                (HERE / "components-runs.json").write_text(json.dumps(controls,indent=2)+"\n")
                if result.returncode: raise SystemExit(result.returncode)
                value = json.loads((output / "result.json").read_text())
                assert value["background"] and value["synchronous_original_save_verified"]
                assert (output / "renderer3d-reference/river-selectors.json").is_file() == traced
                assert bool(list((output / "renderer3d-reference").glob("*.source.json"))) == traced
    print(json.dumps({"quiet_controls":len(controls),"approvals":0,"runtime_bound":False}))


if __name__ == "__main__": main()

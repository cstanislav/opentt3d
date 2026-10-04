"""Inspect all eight relief studies in actual saved river tiles, not only galleries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREFIX = "breadth-original-river-relief-close-observer-separated"
FROZEN = "breadth-original-river-relief-world-observer-separated"


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    records = []
    for climate in ("temperate","toyland"):
        fixture = ROOT / "build-macos" / ("breadth-original-river-natural-survey-"+climate)
        tiles = json.loads((fixture / "fixture.json").read_text())["tiles"]
        for slope in (3,6,9,12):
            tile = min((row for row in tiles if row["slope"] == slope),key=lambda row:(row["min_height_levels"],row["y"],row["x"]))
            for backend in ("vulkan","opengl"):
                for scope in ("canonical","complete"):
                    frozen = ROOT / "build-macos" / (FROZEN+"-"+scope+"-frozen-build")
                    manifest = json.loads((frozen / "manifest.json").read_text())
                    assert all(digest(frozen / name) == sha for name,sha in manifest["sha256"].items())
                    output = ROOT / "build-macos" / f"{PREFIX}-{climate}-{slope}-{backend}-{scope}"
                    if output.exists(): raise ValueError("Retain previous close worlds")
                    command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(frozen),"--output",str(output),
                        "--background","--backend",backend,"--savegame",str(fixture / "save/river-survey.sav"),"--ai-dir",str(fixture / "ai"),
                        "--center",str(tile["x"]),str(tile["y"]),"--zoom","-2","--synchronous-save","--blitter","40bpp-anim",
                        "--verify-world-atlas","--verify-tile-picking","--resolution","640","480","--timeout","600","--brief"]
                    result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1"))
                    records.append({"climate":climate,"slope":slope,"tile":tile,"backend":backend,"scope":scope,
                        "output":str(output.relative_to(ROOT)),"command":command,"exit_code":result.returncode})
                    (HERE / "close-world-runs.json").write_text(json.dumps(records,indent=2)+"\n")
                    if result.returncode: raise SystemExit(result.returncode)
                    value = json.loads((output / "result.json").read_text())
                    assert value["background"] and value["synchronous_original_save_verified"]
                    log = (output / "run.log").read_text()
                    actual = f"diagnostic voxel river relief slope {slope} climate {0 if climate == 'temperate' else 3}"
                    anchor = f"captured at {tile['x']},{tile['y']} original height {tile['min_height_levels']*8}"
                    assert (actual in log and anchor in log) == (scope == "complete")
    assert len(records) == 32
    print(json.dumps({"quiet_saved_close_worlds":32,"individual_models_presented":8,"live_relief_specific_picking_accepted":False,"approvals":0}))


if __name__ == "__main__": main()

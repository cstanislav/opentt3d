"""Compare both observer implementations and tracing at explicit original non-HiDPI pixels."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREFIX = "breadth-original-river-relief-fixed-pixel-preservation"


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    manifest_path = HERE / "fixed-pixel-preservation-runs.json"
    if manifest_path.exists(): raise ValueError("Retain previous fixed-pixel controls")
    rows = []
    for climate in ("temperate","arctic","tropic","toyland"):
        fixture = ROOT / "build-macos" / ("breadth-original-river-natural-survey-"+climate)
        for backend in ("vulkan","opengl"):
            for revision,scope,traced in (("complete-water","canonical",True),("complete-water","complete",True),
                ("observer-separated","canonical",True),("observer-separated","complete",True),("observer-separated","complete",False)):
                frozen = ROOT / "build-macos" / f"breadth-original-river-relief-world-{revision}-{scope}-frozen-build"
                manifest = json.loads((frozen / "manifest.json").read_text())
                assert all(digest(frozen / name) == sha for name,sha in manifest["sha256"].items())
                output = ROOT / "build-macos" / f"{PREFIX}-{climate}-{backend}-{revision}-{scope}-{'on' if traced else 'off'}"
                if output.exists(): raise ValueError("Retain previous controls")
                command = [sys.executable,"tools/opentt3d/smoke.py","--build-dir",str(frozen),"--output",str(output),
                    "--background","--no-hidpi","--backend",backend,"--savegame",str(fixture / "save/river-survey.sav"),
                    "--ai-dir",str(fixture / "ai"),"--center","64","64","--zoom","5","--synchronous-save", "--blitter","40bpp-anim",
                    "--verify-world-atlas","--verify-tile-picking","--resolution","640","480","--timeout","600","--brief"]
                result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1" if traced else "0"))
                rows.append({"climate":climate,"backend":backend,"scope":scope,"revision":revision,"traced":traced,
                    "output":str(output.relative_to(ROOT)),"command":command,"frozen_manifest":str((frozen / "manifest.json").relative_to(ROOT)),
                    "input_save_sha256":digest(fixture / "save/river-survey.sav"),"exit_code":result.returncode})
                manifest_path.write_text(json.dumps(rows,indent=2)+"\n")
                if result.returncode: raise SystemExit(result.returncode)
                record = json.loads((output / "result.json").read_text())
                assert record["image_size"] == [640,480] and record["original_allow_hidpi"] is False
                assert record["background"] and record["synchronous_original_save_verified"]
                assert (output / "renderer3d-reference/river-selectors.json").exists() == traced
                assert ("diagnostic voxel river relief slope " in (output / "run.log").read_text()) == (scope == "complete")
    assert len(rows) == 40
    print(json.dumps({"quiet_fixed_pixel_controls":40,"runtime_tracing_on_off_pairs":8,"observer_revision_scope_pairs":16,
        "full_size_comparisons_pending_audit":True,"quality_approvals":0}))


if __name__ == "__main__": main()

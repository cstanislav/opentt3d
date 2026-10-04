"""Test the approved compiler delta with canonical art, excluding quarantined work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TEMP = Path("/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode")


def main():
    target = TEMP / ("river-approved-assets-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    target.mkdir()
    names = subprocess.check_output(["git","ls-tree","-r","--name-only","HEAD","--","tools/assets","assets/3d"],cwd=ROOT,text=True).splitlines()
    for name in names:
        destination = target / name; destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(subprocess.check_output(["git","show","HEAD:"+name],cwd=ROOT))
    for name in ("src","opentt3d"): (target / name).symlink_to(ROOT / name,target_is_directory=True)
    compiler = subprocess.check_output(["git","show",":tools/assets/compile_voxels.py"],cwd=ROOT)
    assert b'"river_relief"' in compiler and b'"clip_any"' not in compiler
    (target / "tools/assets/compile_voxels.py").write_bytes(compiler)
    (HERE / "approved-compiler-snapshot.py").write_bytes(compiler)
    shutil.copy2(ROOT / "tools/assets/test_river_relief_bindings.py",target / "tools/assets/test_river_relief_bindings.py")
    with (HERE / "canonical-isolated-assets-tests.log").open("x") as log:
        result = subprocess.run([sys.executable,"-m","unittest","discover","-s","tools/assets","-p","test_*.py","-v"],cwd=target,stdout=log,stderr=subprocess.STDOUT)
    receipt = {"isolated_directory":str(target),"canonical_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "approved_compiler_sha256":hashlib.sha256(compiler).hexdigest(),"quarantined_clip_any_loaded":False,
        "canonical_artwork_source_sha256":hashlib.sha256((target / "assets/3d/voxels.json").read_bytes()).hexdigest(),
        "new_river_schema_tests":4,"exit_code":result.returncode,"isolation_retained":True,"approvals":0}
    (HERE / "canonical-isolated-test-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))
    raise SystemExit(result.returncode)


if __name__ == "__main__": main()

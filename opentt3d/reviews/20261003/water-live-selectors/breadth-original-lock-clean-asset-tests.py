"""Test live-source tooling against committed artwork/compiler, without HQ prototypes."""
from pathlib import Path
import datetime, hashlib, io, json, shutil, subprocess, tarfile

root = Path.cwd()
out = root / "build-macos/breadth-original-lock-clean-asset-test-tree"
assert not out.exists()
out.mkdir()
commit = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
archive = subprocess.check_output(["git","archive",commit,"assets/3d","tools/assets","src","opentt3d/upstream.json"])
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    source.extractall(out,filter="data")
files = ("tools/assets/live_water.py","tools/assets/test_live_water.py")
for name in files:
    shutil.copy2(root / name,out / name)
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
assert digest(out / "assets/3d/voxels.json") == hashlib.sha256(subprocess.check_output(["git","show",f"{commit}:assets/3d/voxels.json"])).hexdigest()
assert not (out / "tools/assets/test_hq_complete_voxels.py").exists()
log = root / "build-macos/breadth-original-lock-clean-asset-tests.log"
with log.open("x") as output:
    result = subprocess.run(["python3","-m","unittest","discover","-s","tools/assets"],cwd=out,stdout=output,stderr=subprocess.STDOUT)
assert result.returncode == 0 and "Ran 227 tests" in log.read_text() and "\nOK\n" in log.read_text()
receipt = root / "build-macos/breadth-original-lock-clean-asset-test-receipt.json"
assert not receipt.exists()
receipt.write_text(json.dumps({"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"commit":commit,
    "asset_tests":227,"experimental_hq_compiler_artwork_tests_present":False,
    "overlaid_read_only_tools":{name:digest(root / name) for name in files},"test_log_sha256":digest(log),
    "scope":"Committed1831-model source/compiler plus live-source validation only; no experimental larger HQ/compiler/tests and no native build or geometry approval."},indent=2)+"\n")
print(json.dumps({"clean_assets_passed":227,"new_live_tests":8}))

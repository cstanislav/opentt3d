"""Check full water quality scope in an isolated committed-artwork/compiler tree."""
from pathlib import Path
import hashlib, io, json, shutil, subprocess, tarfile

root = Path.cwd()
out = root / "build-macos/breadth-original-water-quality-clean-test-tree"
assert not out.exists()
out.mkdir()
commit = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git","archive",commit,"assets/3d","tools/assets","src","opentt3d/upstream.json"]))) as source:
    source.extractall(out,filter="data")
files = ("tools/assets/quality_audit.py","tools/assets/test_quality_audit.py")
for name in files:
    shutil.copy2(root / name,out / name)
assert not (out / "tools/assets/test_hq_complete_voxels.py").exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
assert digest(out / "assets/3d/voxels.json") == hashlib.sha256(subprocess.check_output(["git","show",f"{commit}:assets/3d/voxels.json"])).hexdigest()
log = root / "build-macos/breadth-original-water-quality-clean-asset-tests.log"
with log.open("x") as output:
    result = subprocess.run(["python3","-m","unittest","discover","-s","tools/assets"],cwd=out,stdout=output,stderr=subprocess.STDOUT)
assert result.returncode == 0 and "Ran 231 tests" in log.read_text() and "\nOK\n" in log.read_text()
receipt = root / "build-macos/breadth-original-water-quality-clean-test-receipt.json"
assert not receipt.exists()
receipt.write_text(json.dumps({"commit":commit,"asset_tests":231,"experimental_hq_compiler_artwork_tests_present":False,
    "overlaid_read_only_tools":{name:digest(root / name) for name in files},"test_log_sha256":digest(log),
    "scope":"Committed1831-model artwork/compiler and canonical reviews plus the full read-only water quality scope, not a new model build or geometry approval."},indent=2)+"\n")
print(json.dumps({"clean_assets_passed":231,"new_quality_tests":4}))

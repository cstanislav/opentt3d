"""Isolate the additive river-ground quality scope from experimental artwork/compiler."""
from pathlib import Path
import hashlib, io, json, shutil, subprocess, tarfile

root = Path.cwd()
out = root / "build-macos/breadth-original-river-ground-quality-clean-test-tree"
assert not out.exists()
out.mkdir()
commit = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git","archive",commit,"assets/3d","tools/assets","src","opentt3d/upstream.json"]))) as source:
    source.extractall(out,filter="data")
files = ("tools/assets/live_water.py","tools/assets/test_live_river.py","tools/assets/original_water.py",
         "tools/assets/test_original_water.py","tools/assets/inventory.py","tools/assets/quality_audit.py","tools/assets/test_quality_audit.py")
for name in files:
    shutil.copy2(root / name,out / name)
assert not (out / "tools/assets/test_hq_complete_voxels.py").exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
for name in ("assets/3d/voxels.json","tools/assets/compile_voxels.py","assets/3d/quality_reviews.json"):
    assert digest(out / name) == hashlib.sha256(subprocess.check_output(["git","show",f"{commit}:{name}"])).hexdigest()
log = root / "build-macos/breadth-original-river-ground-quality-clean-tests.log"
with log.open("x") as output:
    result = subprocess.run(["python3","-m","unittest","discover","-s","tools/assets"],cwd=out,stdout=output,stderr=subprocess.STDOUT)
assert result.returncode == 0 and "Ran 241 tests" in log.read_text() and "\nOK\n" in log.read_text()
receipt = root / "build-macos/breadth-original-river-ground-quality-clean-test-receipt.json"
assert not receipt.exists()
receipt.write_text(json.dumps({"commit":commit,"asset_tests":241,"experimental_hq_compiler_artwork_tests_present":False,
    "overlaid_read_only_tools":{name:digest(root / name) for name in files},"test_log_sha256":digest(log),
    "scope":"Committed1831-model artwork/compiler/reviews with the read-only river source validator and five-selector ground-scope extension; no experimental renderer/artwork or runtime approval."},indent=2)+"\n")
print(json.dumps({"clean_assets_passed":241,"new_read_only_tests_since_prior_scope":10}))

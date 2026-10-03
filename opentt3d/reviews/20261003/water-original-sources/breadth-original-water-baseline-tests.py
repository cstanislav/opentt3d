"""Test the new read-only water inventory without any experimental HQ compiler/artwork."""
from pathlib import Path
import hashlib, io, json, shutil, subprocess, tarfile

root = Path.cwd()
out = root / "build-macos/breadth-original-water-baseline-test-tree"
assert not out.exists()
out.mkdir()
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
archive = subprocess.check_output(["git", "archive", commit, "assets/3d", "tools/assets", "src", "opentt3d/upstream.json"])
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    source.extractall(out, filter="data")
files = ("tools/assets/inventory.py", "tools/assets/original_water.py", "tools/assets/test_original_water.py")
for name in files:
    shutil.copy2(root / name, out / name)
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
assert digest(out / "assets/3d/voxels.json") == hashlib.sha256(subprocess.check_output(["git", "show", f"{commit}:assets/3d/voxels.json"])).hexdigest()
assert not (out / "tools/assets/test_hq_complete_voxels.py").exists()
log = root / "build-macos/breadth-original-water-committed-artwork-asset-tests.log"
with log.open("x") as output:
    result = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tools/assets"], cwd=out, stdout=output, stderr=subprocess.STDOUT)
assert result.returncode == 0
text = log.read_text()
assert "Ran 219 tests" in text and "\nOK\n" in text
receipt = root / "build-macos/breadth-original-water-baseline-test-receipt.json"
assert not receipt.exists()
receipt.write_text(json.dumps({"commit": commit, "asset_tests": 219, "experimental_hq_compiler_artwork_tests_present": False,
    "overlaid_read_only_tools": {name: digest(root / name) for name in files}, "test_log_sha256": digest(log),
    "scope": "Committed1831-model sources/compiler plus the three new read-only water inventory/test tools only. No native binary is built from this test tree and no prototype is approved."}, indent=2) + "\n")
print(json.dumps({"baseline_assets": 204, "new_water_tests": 15, "passed": 219}))

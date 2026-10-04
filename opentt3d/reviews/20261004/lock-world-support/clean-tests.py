"""Validate only committed artwork plus lock schema; exclude experimental HQ changes."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
target = ROOT / "build-macos/breadth-original-lock-world-support-clean-test-tree"
assert not target.exists()
target.mkdir()
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
archive = subprocess.check_output(["git", "archive", commit, "assets/3d", "tools/assets", "src", "opentt3d/upstream.json"], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    source.extractall(target, filter="data")
compiler_path = target / "tools/assets/compile_voxels.py"
original = compiler_path.read_text()
old_categories = '"effects", "objects", "object_ground") or not isinstance(identifiers, dict):'
new_categories = '"effects", "objects", "object_ground", "lock_walls") or not isinstance(identifiers, dict):'
assert original.count(old_categories) == 1
schema = '            if category in ("airport_tiles", "airport_ground")'
assert original.count(schema) == 1
compiler = original.replace(old_categories, new_categories).replace(schema,
    '            if category == "lock_walls" and (int(identifier) >= 48 or any(int(state) >= 4 for state in states)):\n'
    '                raise ValueError("Lock walls use all48 original source-owner ordinals and explicit climate states0..3")\n' + schema)
compiler_path.write_text(compiler)
shutil.copy2(compiler_path, HERE / "canonical-compiler.py")
overlay = ("tools/assets/test_lock_bindings.py", "src/renderer3d/lock_geometry.hpp", "src/renderer3d/voxel_mesh_cache.hpp",
           "src/renderer3d/voxel_models.cpp", "src/renderer3d/voxel_models.h", "src/renderer3d/world_capture.cpp",
           "src/renderer3d/world_capture.h", "src/renderer3d/renderer3d_voxels.cpp", "src/water_cmd.cpp")
for name in overlay:
    shutil.copy2(ROOT / name, target / name)
assert not (target / "tools/assets/test_hq_complete_voxels.py").exists()
assert '"clip_any"' not in compiler
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
assert digest(target / "assets/3d/voxels.json") == hashlib.sha256(subprocess.check_output(["git", "show", f"{commit}:assets/3d/voxels.json"], cwd=ROOT)).hexdigest()
log = HERE / "all-assets-isolated-tests.log"
with log.open("x") as destination:
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tools/assets", "-v"], cwd=target,
                            stdout=destination, stderr=subprocess.STDOUT)
assert result.returncode == 0 and "\nOK\n" in log.read_text()
count = int(re.search(r"Ran (\d+) tests", log.read_text())[1])
receipt = {"audited_utc": datetime.now(timezone.utc).isoformat(), "base_commit": commit, "asset_tests": count,
           "canonical_artwork_sha256": digest(target / "assets/3d/voxels.json"), "compiler_sha256": digest(compiler_path),
           "overlay_sha256": {name: digest(ROOT / name) for name in overlay}, "test_log_sha256": digest(log),
           "quarantined_hq_artwork_compiler_tests_present": False, "geometry_approvals": 0,
           "scope": "Exact committed artwork with only the new lock binding schema and renderer/support source. No larger-HQ artwork, union ownership compiler or unreviewed HQ tests are included."}
(HERE / "isolated-test-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))

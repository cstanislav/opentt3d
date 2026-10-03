"""Freeze the compiled optional observer with the unchanged released1831-model payload."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess

root = Path("build-macos").resolve()
app = root / "playable-release42-independent-extracted/OpenTT3D.app"
resources = app / "Contents/Resources"
out = root / "breadth-original-water-observer1831-frozen-build"
assert not out.exists()
out.mkdir()
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
binary = root / "opentt3d"
assert b"OPENTT3D_EXPORT_WATER_SOURCES" in binary.read_bytes(), "Actual CMake target must compile the observer first"
shutil.copy2(binary, out / "opentt3d")
for name in ("baseset", "lang", "ai", "game"):
    (out / name).symlink_to(resources / name, target_is_directory=True)
source_names = subprocess.check_output(["git", "diff", "--name-only", "1247c88d5e180ac6fbd88bdf9b71bfafd468f7a5", "--", "src"], text=True).splitlines()
assert set(source_names) == {"src/renderer3d/sprite_textures.hpp", "src/renderer3d/reference_export.cpp", "src/renderer3d/world_capture.cpp"}
inputs = {}
for name in source_names + ["tools/opentt3d/fixture_locks.py", "tools/opentt3d/fixtures/locks/main.nut", "tools/opentt3d/fixtures/locks/info.nut", "tools/assets/original_water.py"]:
    target = out / "source-snapshot" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(name, target)
    inputs[name] = digest(target)
catalogue = resources / "baseset/opentt3d-voxels.json"
assert digest(catalogue) == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
assert len(json.loads(catalogue.read_text())["models"]) == 1831
manifest = {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "binary_sha256": digest(out / "opentt3d"),
    "loaded_catalogue_sha256": digest(catalogue), "loaded_models": 1831, "original_cpp_baseline_commit": "1247c88d5e180ac6fbd88bdf9b71bfafd468f7a5",
    "cpp_deltas": source_names, "source_sha256": inputs, "resources_read_only_reference": str(resources), "exact_tag_binary": False,
    "scope": "Newly compiled local mixed-working-source diagnostic binary; only three optional read-only observer C++ deltas from .42. It is not the exact-tag package and has no release approval. Loads the immutable independently downloaded1831-model payload rather than dirty1915-model experimental artwork/compiler data. Rendering selectors, commands, simulation/RNG, maps and geometry stay unchanged; env-gated observation records actual callbacks."}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"frozen_build": str(out), "binary_sha256": manifest["binary_sha256"], "models": 1831, "exact_tag_binary": False}))

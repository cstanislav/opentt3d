"""Review 48 unbound stone/foam studies against unchanged released runtime artwork."""
import argparse
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
sys.path.insert(0, str(ROOT / "tools/assets"))
from compile_voxels import compile_catalogue
from quality_audit import fingerprint


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="breadth-original-lock-bond-foam-study")
    parser.add_argument("--art-python", type=Path, required=True)
    args = parser.parse_args()
    if not args.prefix.startswith("breadth-original-lock-") or not all(c.isalnum() or c == "-" for c in args.prefix):
        parser.error("Use a fresh breadth-original-lock-* prefix")
    build = ROOT / "build-macos"
    freeze = build / (args.prefix + "-frozen-build")
    if freeze.exists():
        parser.error("Retain the existing diagnostic and use a fresh prefix")
    with (build / (args.prefix + "-structural-tests.log")).open("x") as log:
        subprocess.run([sys.executable, str(HERE / "test_authored_study.py"), "-v"], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    source = json.loads((HERE / "authored-source.json").read_text())
    study = compile_catalogue(source)
    assert len(study["models"]) == 48 and study["bindings"] == {}
    resources = build / "playable-release42-independent-extracted/OpenTT3D.app/Contents/Resources"
    original_path = resources / "baseset/opentt3d-voxels.json"
    original = json.loads(original_path.read_text())
    merged = json.loads(original_path.read_text())
    assert len(original["models"]) == 1831 and not (original["models"].keys() & study["models"].keys())
    offset = len(merged["materials"])
    merged["materials"].extend(study["materials"])
    for name, model in study["models"].items():
        merged["models"][name] = {**model, "runs": [run[:4] + [run[4]+offset] for run in model["runs"]]}
    assert original["bindings"] == merged["bindings"]
    assert all(fingerprint(model,original["materials"]) == fingerprint(merged["models"][name],merged["materials"])
               for name,model in original["models"].items())
    (freeze / "baseset").mkdir(parents=True)
    (freeze / "baseset/opentt3d-voxels.json").write_text(json.dumps(merged,separators=(",", ":")) + "\n")
    for path in (resources / "baseset").iterdir():
        if path.name != "opentt3d-voxels.json":
            (freeze / "baseset" / path.name).symlink_to(path,target_is_directory=path.is_dir())
    for name in ("ai", "game", "lang"):
        (freeze / name).symlink_to(resources / name,target_is_directory=True)
    shutil.copy2(build / "opentt3d",freeze / "opentt3d")
    for name in ("authored-source.json", "test_authored_study.py"):
        shutil.copy2(HERE / name,freeze / name)
    shutil.copy2(ROOT / "tools/assets/compile_voxels.py",freeze / "compiler-snapshot.py")
    identities = {name: digest(freeze / name) for name in ("opentt3d", "baseset/opentt3d-voxels.json",
                                                         "authored-source.json", "test_authored_study.py", "compiler-snapshot.py")}
    runtime_sources = {str(path.relative_to(ROOT)): digest(path) for path in sorted((ROOT / "src/renderer3d").rglob("*")) if path.is_file()}
    runtime_sources["src/water_cmd.cpp"] = digest(ROOT / "src/water_cmd.cpp")
    manifest = {"frozen_utc": datetime.now(timezone.utc).isoformat(), "models": 1879, "unbound_lock_studies": 48,
                "released_catalogue_sha256": digest(original_path), "sha256": identities, "runtime_source_sha256": runtime_sources,
                "study_fingerprints": {name: fingerprint(model,study["materials"]) for name,model in study["models"].items()},
                "prior_1831_models_and_bindings_exact": True, "exact_tag_binary": False, "runtime_bound": False, "approvals": 0,
                "scope": "Explicit authored face bonds/coping joints and shaded open lanterns; only lower-sea foam changes occupied cells. Nonfoam volume, origins, openings and object heights remain exact. Front foam follows its own outer waterline/lamp-end return; NE/NW rear foam is end-only and SW/SE rear foam is absent. These provisional source studies do not establish runtime geometry, terrain support, phases/custom completeness, ships or 8/10."}
    (freeze / "manifest.json").write_text(json.dumps(manifest,indent=2) + "\n")
    runs = []
    fixture = build / "breadth-original-lock-temperate-natural-resources-fixture"
    for backend in ("vulkan", "opengl"):
        output = build / f"{args.prefix}-{backend}"
        command = [sys.executable, "tools/opentt3d/smoke.py", "--build-dir", str(freeze), "--output", str(output),
                   "--background", "--backend", backend, "--savegame", str(fixture / "save/lock-fixture.sav"),
                   "--ai-dir", str(fixture / "ai"), "--center", "101", "4", "--gallery-voxel-prefix", "lock_study_",
                   "--gallery-voxel-overview", "--verify-voxel-meshes", "lock_study_", "--verify-world-atlas", "--verify-tile-picking",
                   "--synchronous-save", "--resolution", "640", "480", "--timeout", "600", "--brief"]
        result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
        runs.append({"output": str(output), "backend": backend, "exit_code": result.returncode, "command": command,
                     "catalogue_sha256": identities["baseset/opentt3d-voxels.json"], "binary_sha256": identities["opentt3d"]})
        run_manifest = build / (args.prefix + "-runs.json")
        run_manifest.write_text(json.dumps(runs,indent=2) + "\n")
        if result.returncode:
            raise SystemExit(result.returncode)
        assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
        assert len(list((output / "renderer3d-reference").glob("model-voxel-lock_study_*.pam"))) == 48*9
    reports = []
    for label, left, right, pattern in (
        ("paired-gallery", build / f"{args.prefix}-vulkan/renderer3d-reference", build / f"{args.prefix}-opengl/renderer3d-reference", "model-voxel-lock_study_*"),
        ("native-gallery", build / f"{args.prefix}-vulkan/renderer3d-reference", build / f"{args.prefix}-opengl/renderer3d-reference", "model-voxel-lock_study_*-native"),
        *((backend + "-prior-world", build / f"breadth-original-lock-front-profile-{backend}/screenshot/smoke.png",
           build / f"{args.prefix}-{backend}/screenshot/smoke.png", "*") for backend in ("vulkan", "opengl"))):
        report_path = build / (args.prefix + "-" + label + "-strict.json")
        with (build / (args.prefix + "-" + label + "-strict.log")).open("x") as log:
            result = subprocess.run([str(args.art_python), "tools/assets/compare_galleries.py", str(left), str(right), "--pattern", pattern,
                                     "--output", str(report_path), "--pixel-details", "8"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode in (0,1) and report_path.is_file()
        report = json.loads(report_path.read_text())
        reports.append({"label": label, "exit_code": result.returncode, "images": report["images"],
                        "different_images": len(report["differences"]), "different_pixels": sum(row.get("changed_pixels",0) for row in report["differences"]),
                        "report": str(report_path)})
    with (build / (args.prefix + "-compaction.log")).open("x") as log:
        subprocess.run([str(args.art_python), "tools/assets/compact_reviews.py", str(build), "--apply", "--validation-manifest", str(run_manifest)],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    sheet_script = ROOT / "opentt3d/reviews/20261003/water-front-and-river-study/breadth-original-lock-authored-study-sheets.py"
    subprocess.run([str(args.art_python), str(sheet_script), "--prefix", args.prefix], cwd=ROOT, check=True)
    assert all(digest(freeze / name) == expected for name,expected in identities.items())
    summary = {"reviewed_utc": datetime.now(timezone.utc).isoformat(), "models": 1879, "unbound_owners": 48, "native_controls": len(runs),
               "comparisons": reports, "runtime_bound": False, "approvals": 0, "scope": manifest["scope"]}
    (build / (args.prefix + "-verification.json")).write_text(json.dumps(summary,indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

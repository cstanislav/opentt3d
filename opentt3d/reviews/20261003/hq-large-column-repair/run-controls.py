"""Freeze/review a source-owned HQ corner repair; never publish candidate artwork.

Run from the project root. A fresh --prefix is required to retain every prior run.
The original public-command saves contain size0 HQs, not forced larger stages.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/assets"))
from quality_audit import fingerprint


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="breadth-original-hq-large-column-corrected")
    parser.add_argument("--art-python", type=Path, required=True)
    args = parser.parse_args()
    if not args.prefix.startswith("breadth-original-hq-") or not all(c.isalnum() or c == "-" for c in args.prefix):
        parser.error("Use a fresh breadth-original-hq-* diagnostic prefix")
    build = ROOT / "build-macos"
    freeze = build / (args.prefix + "-frozen-build")
    if freeze.exists():
        parser.error("The diagnostic freeze already exists; retain it and use a new prefix")
    (freeze / "baseset").mkdir(parents=True)
    paths = ["assets/3d/voxels.json", "tools/assets/compile_voxels.py", "tools/assets/test_hq_complete_voxels.py"]
    paths += [str(path.relative_to(ROOT)) for path in sorted((ROOT / "src/renderer3d").rglob("*")) if path.is_file()]
    paths += ["src/water_cmd.cpp", "src/table/object_land.h", "src/object_cmd.cpp"]
    identities = {}
    for name in paths:
        source, target = ROOT / name, freeze / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        identities[name] = digest(target)
    shutil.copy2(build / "opentt3d", freeze / "opentt3d")
    for name in ("ai", "game", "lang"):
        (freeze / name).symlink_to(build / name, target_is_directory=True)
    for path in (build / "baseset").iterdir():
        if path.name != "opentt3d-voxels.json":
            (freeze / "baseset" / path.name).symlink_to(path, target_is_directory=path.is_dir())
    with (build / (args.prefix + "-compile.log")).open("x") as log:
        subprocess.run([sys.executable, str(freeze / "tools/assets/compile_voxels.py"),
                        str(freeze / "assets/3d/voxels.json"), "--output", str(freeze / "baseset/opentt3d-voxels.json")],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    current = json.loads((freeze / "baseset/opentt3d-voxels.json").read_text())
    prior_path = build / "breadth-original-hq-medium-perimeter-owner-catalogue.json"
    prior = json.loads(prior_path.read_text())
    expected = {f"hq_body_large_{climate}_{part}" for climate in ("temperate", "arctic", "tropic") for part in ("north", "east")}
    changed = {name for name, model in prior["models"].items()
               if fingerprint(model, prior["materials"]) != fingerprint(current["models"][name], current["materials"])}
    assert len(current["models"]) == len(prior["models"]) == 1915 and changed == expected
    assert current["bindings"] == prior["bindings"]
    colours = lambda models, materials: {(x+i, y, z): tuple(materials[material-1])
                                        for model in models for x, y, z, length, material in model["runs"] for i in range(length)}
    for climate in ("temperate", "arctic", "tropic"):
        names = [f"hq_{role}_large_{climate}_{part}" for role, parts in (("ground", ("north", "west", "east", "south")),
                                                                    ("body", ("north", "west", "east"))) for part in parts]
        assert colours([prior["models"][name] for name in names], prior["materials"]) == \
               colours([current["models"][name] for name in names], current["materials"])
    source = json.loads((freeze / "assets/3d/voxels.json").read_text())
    baseline_source = json.loads((ROOT / "opentt3d/reviews/20261003/hq-larger-rejected/prototype-source.json").read_text())
    assert source["materials"] == baseline_source["materials"] and source["bindings"] == baseline_source["bindings"]
    assert all(source["components"][name] == value for name, value in baseline_source["components"].items())
    assert {name for name, value in baseline_source["models"].items() if source["models"][name] != value} == {
        "hq_body_large_temperate_north", "hq_body_large_temperate_east"}
    identities.update({"opentt3d": digest(freeze / "opentt3d"),
                       "baseset/opentt3d-voxels.json": digest(freeze / "baseset/opentt3d-voxels.json")})
    manifest = {"frozen_utc": datetime.now(timezone.utc).isoformat(), "models": 1915, "prior_models_exact": 1909,
                "changed_models": sorted(changed), "prior_catalogue_sha256": digest(prior_path), "sha256": identities,
                "exact_tag_binary": False, "approved": False,
                "scope": "Six candidate body owners change only cell ownership. Every physical joined cell/six-face colour, size/origin, all other models and all bindings stay exact. Canonical1831-model artwork and recommended.42 are unchanged. This is not source fidelity, natural larger-stage/world/state/renderer or quality approval."}
    (freeze / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    runs = []
    for climate in ("temperate", "arctic", "tropic", "toyland"):
        fixture = build / f"breadth-original-object-command-{climate}-owned-land-fixture"
        site = json.loads((fixture / "fixture.json").read_text())
        for backend in ("vulkan", "opengl"):
            output = build / f"{args.prefix}-{climate}-{backend}"
            command = [sys.executable, "tools/opentt3d/smoke.py", "--build-dir", str(freeze), "--output", str(output),
                       "--background", "--backend", backend, "--savegame", str(fixture / "save/object-fixture.sav"),
                       "--ai-dir", str(fixture / "ai"), "--reference-object", "4", "--reference-object-tile", str(site["hq_x"]), str(site["hq_y"]),
                       "--gallery-voxel-overview", "--gallery-voxel-prefix", "hq_", "--export-objects", "--verify-voxel-meshes", "hq_",
                       "--verify-world-atlas", "--verify-tile-picking", "--synchronous-save", "--zoom", "0", "--resolution", "640", "480",
                       "--timeout", "420", "--brief"]
            result = subprocess.run(command, cwd=ROOT)
            runs.append({"output": str(output), "climate": climate, "backend": backend, "exit_code": result.returncode,
                         "command": command, "binary_sha256": identities["opentt3d"], "catalogue_sha256": identities["baseset/opentt3d-voxels.json"]})
            run_manifest = build / (args.prefix + "-runs.json")
            run_manifest.write_text(json.dumps(runs, indent=2) + "\n")
            if result.returncode:
                raise SystemExit(result.returncode)
            text = (output / "run.log").read_text()
            for check in ("145 independent HQ owner LOD views preserve exact occupied/air boundaries",
                          "320 original HQ ground views preserve", "60 joined original HQ views preserve"):
                assert check in text
            assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
            with (build / (args.prefix + "-compaction.log")).open("a") as log:
                subprocess.run([str(args.art_python), "tools/assets/compact_reviews.py", str(build), "--apply",
                                "--validation-manifest", str(run_manifest)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        references = build / f"{args.prefix}-{climate}-vulkan/renderer3d-reference"
        subprocess.run([str(args.art_python), "tools/assets/object_review.py", str(references), str(references),
                        "--output", str(build / (args.prefix + "-studies") / climate), "--owners"], cwd=ROOT, check=True)
    assert all(digest(freeze / name) == identity for name, identity in identities.items())
    print(json.dumps({"native_controls": len(runs), "models": 1915, "prior_models_exact": 1909,
                      "changed_models": sorted(changed), "checks": dict(Counter(row["exit_code"] for row in runs)), "approvals": 0}))


if __name__ == "__main__":
    main()

"""Retain complete worlds, sources, failures and diagnostic catalogues portably."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from quality_audit import audit, fingerprint, write_ratings_csv


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert digest(source) == digest(destination), destination
    else:
        shutil.copy2(source, destination)
    return destination


def compress(source, destination):
    assert not destination.exists()
    with source.open("rb") as content, destination.open("xb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            shutil.copyfileobj(content, compressed)
    with gzip.open(destination, "rb") as restored:
        assert hashlib.file_digest(restored, "sha256").hexdigest() == digest(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    build = ROOT / "build-macos"
    sources = []
    images = []
    cohorts = (("initial", "breadth-original-lock-world-support", "pilot"),
               ("corrected-pilot", args.prefix, "pilot"), ("matrix", args.prefix, "matrix"))
    runs = {}
    for label, prefix, phase in cohorts:
        manifest = build / f"{prefix}-{phase}-runs.json"
        rows = json.loads(manifest.read_text())
        assert len(rows) == {"initial": 5, "corrected-pilot": 12, "matrix": 64}[label]
        assert all(row["exit_code"] == 0 for row in rows)
        copy(manifest, HERE / f"{label}-runs.json")
        if label != "initial":
            copy(build / f"{prefix}-{phase}-verification.json", HERE / f"{label}-native-verification.json")
        runs[label] = rows
        for row in rows:
            original = Path(row["output"])
            target = HERE / "native-controls" / label / row["scope"] / row["climate"] / f"{row['elevation']}-{row['direction']}" / row["backend"]
            for name in ("run.log", "result.json", "openttd.cfg", "scripts/game_start.scr", "screenshot/smoke.png", "renderer3d-reference/water-live.json"):
                copy(original / name, target / name)
            for image in sorted((original / "renderer3d-reference").glob("*.pam")):
                portable = copy(image, target / "renderer3d-reference" / image.name)
                sources.append({"original": str(image.relative_to(ROOT)), "portable_image": str(portable.relative_to(ROOT)), "sha256": digest(portable)})
            screenshot = target / "screenshot/smoke.png"
            images.append({"phase": label, "scope": row["scope"], "climate": row["climate"], "elevation": row["elevation"], "direction": row["direction"],
                           "backend": row["backend"], "image": str(screenshot.relative_to(ROOT)), "sha256": digest(screenshot)})
    (HERE / "source-file-map.json").write_text(json.dumps(sources, indent=2) + "\n")
    (HERE / "full-world-images.json").write_text(json.dumps(images, indent=2) + "\n")
    manifest = json.loads((build / f"{args.prefix}-complete-frozen-build/manifest.json").read_text())
    for name, expected in manifest["runtime_sources"].items():
        assert digest(ROOT / name) == expected, name
    changed = ("src/renderer3d/lock_geometry.hpp", "src/renderer3d/voxel_mesh_cache.hpp", "src/renderer3d/voxel_models.cpp",
               "src/renderer3d/voxel_models.h", "src/renderer3d/world_capture.cpp", "src/renderer3d/world_capture.h",
               "src/renderer3d/renderer3d_voxels.cpp", "src/water_cmd.cpp", "tools/assets/test_lock_bindings.py")
    for name in changed:
        copy(ROOT / name, HERE / "final-source" / name)
    for scope in ("canonical", "complete", "missing-owner"):
        freeze = build / f"{args.prefix}-{scope}-frozen-build"
        frozen = json.loads((freeze / "manifest.json").read_text())
        assert all(digest(freeze / name) == expected for name, expected in frozen["sha256"].items())
        copy(freeze / "manifest.json", HERE / f"{scope}-frozen-manifest.json")
        compress(freeze / "baseset/opentt3d-voxels.json", HERE / f"{scope}-diagnostic-catalogue.json.gz")
    initial = build / "breadth-original-lock-world-support-complete-frozen-build"
    copy(initial / "manifest.json", HERE / "initial-frozen-manifest.json")
    copy(initial / "authored-source.json", HERE / "authored-source.json")
    sheets = HERE / "world-sheets"
    sheets.mkdir()
    for climate in ("temperate", "arctic", "tropic", "toyland"):
        sheet = Image.new("RGB", (1280, 2080), (38, 39, 47))
        draw = ImageDraw.Draw(sheet)
        for elevation in range(2):
            for direction in range(4):
                row = next(row for row in images if row["phase"] == "matrix" and row["climate"] == climate and row["elevation"] == elevation and row["direction"] == direction and row["backend"] == "vulkan")
                position = elevation*4 + direction
                left, top = (position%2)*640, (position//2)*520
                draw.text((left+8, top+8), f"{climate} {'NE SE SW NW'.split()[direction]} elevation{elevation} — 3D world study;6/10, not shipped", fill="white")
                with Image.open(ROOT / row["image"]) as source:
                    sheet.paste(source.convert("RGB").resize((640, 480), Image.Resampling.NEAREST), (left, top+32))
        sheet.save(sheets / f"{climate}.png")
    # The complete catalogue-wide goal and its existing ratings stay separate
    # from the temporary48-owner binding. No gap or source instance is promoted.
    prior = ROOT / "opentt3d/reviews/20261003/water-bond-foam-study"
    foam = ROOT / "opentt3d/reviews/20261003/water-foam-palette-study"
    with gzip.open(foam / "separate-rejected-hq-lock-catalogue.json.gz", "rt") as source:
        mixed = json.load(source)
    with gzip.open(HERE / "canonical-diagnostic-catalogue.json.gz", "rt") as source:
        canonical = json.load(source)
    hq = json.loads(json.dumps(mixed))
    hq["models"] = {name: model for name, model in hq["models"].items() if not name.startswith("lock_study_")}
    reviews = json.loads((foam / "combined-quality-reviews.json").read_text())
    quality = []
    for scope, catalogue, inventory_name in (("canonical", canonical, "canonical-inventory.json"),
                                            ("rejected-hq", hq, "rejected-hq-inventory.json"),
                                            ("rejected-hq-lock", mixed, "rejected-hq-lock-inventory.json")):
        current_reviews = json.loads(json.dumps(reviews))
        current_reviews["models"] = {name: value for name, value in reviews["models"].items() if name in catalogue["models"] or not name.startswith("hq_") and not name.startswith("lock_study_")}
        inventory = json.loads((prior / inventory_name).read_text())
        report = audit(catalogue, current_reviews, scope=inventory)
        assert not report["meets_objective"] and len(report["coverage_gaps"]) == 4
        assert all(row["score"] < 8 and row["status"] not in ("stale-review", "stale-evidence") for row in report["models"])
        (HERE / f"{scope}-quality.json").write_text(json.dumps(report, indent=2) + "\n")
        write_ratings_csv(HERE / f"{scope}-ratings.csv", report["models"])
        quality.append({"scope": scope, "rows": len(report["models"]), "individual_records": sum(row["status"] == "individually-reviewed" for row in report["models"]),
                        "approvals": 0, "coverage_gaps": 4, "meets_objective": False})
    assert [row["rows"] for row in quality] == [2866, 2950, 2998]
    (HERE / "quality-scope-verification.json").write_text(json.dumps(quality, indent=2) + "\n")
    summary = {"retained_utc": datetime.now(timezone.utc).isoformat(), "quiet_native_controls": len(images), "corrected_controls": 76,
               "retained_rejected_initial_controls": 5, "original_source_file_records": len(sources), "full_lossless_world_images": len(images),
               "geometry_approvals": 0, "canonical_bindings_changed": False, "quality": quality}
    (HERE / "retention-verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

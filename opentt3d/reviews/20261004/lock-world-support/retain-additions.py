"""Retain visibility controls and individual bound-state screening, without approvals."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from quality_audit import fingerprint


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def retain(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert digest(source) == digest(destination)
    else:
        shutil.copy2(source, destination)


def main():
    build = ROOT / "build-macos"
    prefix = "breadth-original-lock-world-support-visibility"
    runs = json.loads((build / f"{prefix}-runs.json").read_text())
    assert len(runs) == 18 and all(row["exit_code"] == 0 and row["independent_water_exact"] for row in runs)
    retain(build / f"{prefix}-runs.json", HERE / "visibility-runs.json")
    retain(build / f"{prefix}-verification.json", HERE / "visibility-native-verification.json")
    images, source_files = [], []
    for row in runs:
        original = Path(row["output"])
        target = HERE / "native-controls/visibility" / row["scope"] / row["visibility"] / row["backend"]
        for name in ("run.log", "result.json", "openttd.cfg", "scripts/game_start.scr", "screenshot/smoke.png", "renderer3d-reference/water-live.json"):
            retain(original / name, target / name)
        for source in sorted((original / "renderer3d-reference").glob("*.pam")):
            portable = target / "renderer3d-reference" / source.name
            retain(source, portable)
            source_files.append({"original": str(source.relative_to(ROOT)), "portable_image": str(portable.relative_to(ROOT)), "sha256": digest(portable)})
        screenshot = target / "screenshot/smoke.png"
        images.append({"scope": row["scope"], "visibility": row["visibility"], "backend": row["backend"],
                       "image": str(screenshot.relative_to(ROOT)), "sha256": digest(screenshot)})
    (HERE / "visibility-world-images.json").write_text(json.dumps(images, indent=2) + "\n")
    (HERE / "visibility-source-file-map.json").write_text(json.dumps(source_files, indent=2) + "\n")
    for name in ("tools/opentt3d/smoke.py", "tools/opentt3d/test_smoke.py"):
        retain(ROOT / name, HERE / "final-source" / name)
    with gzip.open(HERE / "complete-diagnostic-catalogue.json.gz", "rt") as source:
        catalogue = json.load(source)
    prior = ROOT / "opentt3d/reviews/20261003/water-foam-palette-study/combined-quality-reviews.json"
    model_reviews = json.loads(prior.read_text())["models"]
    public = ROOT / "opentt3d/reviews/20261003/water-live-selectors/public-fixtures"
    sheets = json.loads((HERE / "matrix-runs.json").read_text())
    full_images = json.loads((HERE / "full-world-images.json").read_text())
    climates = ("temperate", "arctic", "tropic", "toyland")
    states = []
    for climate, label in enumerate(climates):
        fixture = json.loads((public / label / "fixture.json").read_text())
        assert digest(public / label / "save/lock-fixture.sav") == fixture["save_sha256"]
        for owner in range(48):
            elevation, part, face = owner//24, (owner%24)//8, (owner%8)//4
            direction = (1, 0, 2, 3)[owner%4]
            site = next(site for site in fixture["locks"] if site["elevation"] == elevation and site["direction"] == direction)
            sources, worlds = [], []
            for backend in ("vulkan", "opengl"):
                row = next(row for row in sheets if row["climate"] == label and row["elevation"] == elevation and row["direction"] == direction and row["backend"] == backend)
                wall = next(wall for wall in row["emitted_walls"] if wall["owner"] == owner)
                tile = (site["tile"], site["lower"], site["upper"])[part]
                assert wall["climate"] == climate and wall["tile_xy"] == [tile % fixture["map_width"], tile // fixture["map_width"]]
                sources.append(wall)
                image = next(image for image in full_images if image["phase"] == "matrix" and image["climate"] == label and
                             image["elevation"] == elevation and image["direction"] == direction and image["backend"] == backend)
                worlds.append({"backend": backend, "image": image["image"], "sha256": image["sha256"]})
            assert sources[0] == sources[1]
            name = catalogue["bindings"]["lock_walls"][str(owner)][str(climate)]
            model_fingerprint = fingerprint(catalogue["models"][name], catalogue["materials"])
            assert model_fingerprint == model_reviews[name]["fingerprint"] and model_reviews[name]["score"] == 6
            support = ([[-0.5, 0, 8, 8], [0, 0.5, 0, 8], [0.5, 0, 0, 8], [0, -0.5, 8, 8]][direction] if part == 0 else [0, 0, 0, 0])
            evidence = {"source_model_fingerprint": model_fingerprint, "runtime_column_support": support,
                        "source_owner": owner, "climate": climate, "selected_source": sources[0], "worlds": worlds}
            state_fingerprint = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            states.append({"owner": owner, "climate": climate, "climate_name": label, "part": part, "direction": direction, "face": face, "elevation": elevation,
                           "model": name, "representation": "diagnostic-bound-voxel-instance", "score": 5, "status": "structural-screen-only",
                           "checks": dict.fromkeys(("source", "orbit", "street", "world", "states", "consistency"), False),
                           "canonical_binding": False, "geometry_approved": False, "fingerprint": state_fingerprint, **evidence,
                           "defects": model_reviews[name]["defects"] + [
                               "Supported live instance is separately screened5/10; it inherits no aesthetic approval from the provisional6/10 source study.",
                               "Strict paired world pixels differ. Supported orbit/street/source fidelity, independent animation, ship/terrain/custom-family/lock-specific picking and sustained performance are not accepted."],
                           "public_fixture": str((public / label / "fixture.json").relative_to(ROOT)), "save_sha256": fixture["save_sha256"]})
    path = HERE / "bound-lock-state-records.json.gz"
    assert not path.exists()
    with path.open("xb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            compressed.write((json.dumps(states, indent=2) + "\n").encode())
    receipt = {"retained_utc": datetime.now(timezone.utc).isoformat(), "visibility_controls": len(runs),
               "visibility_source_file_records": len(source_files), "individual_diagnostic_bound_state_records": len(states), "geometry_approvals": 0}
    (HERE / "additional-retention-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()

"""Verify the complete diagnostic evidence and retained negative quality decisions."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from quality_audit import fingerprint


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def files():
    return [path for path in sorted(HERE.rglob("*")) if path.is_file() and "__pycache__" not in path.parts
            and path.name != "evidence-sha256.json"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true", help="Refresh documentation hashes, never source/model/native evidence")
    args = parser.parse_args()
    evidence_path = HERE / "evidence-sha256.json"
    if not args.seal:
        evidence = json.loads(evidence_path.read_text())
        assert {str(path.relative_to(ROOT)) for path in files()} == set(evidence["files"])
        assert all(digest(ROOT / name) == expected for name, expected in evidence["files"].items())
    before = json.loads((HERE / "before-manifest.json").read_text())
    assert all(digest(ROOT / name) == expected for name, expected in before["files"].items())
    rejected = json.loads((HERE / "initial-pilot-rejection.json").read_text())
    assert rejected["status"] == "rejected" and len(rejected["reasons"]) == 3 and not rejected["geometry_approvals"]
    initial = json.loads((HERE / "initial-source/sha256.json").read_text())
    assert all(digest(HERE / "initial-source" / name) == expected for name, expected in initial.items())
    canonical, complete, missing = [json.load(gzip.open(HERE / f"{scope}-diagnostic-catalogue.json.gz", "rt"))
                                    for scope in ("canonical", "complete", "missing-owner")]
    assert len(canonical["models"]) == 1831 and len(complete["models"]) == len(missing["models"]) == 1879
    assert "lock_walls" not in canonical["bindings"]
    assert len(complete["bindings"]["lock_walls"]) == 48 and len(missing["bindings"]["lock_walls"]) == 47
    assert all(fingerprint(model, canonical["materials"]) == fingerprint(complete["models"][name], complete["materials"])
               for name, model in canonical["models"].items())
    assert {name: bindings for name, bindings in complete["bindings"].items() if name != "lock_walls"} == canonical["bindings"]
    assert complete["models"] == missing["models"] and complete["materials"] == missing["materials"]
    assert {name: bindings for name, bindings in missing["bindings"]["lock_walls"].items()} == {
        name: bindings for name, bindings in complete["bindings"]["lock_walls"].items() if name != "47"}
    for scope in ("canonical", "complete", "missing-owner"):
        manifest = json.loads((HERE / f"{scope}-frozen-manifest.json").read_text())
        with gzip.open(HERE / f"{scope}-diagnostic-catalogue.json.gz", "rb") as source:
            assert hashlib.file_digest(source, "sha256").hexdigest() == manifest["sha256"]["baseset/opentt3d-voxels.json"]
        assert manifest["geometry_approvals"] == 0 and not manifest["exact_tag_binary"]
    full = json.loads((HERE / "complete-frozen-manifest.json").read_text())
    for path in (HERE / "final-source/src").rglob("*"):
        if path.is_file():
            name = str(path.relative_to(HERE / "final-source"))
            assert digest(path) == full["runtime_sources"][name]
    images = json.loads((HERE / "full-world-images.json").read_text())
    source_files = json.loads((HERE / "source-file-map.json").read_text())
    assert len(images) == 81 and len(source_files) == 4486
    assert all(digest(ROOT / row["image"]) == row["sha256"] for row in images)
    assert all(digest(ROOT / row["portable_image"]) == row["sha256"] for row in source_files)
    matrix = json.loads((HERE / "matrix-native-verification.json").read_text())
    assert matrix["quiet_native_controls"] == 64 and len(matrix["observed_owner_climates"]) == 192
    assert matrix["all192_original_wall_and96_independent_water_source_states_exact"] and not matrix["geometry_approvals"]
    pairs = json.loads((HERE / "matrix-strict-verification.json").read_text())
    assert pairs["different_images"] == 32 and pairs["different_pixels"] == 1213 and not pairs["masks_or_tolerance"]
    pilot = json.loads((HERE / "pilot-strict-verification.json").read_text())
    assert pilot["exact_preservation_controls"] == 6
    assert [row["different_pixels"] for row in pilot["comparisons"] if row["scope"] == "paired-world"] == [74, 47, 39]
    quality = json.loads((HERE / "quality-scope-verification.json").read_text())
    assert [row["rows"] for row in quality] == [2866, 2950, 2998]
    assert [row["individual_records"] for row in quality] == [57, 141, 189]
    for row in quality:
        assert row["approvals"] == 0 and row["coverage_gaps"] == 4 and not row["meets_objective"]
        report = json.loads((HERE / f"{row['scope']}-quality.json").read_text())
        assert not report["meets_objective"] and len(report["models"]) == row["rows"]
        assert all(model["score"] < 8 and model["status"] not in ("stale-review", "stale-evidence") for model in report["models"])
        assert b"\r\n" not in (HERE / f"{row['scope']}-ratings.csv").read_bytes()
    gates = json.loads((HERE / "required-eight-verification.json").read_text())["gates"]
    assert [row["rows"] for row in gates] == [2866, 2950, 2998]
    assert all(row["exit_code"] == 1 and row["approvals"] == 0 and row["coverage_gaps"] == 4 and not row["meets_objective"] for row in gates)
    visibility = json.loads((HERE / "visibility-native-verification.json").read_text())
    assert visibility["quiet_native_controls"] == 18 and visibility["independent_water_and_original_visibility_exact"]
    assert visibility["strict_preservation_passed"] and len(visibility["preservation_comparisons"]) == 10
    visible_images = json.loads((HERE / "visibility-world-images.json").read_text())
    assert len(visible_images) == 18
    assert all(digest(ROOT / row["image"]) == row["sha256"] for row in visible_images)
    visible_sources = json.loads((HERE / "visibility-source-file-map.json").read_text())
    assert all(digest(ROOT / row["portable_image"]) == row["sha256"] for row in visible_sources)
    with gzip.open(HERE / "bound-lock-state-records.json.gz", "rt") as source:
        states = json.load(source)
    assert len(states) == 192 and len({(row["owner"], row["climate"]) for row in states}) == 192
    assert all(row["score"] == 5 and not any(row["checks"].values()) and row["defects"] for row in states)
    assert all(row["canonical_binding"] is False and row["geometry_approved"] is False for row in states)
    for row in states:
        assert complete["bindings"]["lock_walls"][str(row["owner"])][str(row["climate"])] == row["model"]
        assert fingerprint(complete["models"][row["model"]], complete["materials"]) == row["source_model_fingerprint"]
        evidence = {key: row[key] for key in ("source_model_fingerprint", "runtime_column_support", "source_owner", "climate", "selected_source", "worlds")}
        assert hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == row["fingerprint"]
        assert all(digest(ROOT / world["image"]) == world["sha256"] for world in row["worlds"])
        fixture = ROOT / row["public_fixture"]
        assert digest(fixture.parent / "save/lock-fixture.sav") == row["save_sha256"]
    receipt = json.loads((HERE / "isolated-test-receipt.json").read_text())
    assert receipt["asset_tests"] == 253 and not receipt["quarantined_hq_artwork_compiler_tests_present"]
    if args.seal:
        summary = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "corrected_native_controls": 94, "rejected_initial_controls": 5,
                   "full_lossless_world_images": 99, "source_file_records": len(source_files)+len(visible_sources), "individual_bound_state_records": len(states),
                   "strict_same_backend_preservation_comparisons": 16, "strict_matrix_different_images": 32, "strict_matrix_different_pixels": 1213,
                   "canonical_assets_and_bindings_changed": False, "geometry_approvals": 0, "quality_scopes": quality,
                   "scope": "Diagnostic lock wall selection/support and original visibility only. No independent phase, ship, lock-specific pick, all-climate visibility, source-fidelity or performance acceptance."}
        (HERE / "verification.json").write_text(json.dumps(summary, indent=2) + "\n")
        evidence = {"files": {str(path.relative_to(ROOT)): digest(path) for path in files()}, "approvals": 0}
        evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"verified_portable_files": len(evidence["files"]), "full_lossless_world_images": 99,
                      "individual_bound_states": len(states), "approvals": 0, "meets_objective": False}))


if __name__ == "__main__":
    main()

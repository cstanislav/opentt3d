"""Verify all retained relief sources, study fingerprints, full comparisons and honest ratings."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compact_reviews import load_pam
from compare_galleries import captures, image
from quality_audit import fingerprint, REVIEW_CHECKS


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def files():
    return sorted(path for path in HERE.rglob("*") if path.is_file() and
                  "__pycache__" not in path.parts and path.name not in ("evidence-sha256.json",".DS_Store") and path.suffix != ".pyc")


def changed_pixels(left,right):
    assert left.size == right.size
    a,b = left.tobytes(),right.tobytes()
    return sum(a[index:index+4] != b[index:index+4] for index in range(0,len(a),4))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal",action="store_true",help="Refresh evidence hashes only, never a stopping clock or approval")
    args = parser.parse_args()
    canonical_bytes = gzip.decompress((HERE / "canonical-catalogue.json.gz").read_bytes())
    assert hashlib.sha256(canonical_bytes).hexdigest() == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
    canonical = json.loads(canonical_bytes)
    assert len(canonical["models"]) == 1831
    reconstructed = 0
    raw_bytes = 0
    world_images = 0
    strict_preservation = 0
    for phase in ("initial","revised"):
        target = HERE / (phase+"-native-controls")
        frozen = json.loads((target / "frozen-manifest.json").read_text())
        assert frozen["unbound_relief_studies"] == 8 and not frozen["runtime_bound"] and frozen["geometry_approvals"] == 0
        raw = gzip.decompress((target / "diagnostic-catalogue.json.gz").read_bytes())
        assert hashlib.sha256(raw).hexdigest() == frozen["sha256"]["baseset/opentt3d-voxels.json"]
        compiled = json.loads(raw)
        assert len(compiled["models"]) == 1839 and compiled["bindings"] == canonical["bindings"]
        assert all(fingerprint(model,canonical["materials"]) == fingerprint(compiled["models"][name],compiled["materials"])
                   for name,model in canonical["models"].items())
        spec = importlib.util.spec_from_file_location("relief_frozen_compiler_"+phase,target / "compiler-snapshot.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        authored = module.compile_catalogue(json.loads((target / "frozen-authored-source.json").read_text()))
        assert authored["bindings"] == {} and len(authored["models"]) == 8
        assert all(fingerprint(model,authored["materials"]) == frozen["study_fingerprints"][name] == fingerprint(compiled["models"][name],compiled["materials"])
                   for name,model in authored["models"].items())
        assert digest(target / "frozen-authored-source.json") == frozen["sha256"]["authored-source.json"]
        assert digest(target / "compiler-snapshot.py") == frozen["sha256"]["compiler-snapshot.py"]
        if phase == "revised": assert digest(HERE / "authored-source.json") == frozen["sha256"]["authored-source.json"]
        for row in json.loads((target / "lossless-images.json").read_text()):
            path = ROOT / row["portable"]
            assert digest(path) == row["png_sha256"] and row["exact_pam_reconstruction"] and row["original_retained"]
            with Image.open(path) as retained:
                header = retained.info["opentt3d_pam_header"].encode("ascii")
                assert retained.mode == "RGBA" and list(retained.size) == row["size"]
                restored = header+retained.tobytes()
            assert len(restored) == row["original_bytes"] and hashlib.sha256(restored).hexdigest() == row["pam_sha256"]
            reconstructed += 1; raw_bytes += len(restored)
        summary = json.loads((target / "verification.json").read_text())
        assert summary["lossless_pam_reconstructions"] == 192 and summary["quiet_controls"] == 8 and not summary["runtime_bound"]
        runs = {}
        for row in json.loads((target / "runs.json").read_text()):
            run = target / Path(row["output"]).name
            result = json.loads((run / "result.json").read_text())
            assert row["exit_code"] == 0 and result["background"] and result["synchronous_original_save_verified"]
            assert row["binary_sha256"] == frozen["sha256"]["opentt3d"]
            command = result["command"]
            assert command[command.index("-b")+1] == "40bpp-anim"
            assert "OpenGFX2 Classic" in command
            log = (run / "run.log").read_text()
            assert "background Cocoa window active=false, key=false, visible=false, policy=2" in log
            if row["gallery"]:
                assert "192 authored voxel views match unmerged geometry, CPU instances, palette recolouring and transparent picking" in log
                assert len(captures(run / "renderer3d-reference","model-voxel-river_relief_study_*")) == 72
            runs[row["climate"],row["backend"],row["scope"]] = run
            assert (run / "screenshot/smoke.png").is_file()
            world_images += 1
        left = captures(runs["temperate","vulkan","study"] / "renderer3d-reference","model-voxel-river_relief_study_*")
        right = captures(runs["temperate","opengl","study"] / "renderer3d-reference","model-voxel-river_relief_study_*")
        assert left.keys() == right.keys() and len(left) == 72
        differences = {name:changed_pixels(image(left[name]),image(right[name])) for name in left}
        assert len([count for count in differences.values() if count]) == 9
        assert sum(differences.values()) == (69 if phase == "initial" else 88)
        assert not any(count for name,count in differences.items() if name.endswith("-native"))
        for climate,pair_pixels in (("temperate",48),("toyland",76)):
            for backend in ("vulkan","opengl"):
                assert changed_pixels(image(runs[climate,backend,"canonical"] / "screenshot/smoke.png"),
                                      image(runs[climate,backend,"study"] / "screenshot/smoke.png")) == 0
                strict_preservation += 1
            for scope in ("canonical","study"):
                assert changed_pixels(image(runs[climate,"vulkan",scope] / "screenshot/smoke.png"),
                                      image(runs[climate,"opengl",scope] / "screenshot/smoke.png")) == pair_pixels
        reviews = json.loads((HERE / (phase+"-quality-reviews.json")).read_text())
        assert set(reviews["models"]) == set(authored["models"])
        for name,row in reviews["models"].items():
            assert row["score"] == 5 and row["defects"] and row["fingerprint"] == frozen["study_fingerprints"][name]
            assert all(row["checks"][gate] is False for gate in REVIEW_CHECKS)
            assert set(row["evidence_sha256"]) == set(row["evidence"])
            assert all(digest(ROOT / path) == sha for path,sha in row["evidence_sha256"].items())
        report = json.loads((HERE / (phase+"-full-catalogue-quality.json")).read_text())
        assert len(report["models"]) == 2874 and len(report["coverage_gaps"]) == 4 and not report["meets_objective"]
        assert sum(row["status"] == "individually-reviewed" for row in report["models"]) == 65
        assert not any(row["score"] >= 8 for row in report["models"])
        required = json.loads((HERE / (phase+"-required-eight-quality.json")).read_text())
        assert not required["meets_objective"] and len(required["models"]) == 2874 and len(required["coverage_gaps"]) == 4
        assert "Quality pass incomplete" in (HERE / (phase+"-required-eight.log")).read_text()
        csv = (HERE / (phase+"-full-catalogue-ratings.csv")).read_bytes()
        assert b"\r" not in csv and csv.endswith(b"\n")
    matrix = json.loads((HERE / "climate-source-index.json").read_text())
    assert len(matrix) == 20 and sum(row["study_model"] is not None for row in matrix) == 16
    assert all(digest(ROOT / row["portable_source"]) == row["sha256"] and not row["quality_approved"] and not row["runtime_bound"] for row in matrix)
    separated = json.loads((HERE / "source-paint-separation-corrected/index.json").read_text())
    assert len(separated) == 8 and sum(row["native_pixel_counts"]["undecided"] for row in separated) == 17
    for row in separated:
        header,size,original = load_pam(ROOT / row["source"]["portable_source"])
        payload = bytearray(len(original))
        for path in row["layers"].values():
            with Image.open(ROOT / path) as layer:
                assert layer.mode == "RGBA" and layer.size == size
                for index,value in enumerate(layer.tobytes()): payload[index] |= value
        assert bytes(payload) == original and hashlib.sha256(header+payload).hexdigest() == row["source_sha256"]
        assert not row["hidden_water_inpainted"] and not row["palette_phase_indices_recovered"] and not row["runtime_binding_allowed"]
    owners = json.loads((HERE / "diagnostic-source-instance-records.json").read_text())
    assert len(owners) == 16 and all(row["score"] == 3 and not row["quality_approved"] and not row["runtime_bound"] for row in owners)
    assert "AssertionError" in (HERE / "source-paint-separation.log").read_text()
    receipt = json.loads((HERE / "test-receipt.json").read_text())
    assert receipt["canonical_asset_tests"] == 253 and receipt["working_asset_tests"] == 271
    assert receipt["native_ctest_cases"] == 215 and receipt["harness_tests"] == 106 and receipt["study_structural_tests"] == 10
    stdout = gzip.decompress((HERE / receipt["unit_stdout_archive"]).read_bytes())
    assert hashlib.sha256(stdout).hexdigest() == receipt["unit_stdout_sha256"]
    assert b"All tests passed (2852023 assertions in 213 test cases)" in stdout
    assert "100% tests passed, 0 tests failed out of 215" in (HERE / "all-native-tests.log").read_text()
    assert "Ran 253 tests" in (HERE / "canonical-isolated-assets-tests.log").read_text()
    assert "Ran 271 tests" in (HERE / "all-working-assets-tests.log").read_text()
    assert "Ran 106 tests" in (HERE / "harness-tests.log").read_text()
    decisions = json.loads((HERE / "individual-decisions.json").read_text())
    assert decisions["new_runtime_voxel_coverage"] == 0 and decisions["geometry_approvals"] == 0
    evidence = HERE / "evidence-sha256.json"
    if args.seal:
        evidence.write_text(json.dumps({"sealed_utc":datetime.now(timezone.utc).isoformat(),
            "files":{str(path.relative_to(HERE)):digest(path) for path in files()},
            "scope":"Evidence hashes only; not the stopping clock, a runtime binding or aesthetic approval."},indent=2)+"\n")
    hashes = json.loads(evidence.read_text())["files"]
    assert set(hashes) == {str(path.relative_to(HERE)) for path in files()}
    assert all(digest(HERE / path) == sha for path,sha in hashes.items())
    print(json.dumps({"portable_files":len(hashes),"exact_pam_reconstructions":reconstructed,"reconstructed_pam_bytes":raw_bytes,
        "full_world_images":world_images,"exact_same_backend_preservation_pairs":strict_preservation,
        "complete_source_paint_reconstructions":8,"undecided_source_pixels":17,"individual_current_model_reviews":8,
        "current_model_score":5,"required_eight_goal_met":False,"runtime_bound":False,"geometry_approvals":0}))


if __name__ == "__main__":
    main()

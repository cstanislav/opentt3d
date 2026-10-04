"""Reverify complete snowy-bank evidence, raw registered sources and preserved scope."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "river-sloped-bank-breadth"
MANIFEST = HERE / "evidence-sha256.json"
RECEIPT = HERE / "portable-verification.json"
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import image
from quality_audit import fingerprint,REVIEW_CHECKS
sys.path.insert(0,str(ROOT / "tools/opentt3d"))
from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--seal",action="store_true")
    parser.add_argument("--check-local-mixed-work",action="store_true"); args = parser.parse_args()
    native = HERE / "initial-native-controls"
    manifest = json.loads((native / "frozen-manifest.json").read_text())
    payload = gzip.decompress((native / "diagnostic-catalogue.json.gz").read_bytes())
    assert hashlib.sha256(payload).hexdigest() == manifest["sha256"]["baseset/opentt3d-voxels.json"]
    for source,name in (("compiler-snapshot.py","compiler-snapshot.py"),("authored-source.json","frozen-authored-source.json"),("test_authored_study.py","frozen-test_authored_study.py")):
        assert digest(native / name) == manifest["sha256"][source]
    assert digest(native / "compiler-snapshot.py") == digest(HERE.parent / "river-relief-ownership/approved-compiler-snapshot.py")
    catalogue = json.loads(payload)
    prior = json.loads(gzip.decompress((PRIOR / "initial-native-controls/diagnostic-catalogue.json.gz").read_bytes()))
    assert len(catalogue["models"]) == 1931 and len(prior["models"]) == 1911
    assert catalogue["bindings"] == prior["bindings"] and catalogue["materials"][:len(prior["materials"])] == prior["materials"]
    assert all(catalogue["models"][name] == model for name,model in prior["models"].items())
    spec = importlib.util.spec_from_file_location("portable_snow_compiler",native / "compiler-snapshot.py")
    compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)
    study = compiler.compile_catalogue(json.loads((native / "frozen-authored-source.json").read_text()))
    assert len(study["models"]) == 20 and study["bindings"] == {}
    assert all(fingerprint(model,study["materials"]) == fingerprint(catalogue["models"][name],catalogue["materials"]) for name,model in study["models"].items())
    count,original_bytes = 0,0
    for row in json.loads((native / "lossless-images.json").read_text()):
        path = ROOT / row["portable"]; assert digest(path) == row["png_sha256"]
        with Image.open(path) as picture:
            assert picture.mode == "RGBA" and list(picture.size) == row["size"]
            original = picture.info["opentt3d_pam_header"].encode("ascii")+picture.tobytes()
        assert len(original) == row["original_bytes"] and hashlib.sha256(original).hexdigest() == row["pam_sha256"]
        count += 1; original_bytes += len(original)
    assert count == 392 and original_bytes == 134486480
    verification = json.loads((native / "verification.json").read_text())
    assert verification["fresh_acknowledged_quiet_study_runs"] == verification["reused_immutable_acknowledged_canonical_controls"] == 2
    assert not verification["strict_renderers_accepted"] and verification["quality_approvals"] == verification["runtime_bank_coverage_accepted"] == 0
    assert len(verification["controls"]) == 4 and sum(row["reused_prior_run"] for row in verification["controls"]) == 2
    assert all(row["exact_original_save_bytes"] for row in verification["original_save_file_pairs"])
    for row in verification["controls"]:
        run = ROOT / row["control"]; result = json.loads((run / "result.json").read_text())
        assert result["background"] and result["image_size"] == [640,480] and result["original_allow_hidpi"] is False
        assert result["command"][result["command"].index("-b")+1] == "40bpp-anim"
        config = (run / "openttd.cfg").read_text(); assert "threaded_saves = false" in config and "allow_hidpi = false" in config
        commands = [line for line in (run / "scripts/game_start.scr").read_text().splitlines() if not line.startswith(("script","echo "))]
        require_console_command_acknowledgements(run / "console-review.log",commands); require_synchronous_fixture_save(run / "save/smoke-state.sav")
        assert result["original_console_commands_acknowledged"] == len(commands) and result["original_console_save_success_recorded"]
        assert "whole-world atlas relocation preserves" in (run / "run.log").read_text()
    comparisons = {row["label"]:row for row in verification["comparisons"]}
    assert comparisons["complete-model-pairs"]["different_images"] == 12 and comparisons["complete-model-pairs"]["different_pixels"] == 260
    assert comparisons["registered-native-pairs"]["exit_code"] == 0 and comparisons["canonical-paired-world"]["different_pixels"] == 18
    assert all(row["exit_code"] == 0 for row in verification["comparisons"] if "-unbound-" in row["label"])
    sources = json.loads((HERE / "actual-source-index.json").read_text()); assert len(sources) == 20
    assert Counter(row["slope"] for row in sources) == {0:12,3:2,6:2,9:2,12:2}
    assert all(digest(ROOT / row["source_pam"]) == row["source_pam_sha256"] and row["source_height"] > 0 for row in sources)
    assert all(not row["public_terrain_type_query_performed"] and not row["quality_approved"] for row in sources)
    sources = {f"river_bank_snow_study_arctic_offset{row['requested_offset']:02d}":row for row in sources}
    reviews = json.loads((HERE / "current-quality-reviews.json").read_text())["models"]
    assert len(reviews) == 20 and Counter(row["score"] for row in reviews.values()) == {4:12,5:8}
    for name,row in reviews.items():
        assert row["defects"] and set(row["checks"]) == set(REVIEW_CHECKS) and not any(row["checks"].values())
        assert row["fingerprint"] == fingerprint(catalogue["models"][name],catalogue["materials"])
        assert set(row["evidence"]) == set(row["evidence_sha256"])
        assert all(digest(ROOT / path) == sha for path,sha in row["evidence_sha256"].items())
    instances = json.loads((HERE / "diagnostic-source-instance-records.json").read_text()); assert len(instances) == 20
    assert all(row["score"] == 3 and not row["runtime_bound"] and not row["quality_approved"] for row in instances)
    source_audit = json.loads((HERE / "source-native-audit.json").read_text())
    assert source_audit["models"] == source_audit["different_images"] == 20 and source_audit["different_pixels"] == 2731
    assert source_audit["silhouette_differences_additional_diagnostic"] == 941 and source_audit["all_raw_image_bytes_preserved_without_alpha_compositing"]
    spec = importlib.util.spec_from_file_location("snow_raw_registration_recheck",PRIOR / "registered-bytes.py")
    raw = importlib.util.module_from_spec(spec); spec.loader.exec_module(raw)
    for row in source_audit["rows"]:
        source = sources[row["model"]]; original = raw.registered(image(ROOT / source["source_pam"]),source["native_offset"])
        paths = [ROOT / path for path in row["evidence_sha256"]]; registration = next(path for path in paths if path.suffix == ".json")
        model_path = next(path for path in paths if path.stem.endswith("-native"))
        model = raw.native(image(model_path),json.loads(registration.read_text()))
        (a,b),bounds = raw.pair(original,model); x,y = a.tobytes(),b.tobytes()
        assert list(bounds) == row["shared_bounds"] and list(original[1]) == row["raw_source_bounds"] and list(model[1]) == row["raw_native_bounds"]
        assert sum(x[index:index+4] != y[index:index+4] for index in range(0,len(x),4)) == row["complete_rgba_changed_pixels"]
        assert sum(bool(x[index+3]) != bool(y[index+3]) for index in range(0,len(x),4)) == row["alpha_presence_differences_additional_diagnostic"]
    gate = json.loads((HERE / "required-eight-gate-receipt.json").read_text()); report = json.loads((HERE / "current-full-catalogue-quality.json").read_text())
    assert gate["exit_code"] == 1 and gate["quality_rows"] == 2966 and gate["coverage_gaps"] == 4 and gate["quality_approvals"] == 0 and not gate["required_eight_met"]
    assert len(report["models"]) == 2966 and sum(row["status"] == "individually-reviewed" for row in report["models"]) == 157 and not report["meets_objective"]
    state = json.loads((HERE / "state-breadth-inventory.json").read_text())
    assert state["conditional_bank_shape_slots"] == 240 and state["earlier_conditional_slots_unobserved"] == 160 and state["new_conditional_shape_slots_claimed"] == 0
    assert state["additional_particular_snow_paint_variants"] == 20 and digest(PRIOR / "current-conditional-family-inventory.json") == state["prior_conditional_inventory_sha256"]
    if args.check_local_mixed_work:
        preserved = json.loads((HERE.parent / "river-bank-breadth/mixed-work-preservation-before-bank-commit.json").read_text())
        assert all(digest(ROOT / path) == sha for path,sha in preserved["working_sha256"].items())
    files = sorted(path for path in HERE.rglob("*") if path.is_file() and path not in {MANIFEST,RECEIPT} and "__pycache__" not in path.parts
        and path.suffix != ".pyc" and not path.name.startswith("portable-verify-command"))
    hashes = {str(path.relative_to(HERE)):{"sha256":digest(path),"bytes":path.stat().st_size} for path in files}
    if args.seal: MANIFEST.write_text(json.dumps({"format":1,"files":hashes,"quality_approved":False},indent=2)+"\n")
    assert json.loads(MANIFEST.read_text())["files"] == hashes, "Changed or missing evidence is not silently accepted"
    receipt = {"verified_utc":datetime.now(timezone.utc).isoformat(),"portable_files":len(files),"lossless_pam_reconstructions":count,
        "complete_original_pam_bytes_reconstructed":original_bytes,"fresh_acknowledged_quiet_study_runs":2,"reused_immutable_acknowledged_canonical_controls":2,
        "individual_snow_model_screenings":20,"independent_actual_source_instance_screenings":20,"earlier_bank_models_exact":80,
        "canonical_1831_models_materials_bindings_exact":True,"all_file_and_model_evidence_hashes_exact":True,"raw_source_native_failures_recomputed":True,
        "model_backend_failed_images":12,"model_backend_failed_pixels":260,"complete_source_native_failed_images":20,"complete_source_native_failed_pixels":2731,
        "runtime_bank_coverage_accepted":0,"quality_approvals":0,"local_uncommitted_quarantine_also_verified":args.check_local_mixed_work,
        "required_eight_met":False,"recommended_release_changed":False,"stopping_clock_unchanged":True}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt))


if __name__ == "__main__": main()

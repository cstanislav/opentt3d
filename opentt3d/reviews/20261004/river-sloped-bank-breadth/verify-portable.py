"""Seal/reverify every full sloped-bank evidence byte, without granting approval."""
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
FLAT = HERE.parent / "river-bank-breadth"
MANIFEST = HERE / "evidence-sha256.json"
RECEIPT = HERE / "portable-verification.json"
sys.path.insert(0,str(ROOT / "tools/assets"))
from quality_audit import fingerprint,REVIEW_CHECKS
sys.path.insert(0,str(ROOT / "tools/opentt3d"))
from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--seal",action="store_true")
    parser.add_argument("--check-local-mixed-work",action="store_true",help="Also verify this checkout's uncommitted quarantine; not a requirement on clean portable checkouts")
    args = parser.parse_args()
    native = HERE / "initial-native-controls"
    manifest = json.loads((native / "frozen-manifest.json").read_text())
    payload = gzip.decompress((native / "diagnostic-catalogue.json.gz").read_bytes())
    assert hashlib.sha256(payload).hexdigest() == manifest["sha256"]["baseset/opentt3d-voxels.json"]
    for source,name in (("compiler-snapshot.py","compiler-snapshot.py"),("authored-source.json","frozen-authored-source.json"),("test_authored_study.py","frozen-test_authored_study.py")):
        assert digest(native / name) == manifest["sha256"][source]
    assert digest(native / "compiler-snapshot.py") == digest(HERE.parent / "river-relief-ownership/approved-compiler-snapshot.py")
    compiled = json.loads(payload)
    prior = json.loads(gzip.decompress((FLAT / "acknowledged-native-controls/diagnostic-catalogue.json.gz").read_bytes()))
    assert len(compiled["models"]) == 1911 and len(prior["models"]) == 1879
    assert compiled["bindings"] == prior["bindings"] and compiled["materials"][:len(prior["materials"])] == prior["materials"]
    assert all(compiled["models"][name] == model for name,model in prior["models"].items())
    spec = importlib.util.spec_from_file_location("portable_sloped_bank_compiler",native / "compiler-snapshot.py")
    compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)
    study = compiler.compile_catalogue(json.loads((native / "frozen-authored-source.json").read_text()))
    assert len(study["models"]) == 32 and study["bindings"] == {}
    assert all(fingerprint(model,study["materials"]) == fingerprint(compiled["models"][name],compiled["materials"]) for name,model in study["models"].items())
    images,original_bytes = 0,0
    for row in json.loads((native / "lossless-images.json").read_text()):
        path = ROOT / row["portable"]; assert digest(path) == row["png_sha256"]
        with Image.open(path) as picture:
            assert picture.mode == "RGBA" and list(picture.size) == row["size"]
            original = picture.info["opentt3d_pam_header"].encode("ascii")+picture.tobytes()
        assert len(original) == row["original_bytes"] and hashlib.sha256(original).hexdigest() == row["pam_sha256"]
        images += 1; original_bytes += len(original)
    assert images == 704 and original_bytes == 336137248
    verification = json.loads((native / "verification.json").read_text())
    assert verification["fresh_acknowledged_quiet_study_runs"] == verification["reused_immutable_acknowledged_canonical_controls"] == 8
    assert not verification["strict_renderers_accepted"] and verification["quality_approvals"] == verification["runtime_bank_coverage_accepted"] == 0
    assert sum(row["different_images"] for row in verification["comparisons"] if row["label"].endswith("-complete-model-pairs")) == 17
    assert sum(row["different_pixels"] for row in verification["comparisons"] if row["label"].endswith("-complete-model-pairs")) == 34
    assert all(row["exit_code"] == 0 for row in verification["comparisons"] if row["label"].endswith("-registered-native-pairs"))
    controls = verification["controls"]; assert len(controls) == 16 and sum(row["reused_prior_run"] for row in controls) == 8
    for row in controls:
        run = ROOT / row["control"]; result = json.loads((run / "result.json").read_text())
        assert result["background"] and result["image_size"] == [640,480] and result["original_allow_hidpi"] is False
        config = (run / "openttd.cfg").read_text(); assert "threaded_saves = false" in config and "allow_hidpi = false" in config
        commands = [line for line in (run / "scripts/game_start.scr").read_text().splitlines() if not line.startswith(("script", "echo "))]
        require_console_command_acknowledgements(run / "console-review.log",commands)
        require_synchronous_fixture_save(run / "save/smoke-state.sav")
        assert result["original_console_commands_acknowledged"] == len(commands) and result["original_console_save_success_recorded"]
        assert "whole-world atlas relocation preserves" in (run / "run.log").read_text()
    sources = json.loads((HERE / "actual-source-index.json").read_text()); assert len(sources) == 32
    assert all(digest(ROOT / row["source_pam"]) == row["source_pam_sha256"] for row in sources)
    assert Counter(row["source_state"] for row in sources) == {"elevated":26,"sea-level-observation":6}
    conditional = json.loads((HERE / "current-conditional-family-inventory.json").read_text())
    assert len(conditional["states"]) == 240 and sum(row["sloped_candidate_authored"] for row in conditional["states"]) == 32
    assert sum(row["sloped_slot_unobserved_in_this_increment"] for row in conditional["states"]) == 160
    assert all(not row["runtime_source_coverage_accepted"] and not row["quality_approved"] for row in conditional["states"])
    assert digest(FLAT / "evidence-sha256.json") == conditional["existing_flat_evidence_sha256"]
    reviews = json.loads((HERE / "current-quality-reviews.json").read_text())["models"]
    assert len(reviews) == 32 and Counter(row["score"] for row in reviews.values()) == {4:23,5:9}
    for name,row in reviews.items():
        assert row["defects"] and set(row["checks"]) == set(REVIEW_CHECKS) and not any(row["checks"].values())
        assert row["fingerprint"] == fingerprint(compiled["models"][name],compiled["materials"])
        assert set(row["evidence"]) == set(row["evidence_sha256"])
        assert all(digest(ROOT / path) == sha for path,sha in row["evidence_sha256"].items())
    instances = json.loads((HERE / "diagnostic-source-instance-records.json").read_text()); assert len(instances) == 32
    assert all(row["score"] == 3 and not row["runtime_bound"] and not row["quality_approved"] for row in instances)
    source_audit = json.loads((HERE / "source-native-audit.json").read_text())
    assert source_audit["models"] == source_audit["different_images"] == 32 and source_audit["different_pixels"] == 6399
    assert source_audit["silhouette_differences_additional_diagnostic"] == 3226 and source_audit["source_wave_pixels_retained_in_full_comparison"]
    assert source_audit["all_raw_image_bytes_preserved_without_alpha_compositing"]
    flat_supplement = json.loads((HERE / "earlier-flat-byte-preserving-source-native-audit.json").read_text())
    assert flat_supplement["models"] == flat_supplement["different_images"] == 48 and flat_supplement["different_pixels"] == 5128
    assert not flat_supplement["prior_full_raw_byte_preservation_claim_accepted"]
    assert digest(ROOT / flat_supplement["retained_immutable_prior_audit"]) == flat_supplement["retained_immutable_prior_audit_sha256"]
    retained = json.loads((HERE / "retained-alpha-composited-audit/rejection.json").read_text())
    assert not retained["full_raw_fidelity_accepted"] and retained["quality_approvals"] == 0
    for path,sha in retained["original_reports_and_drivers_sha256"].items():
        assert digest(HERE / "retained-alpha-composited-audit" / Path(path).name) == sha
    gate = json.loads((HERE / "required-eight-gate-receipt.json").read_text())
    assert gate["exit_code"] == 1 and not gate["required_eight_met"] and gate["quality_rows"] == 2946 and gate["coverage_gaps"] == 4 and gate["quality_approvals"] == 0
    report = json.loads((HERE / "current-full-catalogue-quality.json").read_text())
    assert len(report["models"]) == 2946 and sum(row["status"] == "individually-reviewed" for row in report["models"]) == 137 and not report["meets_objective"]
    if args.check_local_mixed_work:
        preserved = json.loads((FLAT / "mixed-work-preservation-before-bank-commit.json").read_text())
        assert all(digest(ROOT / path) == sha for path,sha in preserved["working_sha256"].items())
    excluded = {MANIFEST,RECEIPT}
    files = sorted(path for path in HERE.rglob("*") if path.is_file() and path not in excluded and "__pycache__" not in path.parts
        and path.suffix != ".pyc" and not path.name.startswith("portable-verify-command"))
    hashes = {str(path.relative_to(HERE)):{"sha256":digest(path),"bytes":path.stat().st_size} for path in files}
    if args.seal: MANIFEST.write_text(json.dumps({"format":1,"files":hashes,"quality_approved":False},indent=2)+"\n")
    assert json.loads(MANIFEST.read_text())["files"] == hashes, "Changed or missing evidence is not silently accepted"
    receipt = {"verified_utc":datetime.now(timezone.utc).isoformat(),"portable_files":len(files),"lossless_pam_reconstructions":images,
        "complete_original_pam_bytes_reconstructed":original_bytes,"fresh_acknowledged_quiet_study_runs":8,"reused_acknowledged_canonical_controls":8,
        "individual_sloped_model_screenings":32,"independent_actual_source_instance_screenings":32,"earlier_flat_studies_exact":48,
        "canonical_1831_models_materials_bindings_exact":True,"all_file_and_model_evidence_hashes_exact":True,
        "model_backend_failed_images":17,"model_backend_failed_pixels":34,"complete_source_native_failed_images":32,"complete_source_native_failed_pixels":6399,
        "remaining_sloped_conditional_slots_unobserved":160,"runtime_bank_coverage_accepted":0,"quality_approvals":0,
        "local_uncommitted_quarantine_also_verified":args.check_local_mixed_work,
        "required_eight_met":False,"recommended_release_changed":False,"stopping_clock_unchanged":True}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt))


if __name__ == "__main__": main()

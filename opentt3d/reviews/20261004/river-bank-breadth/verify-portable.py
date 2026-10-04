"""Verify full bank/source/world evidence without converting a partial study to approval."""
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
    args = parser.parse_args()
    canonical = json.loads(gzip.decompress((HERE.parent / "river-relief-breadth/canonical-catalogue.json.gz").read_bytes()))
    assert len(canonical["models"]) == 1831
    spec = importlib.util.spec_from_file_location("bank_portable_compiler",HERE / "acknowledged-native-controls/compiler-snapshot.py")
    compiler = importlib.util.module_from_spec(spec); spec.loader.exec_module(compiler)
    images,original_bytes,runs,acknowledged_runs = 0,0,0,0
    for phase,expected in (("initial",16),("revised",16),("snow-repaired",4),("paint-repaired",4),("acknowledged",16)):
        directory = HERE / (phase+"-native-controls")
        value = json.loads((directory / "verification.json").read_text()); assert value["quiet_controls"] == expected
        assert value["quality_approvals"] == value["runtime_bindings"] == 0 and not value["strict_renderers_accepted"]
        encoded = gzip.decompress((directory / "diagnostic-catalogue.json.gz").read_bytes())
        frozen = json.loads((directory / "frozen-manifest.json").read_text())
        assert hashlib.sha256(encoded).hexdigest() == frozen["sha256"]["baseset/opentt3d-voxels.json"]
        for source,name in (("compiler-snapshot.py","compiler-snapshot.py"),("authored-source.json","frozen-authored-source.json"),("test_authored_study.py","frozen-test_authored_study.py")):
            assert digest(directory / name) == frozen["sha256"][source]
        assert digest(directory / "compiler-snapshot.py") == digest(HERE.parent / "river-relief-ownership/approved-compiler-snapshot.py")
        catalogue = json.loads(encoded)
        assert len(catalogue["models"]) == 1879 and catalogue["bindings"] == canonical["bindings"]
        assert catalogue["materials"][:len(canonical["materials"])] == canonical["materials"]
        assert all(catalogue["models"][name] == model for name,model in canonical["models"].items())
        authored = compiler.compile_catalogue(json.loads((directory / "frozen-authored-source.json").read_text()))
        assert len(authored["models"]) == 48 and authored["bindings"] == {}
        assert all(fingerprint(model,authored["materials"]) == fingerprint(catalogue["models"][name],catalogue["materials"]) for name,model in authored["models"].items())
        for row in json.loads((directory / "lossless-images.json").read_text()):
            path = ROOT / row["portable"]; assert digest(path) == row["png_sha256"]
            with Image.open(path) as picture:
                assert picture.mode == "RGBA" and list(picture.size) == row["size"]
                original = picture.info["opentt3d_pam_header"].encode("ascii")+picture.tobytes()
            assert len(original) == row["original_bytes"] and hashlib.sha256(original).hexdigest() == row["pam_sha256"]
            images += 1; original_bytes += len(original)
        for row in json.loads((directory / "runs.json").read_text()):
            run = directory / Path(row["output"]).name; result = json.loads((run / "result.json").read_text())
            assert result["background"] and result["image_size"] == [640,480] and result["synchronous_original_save_verified"]
            assert result["original_allow_hidpi"] is False
            config = (run / "openttd.cfg").read_text(); assert "threaded_saves = false" in config and "allow_hidpi = false" in config
            require_synchronous_fixture_save(run / "save/smoke-state.sav")
            assert "whole-world atlas relocation preserves" in (run / "run.log").read_text()
            if phase == "acknowledged":
                commands = [line for line in (run / "scripts/game_start.scr").read_text().splitlines() if not line.startswith(("script", "echo "))]
                require_console_command_acknowledgements(run / "console-review.log",commands)
                assert result["original_console_commands_acknowledged"] == len(commands) and result["original_console_save_success_recorded"]
                acknowledged_runs += 1
            runs += 1
    assert runs == 56 and acknowledged_runs == 16 and images == 3472
    sources = json.loads((HERE / "actual-source-index.json").read_text()); assert len(sources) == 48
    assert all(digest(ROOT / row["source_pam"]) == row["source_pam_sha256"] for row in sources)
    upstream = json.loads((HERE / "pinned-source-index.json").read_text())
    assert len(upstream["files"]) == 6 and all(digest(ROOT / row["portable"]) == row["sha256"] for row in upstream["files"])
    assert all(digest(ROOT / row["image"]) == row["sha256"] for row in upstream["original_layers"])
    support = json.loads((HERE / "pinned-support-source-original-hashes.json").read_text())
    assert len(support["original_support_sources"]) == 5 and support["authored_changes_excluding_pinned_upstream_diff_check_exit_code"] == 0
    assert all(row["byte_exact"] and digest(ROOT / row["retained_path"]) == row["sha256"] for row in support["original_support_sources"])
    scope = json.loads((HERE / "complete-bank-family-inventory.json").read_text())
    assert len(scope["states"]) == 240 and sum(row["provisional_study_available"] for row in scope["states"]) == 48
    assert all(not row["runtime_source_coverage_accepted"] and not row["quality_approved"] for row in scope["states"])
    reviews = json.loads((HERE / "current-quality-reviews.json").read_text()); assert len(reviews["models"]) == 48
    assert Counter(row["score"] for row in reviews["models"].values()) == {4:24,5:24}
    current = catalogue
    for name,row in reviews["models"].items():
        assert row["defects"] and set(row["checks"]) == set(REVIEW_CHECKS) and not any(row["checks"].values())
        assert fingerprint(current["models"][name],current["materials"]) == row["fingerprint"]
        assert set(row["evidence"]) == set(row["evidence_sha256"])
        assert all(digest(ROOT / path) == sha for path,sha in row["evidence_sha256"].items())
    instances = json.loads((HERE / "diagnostic-source-instance-records.json").read_text()); assert len(instances) == 48
    assert all(row["score"] == 3 and not row["runtime_bound"] and not row["quality_approved"] for row in instances)
    source_audit = json.loads((HERE / "acknowledged-source-native-audit.json").read_text())
    assert source_audit["models"] == source_audit["different_images"] == 48 and source_audit["quality_approvals"] == 0
    noninterference = json.loads((HERE / "console-noninterference/verification.json").read_text())
    assert len(noninterference["comparisons"]) == 40 and all(row["exit_code"] == 0 for row in noninterference["comparisons"])
    gate = json.loads((HERE / "required-eight-gate-receipt.json").read_text())
    assert len(gate) == 2 and all(row["exit_code"] == 1 and not row["required_eight_met"] and row["coverage_gaps"] == 4 and row["quality_approvals"] == 0 for row in gate)
    excluded = {MANIFEST,RECEIPT}
    files = sorted(path for path in HERE.rglob("*") if path.is_file() and path not in excluded and "__pycache__" not in path.parts
        and path.suffix != ".pyc" and not path.name.startswith("portable-verify-command"))
    hashes = {str(path.relative_to(HERE)):{"sha256":digest(path),"bytes":path.stat().st_size} for path in files}
    if args.seal: MANIFEST.write_text(json.dumps({"format":1,"files":hashes,"quality_approved":False},indent=2)+"\n")
    assert json.loads(MANIFEST.read_text())["files"] == hashes, "Changed/missing evidence must be inspected, not silently accepted"
    value = {"verified_utc":datetime.now(timezone.utc).isoformat(),"portable_files":len(files),"native_controls_retained":runs,
        "original_console_acknowledged_runs":acknowledged_runs,"retained_earlier_console_evidence_gaps":40,
        "lossless_pam_reconstructions":images,"complete_original_pam_bytes_reconstructed":original_bytes,
        "all_portable_file_hashes_exact":True,"canonical_1831_models_materials_bindings_exact":True,
        "individual_current_model_reviews":48,"source_instances_separately_screened":48,
        "runtime_bank_coverage_accepted":0,"quality_approvals":0,"required_eight_objective_met":False,
        "recommended_release_changed":False,"stopping_clock_unchanged":True}
    RECEIPT.write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

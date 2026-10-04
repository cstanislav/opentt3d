"""Retain full bank studies and canonical worlds, not isolated success pixels."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--prefix",required=True)
    parser.add_argument("--revision",choices=("initial","revised","snow-repaired","paint-repaired","acknowledged"),default="initial")
    parser.add_argument("--frozen-prefix")
    args = parser.parse_args()
    target = HERE / (args.revision+"-native-controls")
    if target.exists(): parser.error("Retain previous controls")
    (target / "strict-comparisons").mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("bank_world_audit",HERE.parent / "river-relief-ownership/audit-world-controls.py")
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    records = json.loads((HERE / (args.prefix+"-runs.json")).read_text())
    climates = tuple(dict.fromkeys(row["climate"] for row in records))
    assert len(records) == 4*len(climates) and all(row["exit_code"] == 0 for row in records)
    images = []
    acknowledged = 0
    for row in records:
        source = ROOT / row["output"]; destination = target / Path(row["output"]).name
        audit.retain_run(source,destination,images)
        if args.revision == "acknowledged":
            sys.path.insert(0,str(ROOT / "tools/opentt3d"))
            from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save
            shutil.copy2(source / "console-review.log",destination / "console-review.log")
            commands = [line for line in (destination / "scripts/game_start.scr").read_text().splitlines() if not line.startswith(("script", "echo "))]
            require_console_command_acknowledgements(destination / "console-review.log",commands)
            require_synchronous_fixture_save(destination / "save/smoke-state.sav")
            result = json.loads((destination / "result.json").read_text())
            assert result["original_console_commands_acknowledged"] == len(commands) and result["original_console_save_success_recorded"]
            acknowledged += 1
    lookup = {(row["climate"],row["backend"],row["scope"]):target / Path(row["output"]).name for row in records}
    comparisons = []
    for climate in climates:
        for backend in ("vulkan","opengl"):
            a,b = [lookup[climate,backend,scope] for scope in ("canonical","study")]
            result = audit.compare(a / "screenshot/smoke.png",b / "screenshot/smoke.png","*",target / "strict-comparisons" / (climate+"-"+backend+"-unbound-world.json"))
            assert result["exit_code"] == 0
            comparisons.append(result)
            result = audit.compare(a / "renderer3d-reference",b / "renderer3d-reference","model-world-atlas-*",target / "strict-comparisons" / (climate+"-"+backend+"-unbound-atlas.json"))
            assert result["exit_code"] == 0
            comparisons.append(result)
        a,b = [lookup[climate,backend,"study"] / "renderer3d-reference" for backend in ("vulkan","opengl")]
        comparisons.append(audit.compare(a,b,"model-voxel-river_bank_study_"+climate+"_flat_*",target / "strict-comparisons" / (climate+"-complete-model-pairs.json")))
        comparisons.append(audit.compare(a,b,"model-voxel-river_bank_study_"+climate+"_flat_*-native",target / "strict-comparisons" / (climate+"-registered-native-pairs.json")))
        a,b = [lookup[climate,backend,"canonical"] / "screenshot/smoke.png" for backend in ("vulkan","opengl")]
        comparisons.append(audit.compare(a,b,"*",target / "strict-comparisons" / (climate+"-canonical-paired-world.json")))
    shutil.copy2(HERE / (args.prefix+"-runs.json"),target / "runs.json")
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    frozen = ROOT / "build-macos" / ((args.frozen_prefix or args.prefix)+"-frozen-build")
    source_revision = "paint-repaired" if args.revision == "acknowledged" else args.revision
    for name,path in (("diagnostic-catalogue.json.gz",HERE / ("diagnostic-catalogue.json.gz" if source_revision == "initial" else source_revision+"-diagnostic-catalogue.json.gz")),
        ("frozen-manifest.json",frozen / "manifest.json"),("frozen-authored-source.json",frozen / "authored-source.json"),
        ("compiler-snapshot.py",frozen / "compiler-snapshot.py"),("frozen-test_authored_study.py",frozen / "test_authored_study.py")):
        shutil.copy2(path,target / name)
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"quiet_controls":len(records),"individual_unbound_models":48,
        "gallery_climates":list(climates),"same_backend_world_pairs_exact":2*len(climates),"same_backend_atlas_views_exact":8*len(climates),"full_model_images":216*len(climates),
        "lossless_pam_reconstructions":len(images),"original_bytes_reconstructed":sum(row["original_bytes"] for row in images),
        "comparisons":comparisons,"runtime_bindings":0,"quality_approvals":0,
        "actual_console_acknowledged_runs":acknowledged,"actual_original_console_save_success_messages":acknowledged,
        "strict_renderers_accepted":not any(row["exit_code"] for row in comparisons),
        "native_equality_is_not_source_quality_or_complete_bank_coverage":True}
    (target / "verification.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value))


if __name__ == "__main__": main()

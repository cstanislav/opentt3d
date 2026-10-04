"""Audit complete sloped bank galleries and canonical noninterference; no runtime approval."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/opentt3d"))
from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save


def main():
    target = HERE / "initial-native-controls"
    if target.exists(): raise ValueError("Retain earlier complete native controls")
    (target / "strict-comparisons").mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("sloped_bank_audit",HERE.parent / "river-relief-ownership/audit-world-controls.py")
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    records = json.loads((HERE / "runs.json").read_text()); assert len(records) == 8 and all(row["exit_code"] == 0 for row in records)
    images,lookup,acks = [],{},[]
    for row in records:
        for scope,path in (("study",row["output"]),("canonical",row["reused_acknowledged_canonical_control"])):
            source = ROOT / path; destination = target / source.name
            audit.retain_run(source,destination,images)
            shutil.copy2(source / "console-review.log",destination / "console-review.log")
            commands = [line for line in (destination / "scripts/game_start.scr").read_text().splitlines() if not line.startswith(("script", "echo "))]
            require_console_command_acknowledgements(destination / "console-review.log",commands)
            require_synchronous_fixture_save(destination / "save/smoke-state.sav")
            result = json.loads((destination / "result.json").read_text())
            assert result["original_console_commands_acknowledged"] == len(commands) and result["original_console_save_success_recorded"]
            assert result["image_size"] == [640,480] and result["background"] and result["original_allow_hidpi"] is False
            lookup[row["climate"],row["backend"],scope] = destination
            acks.append({"control":str(destination.relative_to(ROOT)),"commands_acknowledged":len(commands),"save_success_message":True,"reused_prior_run":scope == "canonical"})
    comparisons = []
    for climate in ("temperate","arctic","tropic","toyland"):
        for backend in ("vulkan","opengl"):
            a,b = [lookup[climate,backend,scope] for scope in ("canonical","study")]
            label = climate+"-"+backend
            for scope,left,right,pattern in (("unbound-world",a / "screenshot/smoke.png",b / "screenshot/smoke.png","*"),
                ("unbound-atlas",a / "renderer3d-reference",b / "renderer3d-reference","model-world-atlas-*")):
                result = audit.compare(left,right,pattern,target / "strict-comparisons" / (label+"-"+scope+".json")); assert result["exit_code"] == 0
                comparisons.append(result)
        a,b = [lookup[climate,backend,"study"] / "renderer3d-reference" for backend in ("vulkan","opengl")]
        comparisons.append(audit.compare(a,b,"model-voxel-river_bank_slope_study_"+climate+"_*",target / "strict-comparisons" / (climate+"-complete-model-pairs.json")))
        comparisons.append(audit.compare(a,b,"model-voxel-river_bank_slope_study_"+climate+"_*-native",target / "strict-comparisons" / (climate+"-registered-native-pairs.json")))
        a,b = [lookup[climate,backend,"canonical"] / "screenshot/smoke.png" for backend in ("vulkan","opengl")]
        comparisons.append(audit.compare(a,b,"*",target / "strict-comparisons" / (climate+"-canonical-paired-world.json")))
    prefix = Path(records[0]["output"]).name.rsplit("-temperate-",1)[0]
    frozen = ROOT / "build-macos" / (prefix+"-frozen-build")
    for name,path in (("diagnostic-catalogue.json.gz",HERE / "diagnostic-catalogue.json.gz"),("frozen-manifest.json",frozen / "manifest.json"),
        ("frozen-authored-source.json",frozen / "authored-source.json"),("compiler-snapshot.py",frozen / "compiler-snapshot.py"),("frozen-test_authored_study.py",frozen / "test_authored_study.py")):
        shutil.copy2(path,target / name)
    shutil.copy2(HERE / "runs.json",target / "runs.json")
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"fresh_acknowledged_quiet_study_runs":8,
        "reused_immutable_acknowledged_canonical_controls":8,"controls":acks,"individual_unbound_sloped_owners":32,"earlier_flat_owners_unchanged":48,
        "same_backend_world_pairs_exact":8,"same_backend_atlas_images_exact":32,"complete_model_images":576,
        "lossless_pam_reconstructions":len(images),"original_bytes_reconstructed":sum(row["original_bytes"] for row in images),
        "comparisons":comparisons,"strict_renderers_accepted":not any(row["exit_code"] for row in comparisons),
        "runtime_bank_coverage_accepted":0,"quality_approvals":0,"source_quality_and_doubled_terrain_support_never_inferred_from_native_equality":True}
    (target / "verification.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

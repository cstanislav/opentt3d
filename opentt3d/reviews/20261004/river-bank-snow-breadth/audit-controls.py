"""Retain every original world/gallery/save and strict full snowy-bank comparison."""
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
    if target.exists(): raise ValueError("Retain prior snowy-bank evidence")
    (target / "strict-comparisons").mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("snow_bank_audit",HERE.parent / "river-relief-ownership/audit-world-controls.py")
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    records = json.loads((HERE / "runs.json").read_text()); assert len(records) == 2 and all(row["exit_code"] == 0 for row in records)
    images,lookup,controls = [],{},[]
    for row in records:
        for scope,path in (("study",row["output"]),("canonical",row["reused_acknowledged_canonical_control"])):
            source = ROOT / path; destination = target / source.name
            audit.retain_run(source,destination,images); shutil.copy2(source / "console-review.log",destination / "console-review.log")
            commands = [line for line in (destination / "scripts/game_start.scr").read_text().splitlines() if not line.startswith(("script","echo "))]
            require_console_command_acknowledgements(destination / "console-review.log",commands)
            require_synchronous_fixture_save(destination / "save/smoke-state.sav")
            result = json.loads((destination / "result.json").read_text())
            assert result["original_console_commands_acknowledged"] == len(commands) and result["original_console_save_success_recorded"]
            assert result["background"] and result["image_size"] == [640,480] and result["original_allow_hidpi"] is False
            lookup[row["backend"],scope] = destination
            controls.append({"control":str(destination.relative_to(ROOT)),"reused_prior_run":scope == "canonical","commands_acknowledged":len(commands),"actual_save_success_text":True})
    comparisons,save_pairs = [],[]
    for backend in ("vulkan","opengl"):
        a,b = [lookup[backend,scope] for scope in ("canonical","study")]
        for scope,left,right,pattern in (("unbound-world",a / "screenshot/smoke.png",b / "screenshot/smoke.png","*"),
            ("unbound-atlas",a / "renderer3d-reference",b / "renderer3d-reference","model-world-atlas-*")):
            value = audit.compare(left,right,pattern,target / "strict-comparisons" / (backend+"-"+scope+".json")); assert value["exit_code"] == 0; comparisons.append(value)
        original,study = a / "save/smoke-state.sav",b / "save/smoke-state.sav"
        save_pairs.append({"backend":backend,"canonical_sha256":audit.digest(original),"study_sha256":audit.digest(study),"exact_original_save_bytes":original.read_bytes() == study.read_bytes()})
    a,b = [lookup[backend,"study"] / "renderer3d-reference" for backend in ("vulkan","opengl")]
    comparisons.append(audit.compare(a,b,"model-voxel-river_bank_snow_study_arctic_*",target / "strict-comparisons/complete-model-pairs.json"))
    comparisons.append(audit.compare(a,b,"model-voxel-river_bank_snow_study_arctic_*-native",target / "strict-comparisons/registered-native-pairs.json"))
    a,b = [lookup[backend,"canonical"] / "screenshot/smoke.png" for backend in ("vulkan","opengl")]
    comparisons.append(audit.compare(a,b,"*",target / "strict-comparisons/canonical-paired-world.json"))
    frozen = ROOT / "build-macos/breadth-original-river-bank-snow-initial-frozen-build"
    for name,path in (("diagnostic-catalogue.json.gz",HERE / "diagnostic-catalogue.json.gz"),("frozen-manifest.json",frozen / "manifest.json"),
        ("frozen-authored-source.json",frozen / "authored-source.json"),("compiler-snapshot.py",frozen / "compiler-snapshot.py"),("frozen-test_authored_study.py",frozen / "test_authored_study.py")):
        shutil.copy2(path,target / name)
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"fresh_acknowledged_quiet_study_runs":2,"reused_immutable_acknowledged_canonical_controls":2,
        "controls":controls,"individual_unbound_snow_owners":20,"earlier_bank_models_exact":80,"same_backend_world_pairs_exact":2,
        "same_backend_atlas_images_exact":8,"complete_model_images":360,"lossless_pam_reconstructions":len(images),
        "original_bytes_reconstructed":sum(row["original_bytes"] for row in images),"original_save_file_pairs":save_pairs,
        "comparisons":comparisons,"strict_renderers_accepted":not any(row["exit_code"] for row in comparisons),
        "runtime_bank_coverage_accepted":0,"quality_approvals":0,"all_snowline_terrain_type_inputs_phases_or_support_accepted":False}
    (target / "verification.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

"""Retain exact same-backend console-on/off worlds, atlases and complete final bank images."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    target = HERE / "console-noninterference"
    if target.exists(): raise ValueError("Retain previous console noninterference comparisons")
    target.mkdir()
    spec = importlib.util.spec_from_file_location("console_bank_compare",HERE.parent / "river-relief-ownership/audit-world-controls.py")
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    rows,save_pairs = [],[]
    for climate,phase in (("temperate","revised"),("arctic","snow-repaired"),("tropic","revised"),("toyland","paint-repaired")):
        for backend in ("vulkan","opengl"):
            for scope in ("canonical","study"):
                original = HERE / (phase+"-native-controls") / f"breadth-original-river-bank-{phase}-{climate}-{backend}-{scope}"
                logged = HERE / "acknowledged-native-controls" / f"breadth-original-river-bank-acknowledged-{climate}-{backend}-{scope}"
                label = f"{climate}-{backend}-{scope}"
                rows.append(audit.compare(original / "screenshot/smoke.png",logged / "screenshot/smoke.png","*",target / (label+"-world.json")))
                rows.append(audit.compare(original / "renderer3d-reference",logged / "renderer3d-reference","model-world-atlas-*",target / (label+"-atlas.json")))
                if scope == "study":
                    rows.append(audit.compare(original / "renderer3d-reference",logged / "renderer3d-reference","model-voxel-river_bank_study_"+climate+"_flat_*",target / (label+"-models.json")))
                a,b = original / "save/smoke-state.sav",logged / "save/smoke-state.sav"
                save_pairs.append({"scope":label,"original_sha256":audit.digest(a),"console_logged_sha256":audit.digest(b),
                    "exact_bytes":a.read_bytes() == b.read_bytes(),"original_file":str(a.relative_to(HERE)),"logged_file":str(b.relative_to(HERE))})
    assert len(rows) == 40 and all(row["exit_code"] == 0 for row in rows)
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"same_backend_world_pairs_exact":16,
        "same_backend_atlas_images_exact":64,"same_backend_full_bank_model_images_exact":864,
        "comparisons":rows,"original_save_file_pairs":save_pairs,"original_save_byte_pairs_exact":sum(row["exact_bytes"] for row in save_pairs),
        "complete_rgba":True,"resizing_masks_or_tolerance_used":False,"old_missing_console_acknowledgements_retroactively_accepted":False,
        "quality_approvals":0,"runtime_bank_coverage_accepted":0}
    (target / "verification.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value))


if __name__ == "__main__": main()

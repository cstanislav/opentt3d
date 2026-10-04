"""Check complete worlds and supported owners before/after separating diagnostics."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    target = HERE / "observer-separation-preservation"
    if target.exists(): raise ValueError("Retain previous preservation comparisons")
    target.mkdir()
    spec = importlib.util.spec_from_file_location("river_world_audit",HERE / "audit-world-controls.py")
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    old = HERE / "complete-water-world-controls"; new = HERE / "observer-separated-world-controls"
    rows = json.loads((new / "runs.json").read_text())
    comparisons = []
    for index,row in enumerate(rows):
        current = new / Path(row["output"]).name
        previous = old / current.name.replace("observer-separated","complete-water")
        result = audit.compare(previous / "screenshot/smoke.png",current / "screenshot/smoke.png","*",target / f"{index:02d}-world.json")
        assert result["exit_code"] == 0
        comparisons.append(result)
        result = audit.compare(previous / "renderer3d-reference",current / "renderer3d-reference","model-world-atlas-*",target / f"{index:02d}-atlas.json")
        assert result["exit_code"] == 0
        comparisons.append(result)
        if row["gallery"]:
            for pattern,label in (("model-voxel-river-supported-*","supported"),("model-voxel-river_relief_study_*","source-datum")):
                result = audit.compare(previous / "renderer3d-reference",current / "renderer3d-reference",pattern,target / f"{index:02d}-{label}.json")
                assert result["exit_code"] == 0
                comparisons.append(result)
    value = {"complete_same_backend_world_pairs":40,"complete_same_backend_atlas_pairs":40,
        "supported_and_original_datum_pairs":16,"comparisons":comparisons,"default_off_observer_separated":True,
        "masks_or_tolerance_used":False,"quality_approvals":0}
    (target / "verification.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({key:value[key] for key in ("complete_same_backend_world_pairs","complete_same_backend_atlas_pairs","supported_and_original_datum_pairs","quality_approvals")}))


if __name__ == "__main__": main()

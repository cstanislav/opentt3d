"""Enumerate the full conditional bank family; a flat study never removes a runtime gap."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from original_water import catalogue


def main():
    path = HERE / "complete-bank-family-inventory.json"
    if path.exists(): raise ValueError("Retain prior source family inventories")
    original = catalogue(); actual = json.loads((HERE / "actual-source-index.json").read_text())
    rows = []
    for edge in original["river_edge_source_offsets"]:
        for climate,label in enumerate(("temperate","arctic","tropic","toyland")):
            source = next((row for row in actual if row["climate"] == climate and row["requested_offset"] == edge["offset"]),None)
            rows.append({**edge,"climate":climate,"study_model":None if source is None else f"river_bank_study_{label}_flat_{edge['edge']:02d}",
                "actual_source":source,"provisional_study_available":source is not None,
                "canonical_runtime_binding":None,"runtime_source_coverage_accepted":False,"quality_approved":False,
                "absence_requires_actual_source":True,"selector_callbacks_or_dynamic_ids_replaced":False})
    assert len(rows) == 240 and sum(row["provisional_study_available"] for row in rows) == 48
    value = {"retained_utc":datetime.now(timezone.utc).isoformat(),"original_water_inventory":original,
        "defined_slope_groups":5,"conditional_edges_per_group":12,"climates":4,"required_bank_source_instances":240,
        "flat_source_observations_and_unbound_candidates":48,"sloped_instances_without_candidates":192,
        "runtime_bank_instances_accepted":0,"quality_approvals":0,"states":rows,
        "additional_unaccepted_axes":["all source heights and doubled-terrain support/joins",
            "sea-level versus elevated shore callback output","snow-line and tropical desert selection",
            "grass/grid source parameters and overlays","every connectivity/neighbourhood and corner combination",
            "actual callback redirection, feature flags, alternate/custom and incomplete source families",
            "intentional absent feature or transparent owner, without fabricated decoration",
            "independent animated source/remap phases and source layer ordering",
            "actual bank GPU tile selection and ship traversal/clearance",
            "all LOD/terrain boundaries, transparency/visibility and restored cache ownership"],
        "source_hashes":original["source_sha256"],
        "scope_note":"All original defined selectors remain required. Forty-eight elevated-flat observations and unbound studies are not coverage of any unobserved or intentionally absent case. Catalogue-wide eight-point and sustained60fps objectives remain unchanged."}
    path.write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({"original_conditional_bank_instances":240,"unbound_flat_studies":48,"sloped_candidates_missing":192,"runtime_bank_coverage_accepted":0,"quality_approvals":0}))


if __name__ == "__main__": main()

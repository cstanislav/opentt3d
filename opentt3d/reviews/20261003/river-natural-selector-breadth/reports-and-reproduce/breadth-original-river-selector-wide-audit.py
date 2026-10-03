"""Reconcile wider natural selections with prior observed owners without inventing missing ones."""
from pathlib import Path
import hashlib, json

root = Path("build-macos")
out = root / "breadth-original-river-selector-wide-selector-matrix.json"
assert not out.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
wide_path = root / "breadth-original-river-selector-wide-verification.json"
prior_path = root / "breadth-original-river-selector-classic-verification.json"
wide,prior = (json.loads(path.read_text()) for path in (wide_path,prior_path))
assert wide["native_quiet_controls"] == 8 and wide["approvals"] == 0
matrix,shared = [],[]
for climate in ("temperate","arctic","tropic","toyland"):
    current,old = (report["selected_sources"][climate] for report in (wide,prior))
    values = current["slope_source_values"]
    assert len(values) == 5 and not current["geometry_or_quality_approved"]
    for kind,key in (("ground_sources",lambda row:row["tile"]),("edge_sources",lambda row:(row["tile"],row["requested_offset"]))):
        sources,earlier = ({key(row):row for row in report[kind]} for report in (current,old))
        common = sources.keys() & earlier.keys()
        assert all(sources[value] == earlier[value] for value in common),(climate,kind)
        shared.append({"climate":climate,"kind":kind,"prior_states":len(earlier),"wide_states":len(sources),
            "common_states_metadata_and_bytes_exact":len(common),"previous_states_not_in_wider_camera":sorted(earlier.keys()-sources.keys()),
            "new_wider_states":len(sources.keys()-earlier.keys())})
    for slope_name,slope_value in values.items():
        ground = [row for row in current["ground_sources"] if row["slope"] == slope_value]
        banks = [row for row in current["edge_sources"] if row["slope"] == slope_value]
        absent = [row for row in current["absent_edge_features"] if row["slope"] == slope_value]
        inputs = sorted({row["requested_offset"] for row in banks})
        matrix.append({"climate":climate,"slope_name":slope_name,"slope_value":slope_value,
            "observed_ground_owners":len(ground),"observed_bank_owners":len(banks),"observed_actual_absent_features":len(absent),
            "observed_original_source_heights":sorted({row["source_height"] for row in ground}),
            "ground_flag_input_output_states":sorted({(row["feature_flags"],row["requested_offset"],row["resolved_offset"]) for row in ground}),
            "bank_callback_inputs":inputs,"bank_callback_outputs":sorted({row["resolved_offset"] for row in banks}),
            "ground_observed":bool(ground),"all_12_bank_inputs_observed":len(inputs) == 12,
            "all_height_and_ground_variants_verified":False,"animated_raised_water_ownership_verified":False,"geometry_approved":False})
assert len(matrix) == 20
summary = {"matrix":matrix,"prior_source_reconciliation":shared,
    "ground_selector_climates_observed":sum(row["ground_observed"] for row in matrix),
    "bank_input_selector_climates_observed":sum(len(row["bank_callback_inputs"]) for row in matrix),
    "all12_bank_input_selector_climates_observed":sum(row["all_12_bank_inputs_observed"] for row in matrix),
    "actual_absent_edge_features":sum(row["observed_actual_absent_features"] for row in matrix),
    "prior_common_owner_states_exact":sum(row["common_states_metadata_and_bytes_exact"] for row in shared),
    "new_wider_owner_states":sum(row["new_wider_states"] for row in shared),
    "selected_source_report_sha256":digest(wide_path),"prior_report_sha256":digest(prior_path),"approved_models":0,
    "scope":"An additive camera/source-selection audit on unchanged four original public-command saved worlds. Observed natural flat/NE/SE/SW/NW selectors, source heights and bank input/output combinations are stated individually, with prior common owners matching exact metadata and source bytes. Source feature/input breadth does not establish every hypothetical height/neighbourhood/flags/callback/custom family or source ownership/3D geometry/animation/phases/ships/performance/8+ quality. Missing combinations remain unresolved, not intentional absences; real zero-base execution is required for absence."}
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({key:value for key,value in summary.items() if key not in ("matrix","prior_source_reconciliation")}))

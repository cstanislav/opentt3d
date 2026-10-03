"""Keep a per-climate feature/input/height matrix; source breadth is never 3D approval."""
from pathlib import Path
import hashlib, json

root = Path("build-macos")
prefix = "breadth-original-river-natural-selector"
out = root / (prefix+"-matrix.json")
assert not out.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
report_path = root / (prefix+"-verification.json")
report = json.loads(report_path.read_text())
assert report["quiet_native_controls"] == 40 and report["strict_world_images"] == 20
assert report["strict_world_changed_pixels"] == report["approved_models"] == 0
matrix = []
for family,worlds in report["selected_sources"].items():
    for climate in ("temperate","arctic","tropic","toyland"):
        sources = [value for name,value in worlds.items() if name.startswith(climate+"-seed")]
        assert sources and all(not value["geometry_or_quality_approved"] for value in sources)
        ground = [row for value in sources for row in value["ground_sources"]]
        banks = [row for value in sources for row in value["edge_sources"]]
        absent = [row for value in sources for row in value["absent_edge_features"]]
        slopes = sources[0]["slope_source_values"]
        for name,slope in slopes.items():
            grounds = [row for row in ground if row["slope"] == slope]
            edges = [row for row in banks if row["slope"] == slope]
            matrix.append({"base_set_family":family,"climate":climate,"slope_name":name,"slope_value":slope,
                "ground_owner_states":len(grounds),"bank_owner_states":len(edges),
                "ground_selector_observed":bool(grounds),"original_source_heights":sorted({row["source_height"] for row in grounds}),
                "ground_feature_flag_input_output":sorted({(row["feature_flags"],row["requested_offset"],row["resolved_offset"]) for row in grounds}),
                "bank_callback_inputs":sorted({row["requested_offset"] for row in edges}),
                "bank_callback_input_output":sorted({(row["requested_offset"],row["resolved_offset"]) for row in edges}),
                "selected_ground_sources":len({(row["selected_sprite"],row["source_image_sha256"]) for row in grounds}),
                "selected_bank_sources":len({(row["selected_sprite"],row["source_image_sha256"]) for row in edges}),
                "actual_absent_edge_features":sum(row["slope"] == slope for row in absent),
                "all_heights_ground_variants_or_custom_families_verified":False,"raised_animated_water_ownership_verified":False,
                "geometry_or_quality_approved":False})
assert len(matrix) == 40
assert all(row["ground_selector_observed"] for row in matrix)
for family in ("classic","opengfx"):
    rows = [row for row in matrix if row["base_set_family"] == family]
    assert len(rows) == 20 and sum(row["ground_owner_states"] for row in rows) == report["ground_owner_states_exact_per_base_set"]
    assert sum(row["bank_owner_states"] for row in rows) == report["bank_owner_states_exact_per_base_set"]
summary = {"matrix":matrix,"public_surveys":report["public_read_only_surveys"],"quiet_native_controls":40,
    "ground_selector_climates_observed_per_base_set":20,
    "bank_input_selector_climates_observed_per_base_set":{family:sum(len(row["bank_callback_inputs"]) for row in matrix if row["base_set_family"] == family)
        for family in ("classic","opengfx")},
    "original_source_heights_observed":sorted({height for row in matrix for height in row["original_source_heights"]}),
    "actual_absent_edge_features":sum(row["actual_absent_edge_features"] for row in matrix),
    "full_bank_inputs_or_heights_verified":False,"strict_world_changed_pixels":0,"approved_models":0,
    "selected_source_report_sha256":digest(report_path),"scope":report["scope"]}
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({key:value for key,value in summary.items() if key != "matrix"}))

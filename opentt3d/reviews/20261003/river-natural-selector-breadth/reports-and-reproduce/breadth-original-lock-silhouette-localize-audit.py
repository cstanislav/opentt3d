"""Bind the rejected pixels to actual immutable source triangles, not an image mask."""
from pathlib import Path
import hashlib, json, subprocess

root = Path("build-macos")
out = root / "breadth-original-lock-silhouette-localize-verification.json"
assert not out.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
localized = json.loads((root / "breadth-original-lock-silhouette-localize.json").read_text())
rejected = json.loads((root / "breadth-original-lock-front-profile-strict.json").read_text())
assert len(rejected["differences"]) == 8 and rejected["images"] == 432
cases = localized["observed_model_camera_mesh_cases"]
assert len(cases) == 4 and localized["runtime_source_or_artwork_changed"] is False
rows = []
for case in cases:
    candidate = case["nearby_front_triangles"]
    assert len(candidate) == 1 and candidate[0]["palette"] == 1
    triangle = candidate[0]
    assert not triangle["strictly_inside_unrounded"]
    distances = triangle["signed_inside_edge_distances_pixels"]
    assert sum(value < 0 for value in distances) == 1
    assert all(row["edge_functions"][1] == 0 and not row["strictly_inside"] for row in triangle["snapping_hypotheses"])
    for state in ("sea","elevated"):
        name = case["model"].removesuffix("_sea")+"_"+state
        record = next(row for row in rejected["differences"] if row["name"] == "model-voxel-"+name+"-"+str(case["view"]))
        assert record["changed_pixels"] == 1 and record["actual_rgba"] == [16,16,16,255] and record["reference_rgba"] == [133,178,219,255]
        assert [value+0.5 for value in record["first_pixel"]] == case["pixel_centre"]
        rows.append({"model":name,"view":case["view"],"pixel":record["first_pixel"],"candidate_triangle":triangle["triangle"],
            "palette":1,"candidate_has_one_outside_edge_before_rounding":True,"snapped_edge_is_exact_horizontal_tie":True,
            "unrounded_signed_edge_distance_pixels":min(distances),"repair_accepted":False})
catalogue = root / "breadth-original-lock-front-profile-frozen-build/baseset/opentt3d-voxels.json"
manifest = json.loads((catalogue.parent.parent / "manifest.json").read_text())
assert digest(catalogue) == manifest["catalogue_sha256"]
summary = {"cases":rows,"unchanged_model_catalogue_sha256":digest(catalogue),"rejected_strict_report_sha256":digest(root / "breadth-original-lock-front-profile-strict.json"),
    "mesh_and_camera_source_sha256":{name:digest(Path(name)) for name in ("src/renderer3d/voxel_geometry.hpp","src/renderer3d/camera.hpp","src/renderer3d/geometry.hpp")},
    "diagnostic_source_sha256":digest(root / "breadth-original-lock-silhouette-localize.cpp"),
    "diagnostic_binary_sha256":digest(root / "breadth-original-lock-silhouette-localize"),"raw_report_sha256":digest(root / "breadth-original-lock-silhouette-localize.json"),
    "build_log_sha256":digest(root / "breadth-original-lock-silhouette-localize-build.log"),"masks":False,"tolerance":0,"geometry_approvals":0,
    "scope":"Eight existing rejected pixel differences localize to one palette1 bottom-face triangle per direction/owner, sampled just outside an unsnapped horizontal edge. Hypothetical fixed subpixel grids make that edge an exact sample tie, consistent with differing fill-origin conventions; actual GPU clip outputs/fill rules remain a hypothesis until independent render tests. The0.02pixel search radius only locates candidates and is never a rendered/comparison tolerance, acceptance mask or coordinate adjustment. All immutable cells/mesh coordinates/cameras remain unchanged."}
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"rejected_pixels_localized":len(rows),"diagnostic_only":True,"comparison_tolerance":0,"geometry_approvals":0}))

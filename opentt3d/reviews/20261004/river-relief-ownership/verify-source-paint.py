"""Prove original-layer ownership and reconstruct all original PAM bytes, not a mask."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compact_reviews import load_pam


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def resolved(raw,components):
    r,g,b,a,m = raw
    if not m: return [r,g,b,a]
    mapped = components["palette_mapping"][m]
    if not mapped: return [0,0,0,0]
    colour = components["palette_rgba"][mapped]
    brightness = max(r,g,b) or 128
    values = [value*brightness//128 for value in colour[:3]]
    over = sum(max(0,value-255) for value in values)//2
    return [255 if value >= 255 else min(255,value+over*(255-value)//256) for value in values]+[a]


def main():
    report = HERE / "resolved-source-paint.json"
    if report.exists(): raise ValueError("Retain the previous source proof")
    original = json.loads((HERE / "original-layer-ownership.json").read_text())
    material = json.loads((HERE / "water-source-study-complete-owners/source-material-index.json").read_text())
    assignments,totals,source_proofs = [],Counter(),[]
    for row in material:
        label = row["source"]["climate_name"]+"-"+row["source"]["slope_name"].lower()
        raw_path = HERE / "water-source-study" / (label+"-source-components.json")
        original_path = HERE / "water-source-study" / (label+"-source.pam")
        components = json.loads(raw_path.read_text())
        header,size,pixels = load_pam(original_path)
        payload = bytes(value for raw in components["pixels"] for value in resolved(raw,components))
        assert payload == pixels and digest(original_path) == hashlib.sha256(header+payload).hexdigest()
        assert row["pixels"] == components["pixels"]
        visible = 0
        for a,b,owner in zip(row["pixels"],row["water_pixels"],row["owners"]):
            if owner != 2:
                assert a == b; visible += int(owner == 1)
        previous = next(value for value in original if value["source"]["climate"] == row["climate"] and value["source"]["slope"] == row["slope"])
        for pixel in previous["undecided_pixels_from_prior"]:
            x,y = pixel["screen_xy"]
            u,v = x-row["source"]["native_offset"][0],y-row["source"]["native_offset"][1]
            index = v*size[0]+u; owner = row["owners"][index]
            assert (owner == 2) == (pixel["layer_owner"] == "relief")
            totals[pixel["layer_owner"]] += 1
            assignments.append({**pixel,"climate":row["climate"],"slope":row["slope"],"native_xy":[u,v],
                "actual_original_components":components["pixels"][index],"actual_original_rgba":resolved(components["pixels"][index],components),
                "independent_water_components":row["water_pixels"][index],"verified_against_runtime_components":True,
                "original_source_components_sha256":digest(raw_path),"original_pam_sha256":digest(original_path),
                "comparison_mask":False,"quality_approved":False})
        source_proofs.append({"climate":row["climate"],"slope":row["slope"],"source_pam":str(original_path.relative_to(ROOT)),
            "source_components":str(raw_path.relative_to(ROOT)),"source_pam_sha256":digest(original_path),
            "source_components_sha256":digest(raw_path),"complete_original_pam_reconstructed":True,
            "visible_original_water_components_unchanged":visible,"retained_lower_layer_pixels":row["original_hidden_water_pixels_retained"]})
    assert len(assignments) == 17 and totals == {"relief":10,"water":7}
    value = {"original_sources":source_proofs,"previously_undecided_pixels":assignments,"resolved_counts":dict(totals),
        "undecided_pixels_in_this_eight_source_study":0,"visible_original_water_pixels_exact":sum(row["visible_original_water_components_unchanged"] for row in source_proofs),
        "original_pam_reconstructions":8,"original_callback_or_phase_rgb_used_to_infer_indices":False,
        "hidden_original_authoring_paint_not_hidden_compiled_dither_bytes":True,"geometry_approvals":0,
        "scope":"Lossless eight-source semantic paint proof only; not custom, theoretical, independent phase, bank, terrain/ship, runtime quality or performance acceptance."}
    report.write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({"original_pam_reconstructions":8,"resolved_relief_pixels":10,"resolved_water_pixels":7,
                      "visible_water_pixels_exact":value["visible_original_water_pixels_exact"],"approvals":0}))


if __name__ == "__main__": main()

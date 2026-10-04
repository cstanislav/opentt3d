"""Retain original Toyland pale/yellow ownership differences between corner directions."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    target = HERE / "paint-repaired-authored-source.json"
    if target.exists(): raise ValueError("Retain the previous pale-centre/pale-end mismatch")
    spec = importlib.util.spec_from_file_location("bank_author",HERE / "author-revised-models.py")
    author = importlib.util.module_from_spec(spec); spec.loader.exec_module(author)
    prior = HERE / "snow-repaired-authored-source.json"; data = json.loads(prior.read_text())
    # Original pale caps contain warm off-white, not the rejected pure-white strip.
    data["materials"]["toyland_pale"] = [13,169,12,169,28,169]
    data["materials"]["toyland_pale_shade"] = [12,14,11,14,28,14]
    for edge in (5,7,9):
        model = data["models"][f"river_bank_study_toyland_flat_{edge:02d}"]
        # Keep all polygon plans/soil/grass grain; replace only the wrong paint.
        model["ops"] = [op for op in model["ops"] if op[1] not in ("toyland_pale","toyland_pale_shade")]
        patches = ([0,42,2,4,49,4],[14,61,2,23,64,4]) if edge < 8 else ([0,53,2,3,57,4],[2,62,2,4,64,4])
        for bounds in patches: model["ops"].append(["paint","toyland_pale",*author.region(bounds,edge%4)])
        model["ops"].append(["scatter_paint","toyland_pale_shade",5,173205+edge,0,0,1,64,64,4,"toyland_pale",[2,2,1]])
        model["reference"] += " This source retains a yellow middle with distinct pale ends; the earlier incorrectly rotated central pale patch is rejected. Patch geometry/paint remains manually authored and provisional."
    data["reference"] += " All twelve Toyland owners have warmer manually authored pale paint; directions5/7/9 retain yellow centres and pale ends rather than inheriting the other directions' cap ownership. Geometry remains unchanged; independent source reviews are required."
    target.write_text(json.dumps(data,indent=2)+"\n")
    receipt = {"prior_source_sha256":hashlib.sha256(prior.read_bytes()).hexdigest(),
        "paint_repaired_source_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "changed_paint_climate":"toyland","cap_patch_ownership_reauthored_edges":[5,7,9],
        "geometry_change_permitted":False,"originals_preserved":True,"runtime_bindings":0,"quality_approvals":0}
    (HERE / "toyland-paint-authoring-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__ == "__main__": main()

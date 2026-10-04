"""Repair two actual snow-painted source owners without changing any bank geometry."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    target = HERE / "snow-repaired-authored-source.json"
    if target.exists(): raise ValueError("Retain the ordinary-paint mismatch and all prior art")
    spec = importlib.util.spec_from_file_location("revised_bank_author",HERE / "author-revised-models.py")
    author = importlib.util.module_from_spec(spec); spec.loader.exec_module(author)
    source = HERE / "revised-authored-source.json"; data = json.loads(source.read_text())
    data["materials"].update({"observed_snow":[212,210,160,161,28,161],
        "observed_snow_light":[161,210,212,210,28,210],"observed_snow_grain":[135,14,23,14,28,14]})
    names = []
    for edge in (5,6):
        name = f"river_bank_study_arctic_flat_{edge:02d}"; names.append(name)
        model = data["models"][name]
        model["ops"].extend([["paint","observed_snow",0,0,0,64,64,4],
            ["scatter_paint","observed_snow_light",3,223606+edge,0,0,0,64,64,4,"observed_snow",[2,2,2]],
            ["scatter_paint","observed_snow_grain",11,244949+edge,0,0,0,64,64,4,"observed_snow",[1,2,1]]])
        if edge == 6:
            model["ops"].append(["paint","arctic_soil_light",*author.region([0,40,0,8,46,1],edge%4)])
        model["reference"] += " The retained actual source is snow-painted; this owner has a separate manually painted snow return/cap from its exact visible DOS colours. The earlier ordinary-paint mismatch is rejected, not deleted. No all-snow-line/terrain-type/parameter state coverage is inferred."
    data["reference"] += " Two observed Arctic snow-painted owners corrected without changing occupied cells, dimensions or anchors; other forty-six model volumes/paints remain exact."
    target.write_text(json.dumps(data,indent=2)+"\n")
    receipt = {"revised_authored_source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "snow_repaired_source_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),"paint_changed_models":names,
        "geometry_change_permitted":False,"observed_snow_sources":2,"remaining_snow_variants_accepted":0,
        "visible_dos_colour_receipt":"snow-source-visible-colours.json","canonical_bindings_changed":False,"quality_approvals":0}
    (HERE / "snow-repair-authoring-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__ == "__main__": main()

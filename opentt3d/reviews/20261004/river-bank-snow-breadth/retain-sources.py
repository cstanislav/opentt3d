"""Retain twenty actually selected above-sea-level Arctic snow-painted owners."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from PIL import Image,ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = ROOT / "opentt3d/reviews/20261003/river-natural-selector-breadth/source-file-map.json"
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import image
OFFSETS = tuple(range(12))+(12,14,25,27,37,39,48,50)


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    target = HERE / "sources"
    if target.exists(): raise ValueError("Retain earlier snow-source observations")
    target.mkdir(); rows = json.loads(PRIOR.read_text()); retained = []; observations = {}
    for offset in OFFSETS:
        choices = [row for row in rows if row["base_set_family"] == "classic" and row["backend"] == "vulkan" and row["climate"] == "arctic"
            and row["feature"] == "CF_RIVER_EDGE" and row["requested_offset"] == row["resolved_offset"] == offset and row["source_height"] > 0]
        entry = max(choices,key=lambda row:row["source_height"])
        selector = Path(entry["original_image"]).parent / "river-selectors.json"
        if selector not in observations: observations[selector] = json.loads(selector.read_text())["observations"]
        source = next(row for row in observations[selector] if row["feature"] == "CF_RIVER_EDGE" and row["tile"] == entry["tile"]
            and row["requested_offset"] == row["resolved_offset"] == offset)
        expected = 0 if offset < 12 else {12:6,24:12,36:3,48:9}[offset//12*12]
        assert source["slope"] == expected and source["climate"] == 1 and source["base_set"] == "OpenGFX2 Classic"
        assert source["source_height"] > 0 and source["offset_callback"] and not source["absent"] and source["feature_flags"] == 0
        assert all(value%4 == 0 for value in source["source_offset"]+source["source_size"])
        original = ROOT / entry["portable_image"]; assert digest(original) == entry["sha256"]
        picture = image(original); assert list(picture.size) == [value//4 for value in source["source_size"]]
        assert picture.getchannel("A").getbbox()
        path = target / f"arctic-snow-offset{offset:02d}.pam"; shutil.copy2(original,path)
        retained.append({**source,"source_state":"observed-above-sea-level-snow-paint","native_offset":[value//4 for value in source["source_offset"]],
            "native_size":list(picture.size),"source_pam":str(path.relative_to(ROOT)),"source_pam_sha256":digest(path),
            "original_selection_provenance":entry,"prior_source_file_map_sha256":digest(PRIOR),"actual_selector_sha256":digest(selector),
            "public_terrain_type_query_performed":False,"quality_approved":False,
            "scope":"One actual selected Arctic snow-painted bank at this tile/height. Neither all snowline transitions, terrain-type callback inputs, shore/desert/grass/grid parameters, custom/incomplete/absence states nor water phases are accepted."})
    assert len(retained) == 20
    (HERE / "actual-source-index.json").write_text(json.dumps(retained,indent=2)+"\n")
    for kind,selected in (("flat",retained[:12]),("sloped",retained[12:])):
        canvas = Image.new("RGB",(1200,320*((len(selected)+3)//4)),(38,39,47)); draw = ImageDraw.Draw(canvas)
        for slot,row in enumerate(selected):
            x,y = slot%4*300,slot//4*320
            draw.text((x+8,y+8),f"Arctic offset{row['requested_offset']} slope{row['slope']} @ {row['native_offset']}",fill="white")
            draw.text((x+8,y+26),f"Actual height{row['source_height']}; complete original, display7x",fill="white")
            picture = image(ROOT / row["source_pam"]); picture = picture.resize((picture.width*7,picture.height*7),Image.Resampling.NEAREST)
            canvas.paste(picture,(x+8,y+60),picture)
        canvas.save(HERE / ("original-snow-"+kind+"-owners.png"))
    value = {"retained_utc":datetime.now(timezone.utc).isoformat(),"actual_selected_snow_paint_owners":20,"flat_owners":12,"sloped_owners":8,
        "source_heights":[row["source_height"] for row in retained],"terrain_type_queries_or_all_snowline_states_accepted":False,
        "complete_source_rgba_retained":True,"source_geometry_extruded_traced_or_fitted":False,"runtime_bank_coverage_accepted":0,"quality_approvals":0}
    (HERE / "source-retention-receipt.json").write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value))


if __name__ == "__main__": main()

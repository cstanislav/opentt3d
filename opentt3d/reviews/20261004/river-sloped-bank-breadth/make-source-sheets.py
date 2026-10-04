"""Magnify complete original selected bank images for manual inspection only."""
import json
from pathlib import Path
import sys
from PIL import Image,ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import image


def main():
    target = HERE / "original-source-sheets"
    if target.exists(): raise ValueError("Retain earlier original source presentations")
    target.mkdir(); rows = json.loads((HERE / "actual-source-index.json").read_text())
    for climate,label in enumerate(("temperate","arctic","tropic","toyland")):
        canvas = Image.new("RGB",(1200,640),(38,39,47)); draw = ImageDraw.Draw(canvas)
        sources = [row for row in rows if row["climate"] == climate]; assert len(sources) == 8
        for slot,row in enumerate(sources):
            x,y = slot%4*300,slot//4*320
            draw.text((x+8,y+8),f"{label} {row['direction']} edge{row['edge']} @ {row['native_offset']}",fill="white")
            draw.text((x+8,y+25),f"height{row['source_height']} — {row['source_state']}",fill="white")
            original = image(ROOT / row["source_pam"]); enlarged = original.resize((original.width*7,original.height*7),Image.Resampling.NEAREST)
            canvas.paste(enlarged,(x+8,y+60),enlarged)
        canvas.save(target / (label+"-eight-actual-owners.png"))
    print(json.dumps({"complete_originals_presented":32,"display_scale":7,"pixels_changed_in_evidence":False,"model_geometry_derived":False,"quality_approvals":0}))


if __name__ == "__main__": main()

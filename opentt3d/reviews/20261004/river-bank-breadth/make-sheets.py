"""Keep the original native source/tile anchor beside eight independent model views."""
import argparse
import json
from pathlib import Path
import sys
from PIL import Image,ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures,image
from contact_sheet import compose_registered
from object_review import registered_native,equal_scale_pair,tight_thumbnail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision",choices=("initial","revised"),default="initial")
    args = parser.parse_args()
    target = HERE / (args.revision+"-sheets")
    if target.exists(): raise ValueError("Retain previous model sheets")
    target.mkdir(); rows = []
    for source in json.loads((HERE / "actual-source-index.json").read_text()):
        climate = ("temperate","arctic","tropic","toyland")[source["climate"]]; edge = source["requested_offset"]
        name = f"river_bank_study_{climate}_flat_{edge:02d}"
        directory = HERE / (args.revision+"-native-controls") / f"breadth-original-river-bank-{args.revision}-{climate}-vulkan-study/renderer3d-reference"
        frames = captures(directory,"model-voxel-"+name+"-*")
        assert len(frames) == 9
        prefix = "model-voxel-"+name
        original = compose_registered([(image(ROOT / source["source_pam"]),*source["native_offset"])])
        registration = directory / (prefix+"-native.json")
        native = registered_native(frames[prefix+"-native"],json.loads(registration.read_text()))
        pair,bounds = equal_scale_pair(original,native)
        canvas = Image.new("RGB",(1200,620),(38,39,47)); draw = ImageDraw.Draw(canvas)
        draw.text((8,8),name+" — unbound "+args.revision+" volume; source dimensions/paint/state fidelity unaccepted",fill="white")
        for slot,(picture,title) in enumerate(zip(pair,("Actual selected original, 4x native","Candidate soil/low crest, same tile anchor, 4x native"))):
            x = slot*600+(600-picture.width)//2
            canvas.paste(picture,(x,60),picture); draw.text((slot*600+8,35),title,fill="white")
        for view in range(8):
            picture = tight_thumbnail(image(frames[prefix+f"-{view}"]),(285,175))
            x,y = view%4*300,220+view//4*190
            canvas.paste(picture,(x+(300-picture.width)//2,y+20+(175-picture.height)//2))
            draw.text((x+8,y),f"{'Orbit' if view < 4 else 'Street'} {view%4}",fill="white")
        path = target / (name+".png"); canvas.save(path)
        rows.append({"model":name,"climate":source["climate"],"edge":edge,"sheet":str(path.relative_to(ROOT)),
            "source":source["source_pam"],"source_sha256":source["source_pam_sha256"],"native_registration":str(registration.relative_to(ROOT)),
            "native_view":str(frames[prefix+"-native"].relative_to(ROOT)),"shared_bounds":bounds,"quality_approved":False})
    assert len(rows) == 48
    (target / "index.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps({"individual_model_sheets":48,"same_source_scale_and_anchor":True,"quality_approvals":0}))


if __name__ == "__main__": main()

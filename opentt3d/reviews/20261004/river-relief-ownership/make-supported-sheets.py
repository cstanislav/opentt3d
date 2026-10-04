"""Present original datum and supported relief separately at the same tile anchor."""
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
    target = HERE / "supported-model-sheets"
    if target.exists(): raise ValueError("Retain previous supported sheets")
    target.mkdir()
    records = []
    for climate,label in ((0,"temperate"),(3,"toyland")):
        gallery = HERE / "complete-water-world-controls" / f"breadth-original-river-relief-world-complete-water-{label}-271828-vulkan-complete-classic/renderer3d-reference"
        rendered = captures(gallery,"model-voxel-*")
        for slope,direction in ((3,"sw"),(6,"se"),(9,"nw"),(12,"ne")):
            name = "river_relief_study_"+("island" if climate == 3 else "rock")+"_"+direction
            source = HERE / "water-source-study" / f"{label}-{direction}-source.pam"
            native_source = image(source)
            source_offset = [-31,0 if slope in (3,6) else -8]
            original = compose_registered([(native_source,*source_offset)])
            base = "model-voxel-"+name; supported = f"model-voxel-river-supported-{slope}-{climate}"
            registrations = [gallery / (prefix+"-native.json") for prefix in (base,supported)]
            previews = [registered_native(rendered[prefix+"-native"],json.loads(path.read_text())) for prefix,path in zip((base,supported),registrations)]
            pair,bounds = equal_scale_pair(original,previews[0])
            support_pair,support_bounds = equal_scale_pair(original,previews[1])
            canvas = Image.new("RGB",(1200,600),(38,39,47)); draw = ImageDraw.Draw(canvas)
            draw.text((8,8),name+" — diagnostic support; not canonical artwork, an image fit or quality approval",fill="white")
            for slot,(picture,title) in enumerate(((pair[0],"Original undoubled water+relief source; 4x native"),
                (pair[1],"Authored relief only, original datum; 4x native"),(support_pair[1],"Same relief with extra column lift; 4x native"))):
                canvas.paste(picture,(slot*400+(400-picture.width)//2,55),picture)
                draw.text((slot*400+8,32),title,fill="white")
            for view in range(8):
                picture = tight_thumbnail(image(rendered[supported+f"-{view}"]),(285,190))
                x,y = view%4*300,200+view//4*200
                canvas.paste(picture,(x+(300-picture.width)//2,y+22+(190-picture.height)//2))
                draw.text((x+8,y+2),f"Supported {'orbit' if view < 4 else 'street'} {view%4}",fill="white")
            path = target / (name+".png"); canvas.save(path)
            records.append({"model":name,"climate":climate,"slope":slope,"sheet":str(path.relative_to(ROOT)),
                "source":str(source.relative_to(ROOT)),"original_native_registration":str(registrations[0].relative_to(ROOT)),
                "supported_native_registration":str(registrations[1].relative_to(ROOT)),"source_and_original_shared_bounds":bounds,
                "source_and_supported_shared_bounds":support_bounds,"source_geometry_height_fidelity_accepted":False,
                "diagnostic_bound_only":True,"quality_approved":False})
    (target / "index.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps({"individual_supported_owner_sheets":8,"quality_approvals":0}))


if __name__ == "__main__": main()

"""Retain original authoring layers and inspect unresolved pixels without fitting geometry."""
import hashlib
import json
from pathlib import Path
import re
import sys
import pypdn
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "river-relief-breadth"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / "original-layers"
    if target.exists(): raise ValueError("Retain previous layer extraction")
    target.mkdir()
    documents = []
    for source in sorted((HERE / "upstream").glob("*.pdn")):
        document = pypdn.read(str(source))
        directory = target / source.stem
        directory.mkdir()
        layers = []
        for index,layer in enumerate(document.layers):
            name = f"{index:02d}-"+re.sub(r"[^a-z0-9]+","-",layer.name.lower()).strip("-")+".png"
            path = directory / name
            Image.fromarray(layer.image).save(path)
            layers.append({"name":layer.name,"index":index,"visible":layer.visible,"opacity":layer.opacity,
                           "blend_mode":int(layer.blendMode),"image":str(path.relative_to(ROOT)),"sha256":digest(path)})
        documents.append({"source":str(source.relative_to(ROOT)),"source_sha256":digest(source),
                          "size":[document.width,document.height],"layers":layers})
    rows = []
    offsets = {3:81,6:161,9:241,12:321}
    for row in json.loads((PRIOR / "source-paint-separation-corrected/index.json").read_text()):
        source = row["source"]
        document = next(value for value in documents if value["source"].endswith(
            ("toyland" if source["climate"] == 3 else "universal")+"_rivertiles_32bpp.pdn"))
        relief = next(value for value in document["layers"] if value["name"] == ("Rocks" if source["climate"] == 3 else "Rocks Unshaded"))
        with Image.open(ROOT / relief["image"]) as image:
            assignments = []
            for pixel in row["undecided_pixels"]:
                x,y = pixel["screen_xy"]
                u,v = x-source["native_offset"][0],y-source["native_offset"][1]
                sheet_xy = [offsets[source["slope"]]+u,1+v]
                rgba = list(image.getpixel(tuple(sheet_xy)))
                assignments.append({**pixel,"sheet_xy":sheet_xy,"original_relief_layer_rgba":rgba,
                                    "layer_owner":"relief" if rgba[3] else "water",
                                    "verified_against_runtime_components":False})
        rows.append({"source":source,"relief_layer":relief,"crop_xy":[offsets[source["slope"]],1],
                     "undecided_pixels_from_prior":assignments,"runtime_binding_allowed":False})
    (HERE / "original-layer-index.json").write_text(json.dumps(documents,indent=2)+"\n")
    (HERE / "original-layer-ownership.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps({"original_layer_documents":len(documents),"layer_images":sum(len(value["layers"]) for value in documents),
                     "prior_undecided_pixels_traced":sum(len(row["undecided_pixels_from_prior"]) for row in rows),
                     "runtime_binding_allowed":False,"approvals":0}))


if __name__ == "__main__": main()

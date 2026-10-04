"""Explicit small soil/grassy bank volumes; no source pixel becomes a voxel."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Tile-local quarter-unit authoring coordinates. Each crest has an explicit
# irregular plan; the ordinary tile centre and water remain entirely empty.
SIDE = [[0,0],[4,0],[4,6],[5,6],[5,10],[3,10],[3,16],[5,16],[5,22],[4,22],
    [4,28],[6,28],[6,32],[4,32],[4,40],[5,40],[5,46],[3,46],[3,52],[5,52],
    [5,58],[4,58],[4,64],[0,64]]
OUTER = [[0,54],[2,54],[2,56],[4,56],[4,58],[6,60],[8,60],[8,62],[10,62],[10,64],[0,64]]
INNER = [[0,57],[2,58],[2,60],[4,60],[4,62],[7,64],[0,64]]

# Original DOS palette entries individually inspected in actual source paint.
# These are an authored approximation, not colour fitting or phase inference.
PALETTES = {
    "temperate": {"earth":[28,29,28,29,27,29],"grass":[89,90,88,89,28,82],"grass_grain":[90,91,89,90,28,83],"stone":[28,30,28,30,27,31]},
    "arctic": {"earth":[28,29,28,29,27,29],"grass":[33,34,24,25,28,34],"grass_grain":[34,35,25,26,28,26],"stone":[28,30,28,30,27,31]},
    "tropic": {"earth":[28,29,28,29,27,29],"grass":[89,91,88,90,28,90],"grass_grain":[90,92,89,91,28,91],"stone":[28,30,28,30,27,31]},
    "toyland": {"earth":[58,59,37,38,28,39],"grass":[63,65,64,65,28,65],"grass_grain":[64,66,65,66,28,64],"stone":[9,12,8,11,7,13]},
}


def turn(points,count):
    for _ in range(count): points = [[y,64-x] for x,y in points]
    return points


def main():
    path = HERE / "authored-source.json"
    if path.exists(): raise ValueError("Retain earlier geometry authoring")
    sources = json.loads((HERE / "actual-source-index.json").read_text())
    materials,models = {},{}
    for climate,(label,paints) in enumerate(PALETTES.items()):
        for kind,colours in paints.items(): materials[label+"_"+kind] = colours
        for edge in range(12):
            source = next(row for row in sources if row["climate"] == climate and row["requested_offset"] == edge)
            shape = SIDE if edge < 4 else OUTER if edge < 8 else INNER
            polygon = turn(shape,edge%4)
            # Independent soil and low grass strata share exactly the same
            # authored footprint. Face paint changes no occupied cells.
            ops = [["prism",label+"_earth",2,0,2,polygon],["prism",label+"_grass",2,2,4,polygon],
                ["scatter_paint",label+"_grass_grain",5,314159+edge,0,0,2,64,64,4,label+"_grass",[2,2,1]],
                ["scatter_paint",label+"_stone",13,271828+edge,0,0,0,64,64,2,label+"_earth",[1,2,1]]]
            if label == "toyland":
                # Original Toyland ground is yellow/pale, not ordinary grass.
                # Four explicit quarter-tile pale bands are paint-only; source
                # bands/patch shape still require an individual fidelity pass.
                for start,end in ((4,10),(19,24),(36,44),(53,59)):
                    ops.append(["face_paint",label+"_stone",32,0,start,2,64,end,4])
            name = f"river_bank_study_{label}_flat_{edge:02d}"
            models[name] = {"size":[64,64,4],"cell_size":[0.25,0.25,0.25],"origin":[0,0,0],
                "review_status":"unbound-source-study",
                "reference":f"Actual elevated Classic flat CF_RIVER_EDGE input/output {edge}, climate {climate}, source PAM SHA256 {source['source_pam_sha256']}. Manually authored soil/low crest candidate. Water/foam, original absent states, sloped/sea-level/snow/desert/parameter/custom families and world support are not modelled or approved. Width/height/registration/paint fidelity remain to be inspected; no runtime binding.",
                "ops":ops}
    value = {"format":1,"reference":"Forty-eight separately owned elevated flat river-bank volume studies only. Geometry is explicit tile-local authoring data, never sprite extrusion, raster fitting or water inpainting. Original sources/layers and rejected studies remain separate. This is not complete runtime bank coverage or quality approval.",
        "materials":materials,"models":models,"bindings":{}}
    assert len(models) == 48
    path.write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({"unbound_flat_bank_models":48,"climates":4,"owners_per_climate":12,"runtime_bindings":0,"quality_approvals":0}))


if __name__ == "__main__": main()

"""Hand-author bank toes, soil shelves and crests, retaining the rejected first pass."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Quarter-unit tile coordinates, not samples or an extrusion of the source image.
# Three nested plans give the bank a shallow eroded toe rather than a painted slab.
SIDE_TOE = [[0,0],[7,0],[7,5],[10,5],[10,9],[7,9],[7,17],[9,17],[9,22],[7,22],
    [7,29],[10,29],[10,33],[8,33],[8,40],[9,40],[9,46],[7,46],[7,52],[9,52],
    [9,57],[7,57],[7,64],[0,64]]
SIDE_SHELF = [[0,0],[5,0],[5,5],[7,5],[7,9],[5,9],[5,17],[7,17],[7,22],[5,22],
    [5,29],[7,29],[7,33],[6,33],[6,40],[7,40],[7,46],[5,46],[5,52],[7,52],
    [7,57],[5,57],[5,64],[0,64]]
SIDE_CREST = [[0,0],[3,0],[3,6],[5,6],[5,9],[3,9],[3,18],[5,18],[5,21],[3,21],
    [3,30],[5,30],[5,33],[4,33],[4,41],[5,41],[5,45],[3,45],[3,53],[5,53],
    [5,57],[3,57],[3,64],[0,64]]

# Both arms of the concave corner belong to this owner; neither is a full tile.
OUTER_TOE = [[0,40],[4,40],[6,44],[8,44],[8,50],[12,50],[12,54],[18,54],
    [20,58],[24,58],[24,64],[0,64]]
OUTER_SHELF = [[0,41],[3,41],[5,45],[6,45],[6,52],[10,52],[10,56],[16,56],
    [18,60],[23,60],[23,64],[0,64]]
OUTER_CREST = [[0,42],[2,42],[4,46],[4,54],[8,54],[8,58],[14,58],[16,62],
    [22,62],[22,64],[0,64]]
INNER_TOE = [[0,48],[4,48],[4,52],[6,52],[6,56],[10,56],[10,60],[14,60],
    [14,62],[4,64],[0,64]]
INNER_SHELF = [[0,49],[3,49],[3,53],[5,53],[5,57],[8,57],[8,61],[12,61],
    [12,62],[3,64],[0,64]]
INNER_CREST = [[0,54],[2,54],[2,57],[4,57],[4,60],[6,60],[6,62],[10,62],
    [2,64],[0,64]]
PLANS = ((SIDE_TOE,SIDE_SHELF,SIDE_CREST),(OUTER_TOE,OUTER_SHELF,OUTER_CREST),
    (INNER_TOE,INNER_SHELF,INNER_CREST))

# Globally lit six-face paints, individually inspected in the retained source.
# This is explicit authoring paint, not automatic RGB fitting or a water material.
PALETTES = {
    "temperate":{"soil":[28,30,28,29,27,29],"soil_light":[29,31,29,30,27,30],
        "soil_dark":[27,29,27,28,26,28],"grass":[89,91,88,90,28,82],
        "grass_light":[90,92,89,91,28,90],"grass_pale":[91,93,90,92,28,92]},
    "arctic":{"soil":[28,30,28,29,27,29],"soil_light":[29,31,29,30,27,30],
        "soil_dark":[27,29,27,28,26,28],"grass":[33,35,25,26,28,34],
        "grass_light":[89,92,89,91,28,26],"grass_pale":[90,93,90,92,28,92]},
    "tropic":{"soil":[28,30,28,29,27,29],"soil_light":[29,31,29,30,27,30],
        "soil_dark":[27,29,27,28,26,28],"grass":[89,91,88,90,28,90],
        "grass_light":[90,92,89,91,28,91],"grass_pale":[91,93,90,92,28,93]},
    "toyland":{"soil":[28,30,28,29,27,29],"soil_light":[29,31,29,30,27,30],
        "soil_dark":[27,29,27,28,26,28],"grass":[63,65,64,65,28,65],
        "grass_light":[64,66,65,66,28,66],"grass_pale":[65,67,66,67,28,67],
        "pale":[12,15,12,14,28,15],"pale_shade":[11,14,11,13,28,14]},
}


def turn(points,count):
    for _ in range(count): points = [[y,64-x] for x,y in points]
    return points


def region(bounds,count):
    x0,y0,z0,x1,y1,z1 = bounds
    corners = turn([[x0,y0],[x0,y1],[x1,y0],[x1,y1]],count)
    return [min(p[0] for p in corners),min(p[1] for p in corners),z0,
        max(p[0] for p in corners),max(p[1] for p in corners),z1]


def main():
    path = HERE / "revised-authored-source.json"
    if path.exists(): raise ValueError("Retain every earlier authoring pass")
    sources = json.loads((HERE / "actual-source-index.json").read_text())
    initial = HERE / "authored-source.json"
    materials,models = {},{}
    for climate,(label,paints) in enumerate(PALETTES.items()):
        for kind,colours in paints.items(): materials[label+"_"+kind] = colours
        for edge in range(12):
            source = next(row for row in sources if row["climate"] == climate and row["requested_offset"] == edge)
            family,rotation = edge//4,edge%4
            toe,shelf,crest = [turn(plan,rotation) for plan in PLANS[family]]
            ops = [["prism",label+"_soil",2,0,1,toe],["prism",label+"_soil",2,1,2,shelf],
                ["prism",label+"_grass",2,2,4,crest]]
            # Two-scale sediment/grass paint never creates a occupied voxel.
            ops.extend([["scatter_paint",label+"_soil_light",3,271828+edge,0,0,0,64,64,2,label+"_soil",[2,3,1]],
                ["scatter_paint",label+"_soil_dark",7,161803+edge,0,0,0,64,64,2,label+"_soil",[1,2,1]],
                ["scatter_paint",label+"_grass_light",3,314159+edge,0,0,2,64,64,4,label+"_grass",[2,3,2]],
                ["scatter_paint",label+"_grass_pale",7,141421+edge,0,0,2,64,64,4,label+"_grass",[1,2,2]]])
            if label == "toyland":
                # Irregular pale cap/return patches follow the owner's local arms.
                # Bounds rotate, while sunlight-facing paint remains globally lit.
                patches = ([(0,14,2,5,25,4),(0,20,2,3,29,4),(0,48,2,5,60,4),(0,56,2,3,64,4)] if family == 0 else
                    [(0,52,2,8,60,4),(2,56,2,14,64,4)] if family == 1 else [(0,53,1,7,62,4),(2,60,1,12,64,4)])
                for bounds in patches: ops.append(["paint",label+"_pale",*region(bounds,rotation)])
                # Mottle only existing pale volumes; no regular white stripe slabs.
                ops.append(["scatter_paint",label+"_pale_shade",5,173205+edge,0,0,1,64,64,4,label+"_pale",[2,2,1]])
            name = f"river_bank_study_{label}_flat_{edge:02d}"
            models[name] = {"size":[64,64,4],"cell_size":[0.25,0.25,0.25],"origin":[0,0,0],
                "review_status":"unbound-source-study",
                "reference":f"Separate actual elevated Classic flat CF_RIVER_EDGE input/output {edge}, climate {climate}, original SHA256 {source['source_pam_sha256']}. Hand-authored nested soil toe/shelf/low crest and corrected two-arm corner plan. Original height and tile datum are unchanged; source silhouette/face-paint fidelity is still provisional. No water, extra terrain support, runtime binding or sloped/sea-level/snow/desert/parameter/custom/absence acceptance.",
                "ops":ops}
    value = {"format":1,"reference":"Second retained bank authoring pass; all forty-eight owners remain separate and unbound. First geometry/native worlds/galleries are preserved. Explicit polygon plans and local paint boxes are not image extrusion, alpha tracing, source fitting or inpainting. Broader catalogue coverage remains unfinished.",
        "materials":materials,"models":models,"bindings":{}}
    path.write_text(json.dumps(value,indent=2)+"\n")
    receipt = {"initial_authored_source_sha256":hashlib.sha256(initial.read_bytes()).hexdigest(),
        "revised_authored_source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"models":48,
        "object_height_unchanged":1,"tile_origin_unchanged":[0,0,0],"canonical_bindings_changed":False,"quality_approvals":0}
    (HERE / "revision-authoring-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__ == "__main__": main()

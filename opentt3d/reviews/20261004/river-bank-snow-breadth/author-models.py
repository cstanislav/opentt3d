"""Hand-author twenty separate snowy bank volumes with original thin datums."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PALETTE = {
    "soil":[28,30,28,29,27,29],"soil_light":[29,31,29,30,27,30],"soil_dark":[27,29,27,28,26,28],
    "snow":[212,210,160,161,28,161],"snow_light":[161,210,212,210,28,210],
    "snow_shade":[160,161,153,212,28,212],"snow_grain":[135,14,23,14,28,14]
}
# Manual tile-local quarter-unit outlines: widened upper snowy shoulders, two
# independently occupied corner arms and smaller broken inner-corner snow lobes.
# These points are authoring geometry, never traced alpha/pixel positions.
SIDE = (
    [[0,0],[8,0],[8,6],[10,6],[10,11],[8,11],[8,18],[9,18],[9,24],[8,24],[8,32],[10,32],[10,37],[8,37],[8,45],[9,45],[9,50],[8,50],[8,57],[9,57],[9,61],[8,61],[8,64],[0,64]],
    [[0,0],[7,0],[7,5],[8,5],[8,11],[7,11],[7,19],[8,19],[8,24],[7,24],[7,32],[8,32],[8,37],[7,37],[7,45],[8,45],[8,50],[7,50],[7,58],[8,58],[8,62],[7,62],[7,64],[0,64]],
    [[0,0],[6,0],[6,6],[7,6],[7,10],[6,10],[6,19],[7,19],[7,23],[6,23],[6,32],[7,32],[7,36],[6,36],[6,45],[7,45],[7,49],[6,49],[6,58],[7,58],[7,61],[6,61],[6,64],[0,64]]
)
OUTER = (
    [[0,40],[5,40],[6,45],[9,45],[9,50],[13,50],[13,54],[18,54],[20,58],[24,58],[24,64],[0,64]],
    [[0,41],[4,41],[5,45],[8,46],[8,51],[12,51],[12,55],[17,55],[19,59],[23,59],[23,64],[0,64]],
    [[0,42],[3,42],[4,46],[6,46],[6,53],[10,53],[10,57],[16,57],[17,61],[22,61],[22,64],[0,64]]
)
INNER = (
    [[0,49],[4,49],[4,53],[6,53],[6,57],[10,57],[10,60],[14,60],[14,62],[4,64],[0,64]],
    [[0,50],[3,50],[3,54],[5,54],[5,58],[8,58],[8,61],[12,61],[12,62],[3,64],[0,64]],
    [[0,55],[2,55],[2,58],[4,58],[4,61],[7,61],[7,62],[9,62],[2,64],[0,64]]
)
SECTIONS = (0,8,16,24,32,40,48,56,64)
TOE = (8,9,8,10,9,8,10,9)
SHELF = (7,8,7,9,8,7,9,8)
SNOW = (6,7,6,8,7,6,8,7)


def turn(points,count):
    for _ in range(count): points = [[y,64-x] for x,y in points]
    return points


def section(slope,edge,start,end,width,bottom,thickness,material):
    longitudinal = 0 if slope in (3,12) else 1
    far = edge in (1,2); low,high = (64-width,64) if far else (0,width)
    height = lambda t: t//2 if slope in (3,6) else 32-t//2
    points = [[start,height(start)+bottom],[end,height(end)+bottom],
        [end,height(end)+bottom+thickness],[start,height(start)+bottom+thickness]]
    return ["prism",material,1-longitudinal,low,high,points]


def main():
    target = HERE / "authored-source.json"
    if target.exists(): raise ValueError("Retain earlier snowy bank authoring passes")
    models = {}
    for source in json.loads((HERE / "actual-source-index.json").read_text()):
        offset,slope = source["requested_offset"],source["slope"]
        if slope == 0:
            plans = (SIDE,OUTER,INNER)[offset//4]
            toe,shelf,cap = [turn(plan,offset%4) for plan in plans]
            ops = [["prism","soil",2,0,1,toe],["prism","soil",2,1,2,shelf],["prism","snow",2,2,4,cap]]
            size = [64,64,4]
        else:
            edge = offset%12; ops = []
            for index,(start,end) in enumerate(zip(SECTIONS,SECTIONS[1:])):
                ops.extend([section(slope,edge,start,end,TOE[index],0,1,"soil"),
                    section(slope,edge,start,end,SHELF[index],1,1,"soil"),
                    section(slope,edge,start,end,SNOW[index],2,2,"snow")])
            size = [64,64,36]
        # Local deterministic authoring paint, never the simulation RNG. Snow
        # coats only existing crest cells; bottom sediment is independently owned.
        ops.extend([["scatter_paint","soil_light",4,271828+offset,0,0,0,64,64,size[2],"soil",[2,3,1]],
            ["scatter_paint","soil_dark",11,161803+offset,0,0,0,64,64,size[2],"soil",[1,2,1]],
            ["scatter_paint","snow_light",3,314159+offset,0,0,0,64,64,size[2],"snow",[2,3,2]],
            ["scatter_paint","snow_shade",7,141421+offset,0,0,0,64,64,size[2],"snow",[3,2,1]],
            ["scatter_paint","snow_grain",19,173205+offset,0,0,0,64,64,size[2],"snow",[1,2,1]]])
        name = f"river_bank_snow_study_arctic_offset{offset:02d}"
        models[name] = {"size":size,"cell_size":[0.25,0.25,0.25],"origin":[0,0,0],"review_status":"unbound-source-study",
            "reference":f"Independent actual snow-painted Classic CF_RIVER_EDGE input/output {offset}, Arctic tile {source['tile']} at original source height {source['source_height']}, slope {slope}; complete original PAM SHA256 {source['source_pam_sha256']}. Manually authored soil toe/shelf and wider snow crest/corner arms remain thin (four quarter-unit cells), at the original tile datum. The original undoubled slope is separate from any future extra displayed terrain support. Explicit snow grain/face paint is not a source fit or image extrusion. No water geometry, blue wave reclassification, runtime binding, all snowline/terrain-type/parameter/custom/absence/phase/LOD/support/ship acceptance or quality approval.",
            "ops":ops}
    assert len(models) == 20
    value = {"format":1,"reference":"Twenty distinct observed snow-painted bank owners add state breadth to the full catalogue goal, not a replacement narrowed target. All canonical art and earlier80 unbound banks remain unchanged. Original complete sources and all later failures are retained. Hand-authored original-datum volumes, never alpha extrusion, image fitting or animation-water voxelisation; all runtime/state/quality gates remain unaccepted.",
        "materials":PALETTE,"models":models,"bindings":{}}
    target.write_text(json.dumps(value,indent=2)+"\n")
    receipt = {"models":20,"flat_models":12,"sloped_models":8,"maximum_bank_thickness_cells":4,
        "original_sloped_rise_cells":32,"extra_doubled_terrain_support_authored":False,"water_materials_or_geometry_authored":False,
        "source_geometry_sampled_traced_or_fitted":False,"authored_source_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),"runtime_bindings":0,"quality_approvals":0}
    (HERE / "authoring-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt))


if __name__ == "__main__": main()

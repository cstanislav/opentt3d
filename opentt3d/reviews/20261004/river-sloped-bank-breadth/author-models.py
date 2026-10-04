"""Manually author thin eroded banks on the original four undoubled river planes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLAT = HERE.parent / "river-bank-breadth"

# Explicit longitudinal quarter-unit sections, not sampled source pixels/alpha.
SECTIONS = [0,8,16,24,32,40,48,56,64]
TOE = [6,7,6,8,7,6,8,7]
SHELF = [4,5,4,6,5,4,6,5]
CREST = [3,4,3,4,4,3,5,4]
PLANES = {3:(0,1),6:(1,1),9:(1,-1),12:(0,-1)}


def height(slope,coordinate):
    # An original half-unit rise per tile-local unit. Extra displayed terrain
    # support is NOT authored here and never scales the four-cell bank thickness.
    return coordinate//2 if PLANES[slope][1] > 0 else 32-coordinate//2


def section(slope,edge,start,end,width,bottom,thickness,material):
    longitudinal,sign = PLANES[slope]; across = 1-longitudinal
    far = edge in (1,2)
    low,high = (64-width,64) if far else (0,width)
    outline = [[start,height(slope,start)+bottom],[end,height(slope,end)+bottom],
        [end,height(slope,end)+bottom+thickness],[start,height(slope,start)+bottom+thickness]]
    return ["prism",material,across,low,high,outline]


def paint_region(slope,edge,start,end,width):
    axis = PLANES[slope][0]; far = edge in (1,2)
    low,high = (64-width,64) if far else (0,width)
    return [start,low,0,end,high,36] if axis == 0 else [low,start,0,high,end,36]


def main():
    target = HERE / "authored-source.json"
    if target.exists(): raise ValueError("Retain every earlier sloped bank authoring pass")
    flat_path = FLAT / "paint-repaired-authored-source.json"
    materials = json.loads(flat_path.read_text())["materials"]
    sources = json.loads((HERE / "actual-source-index.json").read_text()); models = {}
    for source in sources:
        slope,edge,climate = source["slope"],source["edge"],source["climate"]
        label = ("temperate","arctic","tropic","toyland")[climate]
        assert (slope in (3,12) and edge in (1,3)) or (slope in (6,9) and edge in (0,2))
        ops = []
        for index,(start,end) in enumerate(zip(SECTIONS,SECTIONS[1:])):
            ops.extend([section(slope,edge,start,end,TOE[index],0,1,label+"_soil"),
                section(slope,edge,start,end,SHELF[index],1,1,label+"_soil"),
                section(slope,edge,start,end,CREST[index],2,2,label+"_grass")])
        # Independently painted exposed sediment and turf: no occupied cell is
        # created by grain, face painting or the irregular Toyland cap patches.
        seed = 271828+source["requested_offset"]+climate*100
        ops.extend([["scatter_paint",label+"_soil_light",3,seed,0,0,0,64,64,36,label+"_soil",[2,3,1]],
            ["scatter_paint",label+"_soil_dark",7,seed+161803,0,0,0,64,64,36,label+"_soil",[1,2,1]],
            ["scatter_paint",label+"_grass_light",3,seed+314159,0,0,0,64,64,36,label+"_grass",[2,3,2]],
            ["scatter_paint",label+"_grass_pale",7,seed+141421,0,0,0,64,64,36,label+"_grass",[1,2,2]]])
        if label == "toyland":
            patches = ((12,24),(46,58)) if edge in (0,3) else ((5,17),(36,49))
            for start,end in patches:
                ops.append(["face_paint","toyland_pale",32,*paint_region(slope,edge,start,end,5)])
        name = f"river_bank_slope_study_{label}_{source['direction']}_edge{edge:02d}"
        models[name] = {"size":[64,64,36],"cell_size":[0.25,0.25,0.25],"origin":[0,0,0],
            "review_status":"unbound-source-study",
            "reference":f"Separate actual Classic CF_RIVER_EDGE input/output {source['requested_offset']}, slope {slope}, edge {edge}, climate {climate}, original complete PAM SHA256 {source['source_pam_sha256']}; source state {source['source_state']} at original height {source['source_height']}. Hand-authored soil toe/shelf/turf crest sections follow only the original undoubled river plane. Object thickness is four quarter-unit cells, not an eight-unit inflated bank. Extra doubled-terrain support, tilt/join/height/paint fidelity and all live/LOD/phase/ship/custom/absence states remain unaccepted. No source pixel/alpha is geometry and no water belongs to this volume. Sea-level source wave fringes remain independently original, not blue voxel bank paint; no runtime source interception/binding occurs.",
            "ops":ops}
    assert len(models) == 32
    value = {"format":1,"reference":"Thirty-two separate manually authored original-datum sloped bank studies. Twenty-six particular elevated observations and six particular sea-level observations do not establish the other160 conditional sloped owners or all shore/snow/desert/grid/height/custom/absence states. Earlier48 flat studies and all catalogue-wide coverage requirements remain; all banks are unbound and below acceptance.",
        "materials":materials,"models":models,"bindings":{}}
    target.write_text(json.dumps(value,indent=2)+"\n")
    receipt = {"models":32,"authored_source_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "retained_flat_palette_sha256":hashlib.sha256(flat_path.read_bytes()).hexdigest(),
        "quarter_unit_original_slope_rise":32,"maximum_local_bank_thickness_cells":4,
        "extra_doubled_terrain_support_authored":False,"water_material_or_geometry_authored":False,"runtime_bindings":0,"quality_approvals":0}
    (HERE / "authoring-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n"); print(json.dumps(receipt))


if __name__ == "__main__": main()

"""Hand-author separate thin shore-bank shells; never voxelise their water fringes."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
CLIMATES=('temperate','arctic','tropic','toyland')
PLANES={3:(0,1),6:(1,1),9:(1,-1),12:(0,-1)}
# Explicit nonuniform quarter-unit erosion sections, not image/palette sampling.
SECTIONS=(0,6,14,23,31,42,50,59,64)
TOES=(9,10,8,9,11,9,10,8)
SHELVES=(7,8,6,7,9,7,8,6)
CRESTS=(5,6,4,5,7,5,6,4)


def section(slope,edge,start,end,width,bottom,thickness,material):
    longitudinal,sign=PLANES[slope];far=edge in (1,2)
    low,high=(64-width,64) if far else (0,width)
    height=lambda t:t//2 if sign>0 else 32-t//2
    outline=[[start,height(start)+bottom],[end,height(end)+bottom],
        [end,height(end)+bottom+thickness],[start,height(start)+bottom+thickness]]
    return ['prism',material,1-longitudinal,low,high,outline]


def main():
    target=HERE/'authored-source.json'
    if target.exists():raise ValueError('Retain every original shore-bank authoring pass')
    palette_path=HERE.parent/'river-bank-breadth/paint-repaired-authored-source.json'
    palette=json.loads(palette_path.read_text())['materials'];models={}
    for source in json.loads((HERE/'actual-source-index.json').read_text()):
        slope,edge,label=source['slope'],source['requested_offset']%12,source['climate_name']
        assert source['source_height']==0 and source['public_terrain_type_query_performed'] and slope in PLANES
        assert (slope in (3,12) and edge in (1,3)) or (slope in (6,9) and edge in (0,2))
        ops=[]
        for index,(start,end) in enumerate(zip(SECTIONS,SECTIONS[1:])):
            ops.extend([section(slope,edge,start,end,TOES[index],0,1,label+'_soil'),
                section(slope,edge,start,end,SHELVES[index],1,1,label+'_soil'),
                section(slope,edge,start,end,CRESTS[index],2,2,label+'_grass')])
        seed=271828+source['requested_offset']+CLIMATES.index(label)*100
        ops.extend([['scatter_paint',label+'_soil_light',5,seed,0,0,0,64,64,36,label+'_soil',[3,2,1]],
            ['scatter_paint',label+'_soil_dark',11,seed+161803,0,0,0,64,64,36,label+'_soil',[2,3,1]],
            ['scatter_paint',label+'_grass_light',5,seed+314159,0,0,0,64,64,36,label+'_grass',[3,2,2]],
            ['scatter_paint',label+'_grass_pale',13,seed+141421,0,0,0,64,64,36,label+'_grass',[2,3,1]]])
        name=f"river_bank_shore_study_{label}_offset{source['requested_offset']:02d}"
        models[name]={'size':[64,64,36],'cell_size':[0.25,0.25,0.25],'origin':[0,0,0],
            'review_status':'unbound-source-study',
            'reference':f"Separate observed sea-level Classic bank owner {source['requested_offset']}, slope {slope}, {label}; actual public AITile terrain type {source['public_terrain_type']}, exact complete original source SHA256 {source['source_pam_sha256']}. Manual nonuniform soil toe/shelf/turf erosion sections remain at the original undoubled slope and tile datum, with four-cell maximum bank thickness. Original sea wave fringe is retained independently in the complete source comparison, never turned into blue bank voxels or accepted as a proven new water decomposition. Extra doubled-terrain support, runtime source interception, complete conditional/terrain/parameter/phase/LOD/picking/ship states and all six quality gates remain unaccepted.",
            'ops':ops}
    assert len(models)==20
    value={'format':1,'reference':'Twenty particular observed shore-painted bank studies add state breadth, not twenty additional conditional shape slots or accepted runtime owners. Some particular sea-level source states overlap earlier unaccepted sloped observations; these are separately reauthored owners, not fabricated new conditional slots. Canonical artwork and all100 earlier bank studies are unchanged. Geometry is manually authored without image fitting, alpha tracing, colour fitting or simulation RNG. Original wave pixels and every later failure are preserved.',
        'materials':palette,'models':models,'bindings':{}}
    target.write_text(json.dumps(value,indent=2)+'\n')
    receipt={'models':len(models),'authored_source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'maximum_bank_thickness_cells':4,'original_undoubled_slope_rise_cells':32,
        'new_conditional_shape_slots_claimed':0,'water_geometry_or_blue_wave_reclassification_authored':False,
        'geometry_derived_from_pixels_or_alpha':False,'runtime_bindings':0,'quality_approvals':0}
    (HERE/'authoring-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()

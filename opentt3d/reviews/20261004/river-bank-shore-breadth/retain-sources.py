"""Retain complete actually selected shore sources and their public-query provenance."""
from collections import Counter
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools/assets'))
from contact_sheet import read_pam


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--complete-interrupted-retention',action='store_true');args=parser.parse_args()
    target=HERE/'sources'
    if target.exists():
        if not args.complete_interrupted_retention or not (HERE/'retained-incorrect-source-count.json').exists():
            raise ValueError('Retain earlier complete shore sources')
        retained=json.loads((HERE/'retained-incorrect-source-count.json').read_text())
        assert all(digest(HERE/name)==sha for name,sha in retained['copied_original_sources_retained_without_changes'].items())
    else:target.mkdir()
    all_rows=json.loads((HERE/'actual-terrain-selector-observations.json').read_text());selected={}
    for row in all_rows:
        if row['backend']!='vulkan' or row['feature']!='CF_RIVER_EDGE' or row['source_height']!=0 or row['absent']:continue
        key=(row['climate_name'],row['requested_offset'])
        if key in selected:continue
        assert row['base_set']=='OpenGFX2 Classic' and row['base_graphics'] and row['requested_offset']==row['resolved_offset']
        assert row['public_terrain_type_query_performed'] and row['source_file']=='ogfx2e_extra_8'
        original=ROOT/row['original_source_pam'];assert digest(original)==row['source_image_sha256']
        twin=next(other for other in all_rows if other['backend']=='opengl' and other['seed']==row['seed'] and
            other['climate']==row['climate'] and other['feature']==row['feature'] and other['tile']==row['tile'] and other['requested_offset']==row['requested_offset'])
        assert twin['source_image_sha256']==row['source_image_sha256'] and twin['source_offset']==row['source_offset'] and twin['source_size']==row['source_size']
        destination=target/f"{row['climate_name']}-shore-{row['requested_offset']:02d}.pam"
        if destination.exists():assert digest(destination)==digest(original)
        else:shutil.copy2(original,destination)
        picture=read_pam(destination);assert picture.mode=='RGBA'
        native_size=list(picture.size)
        # The observer stores cache registration at 4x, while ExportSprite keeps
        # the complete raw native sprite. Never divide, crop or resize its pixels.
        assert row['source_size']==[dimension*4 for dimension in native_size]
        assert all(value%4==0 for value in row['source_offset'])
        selected[key]={**row,'source_pam':str(destination.relative_to(ROOT)),'source_pam_sha256':digest(destination),
            'native_size':native_size,'native_offset':[value//4 for value in row['source_offset']],
            'native_source_pixels_resized':False,'source_wave_fringe_preserved':True,
            'source_state':'actual-observed-sea-level-shore','runtime_bound':False,'quality_approved':False}
    rows=[row for key,row in sorted(selected.items())];assert len(rows)==20
    with (HERE/'actual-source-index.json').open('x') as stream:json.dump(rows,stream,indent=2);stream.write('\n')
    terrain=Counter((row['climate_name'],row['public_terrain_type']) for row in all_rows if row['backend']=='vulkan' and row['feature']=='CF_RIVER_SLOPE')
    value={'retained_utc':datetime.now(timezone.utc).isoformat(),'distinct_particular_shore_sources':len(rows),
        'shore_sources_by_climate':dict(Counter(row['climate_name'] for row in rows)),
        'public_terrain_types_observed':[{'climate':key[0],'public_terrain_type':key[1],'river_tiles':count} for key,count in sorted(terrain.items())],
        'new_conditional_shape_slots_claimed':0,'unobserved_slots_or_terrain_types_declared_absent':False,
        'complete_original_native_source_images_and_wave_fringe_retained':True,'backend_source_bytes_and_registration_exact':True,
        'all_source_geometry_ownership_phase_and_quality_gates_accepted':False,'quality_approvals':0}
    with (HERE/'source-retention-receipt.json').open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(value))


if __name__=='__main__':main()

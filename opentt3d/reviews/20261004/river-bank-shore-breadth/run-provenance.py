"""Public terrain queries and fresh quiet original-selector controls for shore banks."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BUILD = ROOT/'build-macos'
CONTROL = BUILD/'breadth-original-river-shore-canonical-frozen-build'
CLIMATES = ('temperate','arctic','tropic','toyland')
sys.path.insert(0,str(ROOT/'tools/assets'))
sys.path.insert(0,str(ROOT/'tools/opentt3d'))
from live_river_selectors import selected_river_selectors
from fixture_rivers import validate_survey
from fixture_locks import verify_save


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def write_new(path,value):
    with path.open('x') as stream: json.dump(value,stream,indent=2);stream.write('\n')


def originals():
    return [(climate,271828,BUILD/('breadth-original-river-natural-survey-'+climate)) for climate in CLIMATES]+[
        ('tropic',161803,BUILD/'breadth-original-river-natural-survey-tropic-seed161803')]


def survey():
    records=[]
    for climate,seed,original in originals():
        source=json.loads((original/'fixture.json').read_text());save=original/source['save']
        assert verify_save(save)==source['save_sha256']
        if climate=='arctic':
            output=BUILD/'breadth-original-river-terrain-query-arctic-reload-correlated'
            command=None
            assert (output/'fixture.json').is_file()
        else:
            output=BUILD/f'breadth-original-river-terrain-query-{climate}-seed{seed}-correlated'
            command=[sys.executable,'tools/opentt3d/fixture_rivers.py','--build-dir',str(BUILD),'--output',str(output),
                '--climate',climate,'--seed',str(seed),'--savegame',str(save),'--timeout','300']
            with (HERE/f'survey-{climate}-seed{seed}.log').open('x') as log:
                subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1'),stdout=log,stderr=subprocess.STDOUT,check=True)
        observed=json.loads((output/'fixture.json').read_text());validate_survey(observed,observed['tiles'])
        assert observed['public_terrain_type_queries'] and observed['loaded_original_world_not_regenerated']
        assert observed['input_save_sha256']==source['save_sha256']
        assert [{key:tile[key] for key in ('tile','x','y','slope','min_height_levels')} for tile in observed['tiles']]==source['tiles']
        assert verify_save(output/observed['save'])==observed['save_sha256']
        records.append({'climate':climate,'seed':seed,'output':str(output.relative_to(ROOT)),
            'command':command,'reused_fresh_correlated_arctic_run':command is None,'original_tile_slope_height_rows_exact':True,
            'fixture_sha256':digest(output/'fixture.json'),'input_original_save_sha256':source['save_sha256'],
            'original_save_sha256':observed['save_sha256'],'public_terrain_type_counts':dict(Counter(tile['public_terrain_type'] for tile in observed['tiles'])),
            'actual_command_acknowledgements_sha256':digest(output/'command-acknowledgements.json'),
            'survey_token':observed['survey_token'],'complete_terrain_type_or_snowline_coverage':False,'quality_approved':False})
    write_new(HERE/'surveys.json',records);print(json.dumps({'surveys':len(records),'original_public_queries':True,'quality_approvals':0}))


def freeze():
    assert not CONTROL.exists()
    (CONTROL/'baseset').mkdir(parents=True)
    shutil.copy2(BUILD/'opentt3d',CONTROL/'opentt3d')
    payload=(BUILD/'baseset/opentt3d-voxels.json').read_bytes();catalogue=json.loads(payload)
    assert len(catalogue['models'])==1915
    for category in ('objects','object_ground'):assert not any(int(layout)>=12 for layout in catalogue['bindings'][category])
    (CONTROL/'baseset/opentt3d-voxels.json').write_bytes(payload)
    for path in (BUILD/'baseset').iterdir():
        if path.name!='opentt3d-voxels.json':(CONTROL/'baseset'/path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name in ('ai','game','lang'):(CONTROL/name).symlink_to((BUILD/name).resolve(),target_is_directory=True)
    (HERE/'canonical-catalogue.json.gz').write_bytes(gzip.compress(payload,mtime=0))
    value={'frozen_utc':datetime.now(timezone.utc).isoformat(),'models':1915,'unbound_larger_hq_studies':84,
        'runtime_larger_hq_bindings':0,'sha256':{name:digest(CONTROL/name) for name in ('opentt3d','baseset/opentt3d-voxels.json')},
        'canonical_runtime_bindings_unchanged':True,'quality_approvals':0}
    write_new(CONTROL/'manifest.json',value);write_new(HERE/'canonical-frozen-manifest.json',value);print(json.dumps(value))


def capture():
    manifest=json.loads((CONTROL/'manifest.json').read_text());assert all(digest(CONTROL/name)==sha for name,sha in manifest['sha256'].items())
    records=[];joined=[]
    for survey in json.loads((HERE/'surveys.json').read_text()):
        fixture=ROOT/survey['output'];data=json.loads((fixture/'fixture.json').read_text());owners={tile['tile']:tile for tile in data['tiles']}
        for backend in ('vulkan','opengl'):
            for tracing in (False,True):
                output=BUILD/f"breadth-original-river-shore-provenance-{survey['climate']}-seed{survey['seed']}-{backend}-{'on' if tracing else 'off'}"
                command=[sys.executable,'tools/opentt3d/smoke.py','--build-dir',str(CONTROL),'--output',str(output),
                    '--background','--no-hidpi','--record-console','--synchronous-save','--blitter','40bpp-anim','--backend',backend,
                    '--savegame',str(fixture/data['save']),'--ai-dir',str(fixture/'ai'),'--center','64','64','--zoom','5',
                    '--resolution','640','480','--verify-world-atlas','--verify-tile-picking','--timeout','600','--brief']
                with (HERE/(output.name+'.log')).open('x') as log:
                    process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1',OPENTT3D_EXPORT_WATER_SOURCES='1' if tracing else '0'),stdout=log,stderr=subprocess.STDOUT)
                records.append({'output':str(output.relative_to(ROOT)),'climate':survey['climate'],'seed':survey['seed'],
                    'backend':backend,'tracing':tracing,'command':command,'exit_code':process.returncode,
                    'input_save_sha256':data['save_sha256'],'public_survey_fixture_sha256':survey['fixture_sha256']})
                (HERE/'provenance-runs.json').write_text(json.dumps(records,indent=2)+'\n')
                if process.returncode:raise SystemExit(process.returncode)
                result=json.loads((output/'result.json').read_text())
                assert result['background'] and result['image_size']==[640,480] and result['original_console_save_success_recorded'] and result['synchronous_original_save_verified']
                if not tracing:continue
                directory=output/'renderer3d-reference';observed=json.loads((directory/'river-selectors.json').read_text())['observations']
                for source in observed:
                    tile=owners[source['tile']]
                    assert source['tile_xy']==[tile['x'],tile['y']] and source['slope']==tile['slope'] and source['source_height']==tile['min_height_levels']*8
                    if not source['absent']:source['source_image_sha256']=digest(directory/source['source_image'])
                selected=selected_river_selectors(observed,data,CLIMATES.index(survey['climate']))
                assert selected['observed_tiles']==data['river_tiles']
                for source in observed:
                    joined.append({**source,'climate_name':survey['climate'],'seed':survey['seed'],'backend':backend,
                        'public_terrain_type':owners[source['tile']]['public_terrain_type'],'public_terrain_type_query_performed':True,
                        'public_survey_token':data['survey_token'],'public_survey_fixture':str((fixture/'fixture.json').relative_to(ROOT)),
                        'public_survey_fixture_sha256':digest(fixture/'fixture.json'),'native_control':str(output.relative_to(ROOT)),
                        'original_source_pam':str((directory/source['source_image']).relative_to(ROOT)) if not source['absent'] else None,
                        'quality_approved':False})
    assert len(records)==20
    write_new(HERE/'actual-terrain-selector-observations.json',joined)
    print(json.dumps({'quiet_acknowledged_controls':len(records),'source_observations':len(joined),'complete_terrain_type_coverage':False,'quality_approvals':0}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('survey','freeze','capture','all'));args=parser.parse_args()
    if args.phase=='all':
        survey();freeze();capture()
    else:{'survey':survey,'freeze':freeze,'capture':capture}[args.phase]()


if __name__=='__main__':main()

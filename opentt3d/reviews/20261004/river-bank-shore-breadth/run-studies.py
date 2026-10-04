"""Freeze unchanged canonical/earlier banks plus twenty separate shore studies."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BUILD=ROOT/'build-macos'
BASE=BUILD/'breadth-original-river-shore-canonical-frozen-build'
FROZEN=BUILD/'breadth-original-river-shore-initial-frozen-build'
COMPILER=HERE.parent/'river-relief-ownership/approved-compiler-snapshot.py'
CLIMATES=('temperate','arctic','tropic','toyland')
sys.path.insert(0,str(ROOT/'tools/assets'))
from quality_audit import fingerprint


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def add_models(merged,source,names):
    indices={tuple(material):index+1 for index,material in enumerate(merged['materials'])}
    mapping={}
    for index,material in enumerate(source['materials'],1):
        key=tuple(material)
        if key not in indices:
            merged['materials'].append(material);indices[key]=len(merged['materials'])
        mapping[index]=indices[key]
    for name in names:
        assert name not in merged['models']
        model=source['models'][name]
        merged['models'][name]={**model,'runs':[run[:4]+[mapping[run[4]]] for run in model['runs']]}
        assert fingerprint(model,source['materials'])==fingerprint(merged['models'][name],merged['materials'])


def freeze():
    assert not FROZEN.exists() and not (HERE/'diagnostic-catalogue.json.gz').exists()
    before=json.loads((BASE/'manifest.json').read_text());assert all(digest(BASE/name)==sha for name,sha in before['sha256'].items())
    base=json.loads((BASE/'baseset/opentt3d-voxels.json').read_text());assert len(base['models'])==1915
    prior=json.loads(gzip.decompress((HERE.parent/'river-bank-snow-breadth/diagnostic-catalogue.json.gz').read_bytes()))
    old_names=[name for name in prior['models'] if name.startswith(('river_bank_study_','river_bank_slope_study_','river_bank_snow_study_'))]
    assert len(old_names)==100
    canonical=set(prior['models'])-set(old_names);assert len(canonical)==1831
    assert base['bindings']==prior['bindings']
    assert all(fingerprint(prior['models'][name],prior['materials'])==fingerprint(base['models'][name],base['materials']) for name in canonical)
    spec=importlib.util.spec_from_file_location('shore_compiler',COMPILER);compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
    study=compiler.compile_catalogue(json.loads((HERE/'authored-source.json').read_text()));assert len(study['models'])==20 and study['bindings']=={}
    merged=json.loads(json.dumps(base));add_models(merged,prior,old_names);add_models(merged,study,study['models'])
    assert len(merged['models'])==2035 and merged['bindings']==base['bindings']
    assert all(merged['models'][name]==model for name,model in base['models'].items())
    (FROZEN/'baseset').mkdir(parents=True)
    payload=(json.dumps(merged,separators=(',',':'))+'\n').encode();(FROZEN/'baseset/opentt3d-voxels.json').write_bytes(payload)
    (HERE/'diagnostic-catalogue.json.gz').write_bytes(gzip.compress(payload,mtime=0))
    shutil.copy2(BASE/'opentt3d',FROZEN/'opentt3d')
    for path in (BASE/'baseset').iterdir():
        if path.name!='opentt3d-voxels.json':(FROZEN/'baseset'/path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name in ('ai','game','lang'):(FROZEN/name).symlink_to((BASE/name).resolve(),target_is_directory=True)
    for name,path in (('compiler-snapshot.py',COMPILER),('authored-source.json',HERE/'authored-source.json'),('test_authored_study.py',HERE/'test_authored_study.py')):shutil.copy2(path,FROZEN/name)
    manifest={'frozen_utc':datetime.now(timezone.utc).isoformat(),'models':2035,'canonical_models_unchanged':1831,
        'unbound_larger_hq_models':84,'earlier_unbound_banks_unchanged':100,'new_shore_bank_models':20,
        'bindings_and_original_canonical_volume_fingerprints_exact':True,'runtime_bindings_added':0,'quality_approvals':0,
        'sha256':{name:digest(FROZEN/name) for name in ('opentt3d','baseset/opentt3d-voxels.json','compiler-snapshot.py','authored-source.json','test_authored_study.py')},
        'model_fingerprints':{name:fingerprint(model,study['materials']) for name,model in study['models'].items()}}
    for path in (FROZEN/'manifest.json',HERE/'frozen-manifest.json'):
        with path.open('x') as stream:json.dump(manifest,stream,indent=2);stream.write('\n')
    print(json.dumps({key:value for key,value in manifest.items() if key not in ('sha256','model_fingerprints')}))


def run():
    manifest=json.loads((FROZEN/'manifest.json').read_text());assert all(digest(FROZEN/name)==sha for name,sha in manifest['sha256'].items())
    assert not (HERE/'study-runs.json').exists();records=[]
    surveys=json.loads((HERE/'surveys.json').read_text())
    for climate in CLIMATES:
        survey=next(row for row in surveys if row['climate']==climate and row['seed']==271828)
        fixture=ROOT/survey['output'];data=json.loads((fixture/'fixture.json').read_text())
        for backend in ('vulkan','opengl'):
            output=BUILD/f'breadth-original-river-shore-initial-{climate}-{backend}-study'
            command=[sys.executable,'tools/opentt3d/smoke.py','--build-dir',str(FROZEN),'--output',str(output),
                '--background','--no-hidpi','--record-console','--synchronous-save','--blitter','40bpp-anim','--backend',backend,
                '--savegame',str(fixture/data['save']),'--ai-dir',str(fixture/'ai'),'--center','64','64','--zoom','5',
                '--resolution','640','480','--verify-world-atlas','--verify-tile-picking',
                '--gallery-voxel-prefix','river_bank_shore_study_'+climate,'--gallery-voxel-overview',
                '--verify-voxel-meshes','river_bank_shore_study_'+climate,'--timeout','600','--brief']
            with (HERE/(output.name+'.log')).open('x') as log:
                process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1',OPENTT3D_EXPORT_WATER_SOURCES='0'),stdout=log,stderr=subprocess.STDOUT)
            records.append({'output':str(output.relative_to(ROOT)),'climate':climate,'backend':backend,'exit_code':process.returncode,
                'command':command,'input_original_save_sha256':data['save_sha256'],
                'canonical_control':f"build-macos/breadth-original-river-shore-provenance-{climate}-seed271828-{backend}-off"})
            (HERE/'study-runs.json').write_text(json.dumps(records,indent=2)+'\n')
            if process.returncode:raise SystemExit(process.returncode)
            result=json.loads((output/'result.json').read_text())
            assert result['background'] and result['image_size']==[640,480] and result['original_console_save_success_recorded'] and result['synchronous_original_save_verified']
    subprocess.run([sys.executable,'tools/assets/compact_reviews.py',str(BUILD),'--validation-manifest',str(HERE/'study-runs.json'),'--apply'],cwd=ROOT,check=True)
    print(json.dumps({'fresh_acknowledged_quiet_study_runs':len(records),'individual_shore_models':20,'runtime_bank_coverage_accepted':0,'quality_approvals':0}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('freeze','run','all'));args=parser.parse_args()
    if args.phase=='all':freeze();run()
    else:{'freeze':freeze,'run':run}[args.phase]()


if __name__=='__main__':main()

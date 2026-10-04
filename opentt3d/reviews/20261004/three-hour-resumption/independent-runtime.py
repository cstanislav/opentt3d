"""Native tests of the independently downloaded signed app, using its own resources."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BUILD=ROOT/'build-macos'
sys.path.insert(0,str(ROOT/'tools/assets'))
from compare_galleries import captures,image


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tag',required=True);parser.add_argument('--commit',required=True);args=parser.parse_args()
    audit=json.loads((HERE/'independent-artifact-audit.json').read_text())
    assert audit['source_and_all_downloaded_artifacts_exact'] and audit['tag']==args.tag and audit['commit']==args.commit
    download=BUILD/'playable-release43-independent-download'/f'{args.tag}-macos-arm64.zip'
    expected=next(row for row in audit['assets'] if row['name']==download.name)
    assert digest(download)==expected['sha256'] and download.stat().st_size==expected['bytes']
    extracted=BUILD/'playable-release43-independent-extracted';assert not extracted.exists()
    subprocess.run(['ditto','-x','-k',str(download),str(extracted)],check=True)
    app,=extracted.rglob('*.app');resources=app/'Contents/Resources';executable=app/'Contents/MacOS/opentt3d'
    metadata=json.loads((resources/'release-info/build.json').read_text())
    assert metadata['commit']==args.commit and metadata['tag']==args.tag
    catalogue=digest(resources/'baseset/opentt3d-voxels.json');binary=digest(executable)
    assert catalogue==audit['catalogue_lf_sha256'] and len(json.loads((resources/'baseset/opentt3d-voxels.json').read_text())['models'])==1915
    with (HERE/'independent-codesign-before.log').open('x') as log:
        subprocess.run(['codesign','--verify','--deep','--strict','--verbose=2',str(app)],stdout=log,stderr=subprocess.STDOUT,check=True)
    packages=[];records=[];equal=[]
    for backend,driver in (('default',None),('opengl','cocoa-opengl')):
        output=BUILD/f'playable-release43-independent-package-{backend}'
        command=[sys.executable,'tools/opentt3d/package_smoke.py',str(app),'--output',str(output)]
        if driver:command.extend(['--driver',driver])
        with (HERE/(output.name+'.log')).open('x') as log:
            process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1'),stdout=log,stderr=subprocess.STDOUT)
        packages.append({'output':str(output.relative_to(ROOT)),'command':command,'exit_code':process.returncode})
        (HERE/'independent-package-runs.json').write_text(json.dumps(packages,indent=2)+'\n')
        if process.returncode:raise SystemExit(process.returncode)
    for climate in ('temperate','arctic','tropic','toyland'):
        fixture=BUILD/f'breadth-original-object-command-{climate}-owned-land-fixture';site=json.loads((fixture/'fixture.json').read_text())
        for backend in ('vulkan','opengl'):
            output=BUILD/f'playable-release43-independent-{climate}-{backend}'
            command=[sys.executable,str(HERE/'smoke-cow.py'),'--build-dir',str(resources),'--executable',str(executable),'--output',str(output),
                '--background','--no-hidpi','--record-console','--synchronous-save','--blitter','40bpp-anim','--backend',backend,
                '--savegame',str(fixture/'save/object-fixture.sav'),'--ai-dir',str(fixture/'ai'),
                '--reference-object','4','--reference-object-tile',str(site['hq_x']),str(site['hq_y']),
                '--export-objects','--gallery-voxel-prefix','hq_ground_tiny_','--gallery-voxel-overview',
                '--verify-voxel-meshes','hq_','--verify-world-atlas','--verify-tile-picking','--zoom','0','--resolution','640','480','--timeout','600','--brief']
            with (HERE/(output.name+'.log')).open('x') as log:
                process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1',OPENTT3D_EXPORT_WATER_SOURCES='0'),stdout=log,stderr=subprocess.STDOUT)
            records.append({'output':str(output.relative_to(ROOT)),'climate':climate,'backend':backend,'command':command,'exit_code':process.returncode})
            (HERE/'independent-native-runs.json').write_text(json.dumps(records,indent=2)+'\n')
            if process.returncode:raise SystemExit(process.returncode)
            runlog=(output/'run.log').read_text();result=json.loads((output/'result.json').read_text())
            assert '40 independent HQ owner LOD rebuild views preserve' in runlog and '128 original HQ ground views preserve' in runlog and '24 joined original HQ views preserve' in runlog
            assert result['background'] and result['original_allow_hidpi'] is False and result['image_size']==[640,480]
            assert result['synchronous_original_save_verified'] and result['original_console_save_success_recorded']
            assert digest(output/'baseset/opentt3d-voxels.json')==catalogue
            baseline=BUILD/f'breadth-original-hq-source-owner-final-{climate}-{backend}'
            old,new=[captures(directory/'renderer3d-reference','model-voxel-hq_ground_tiny_*') for directory in (baseline,output)]
            assert len(old)==144 and old.keys()==new.keys()
            for name,path in old.items():
                a,b=image(path),image(new[name]);assert a.size==b.size and a.tobytes()==b.tobytes(),(climate,backend,name)
            source_count=0
            old_sources=captures(baseline/'renderer3d-reference','object-*');new_sources=captures(output/'renderer3d-reference','object-*')
            assert len(old_sources)==37 and old_sources.keys()==new_sources.keys()
            for name,path in old_sources.items():
                a,b=image(path),image(new_sources[name]);assert a.size==b.size and a.tobytes()==b.tobytes(),(climate,backend,name)
                source_count+=1
            equal.append({'climate':climate,'backend':backend,'prior_tiny_ground_gallery_images_exact':144,'prior_original_source_images_exact':source_count,
                'scoped_native_owner_lod_picking_atlas_and_actual_save_success_verified':True,'whole_world_equality_to_old_unlogged_control_inferred':False})
            subprocess.run([sys.executable,'tools/assets/compact_reviews.py',str(BUILD),'--validation-manifest',str(HERE/'independent-native-runs.json'),'--apply'],cwd=ROOT,check=True)
    for kind,size,x,y,fixture in (
        ('public-tunnel',0,78,16,BUILD/'breadth-original-hq-public-tunnel-site-fixture'),
        ('natural-size1',1,8,8,BUILD/'breadth-original-hq-natural-upgrade-temperate-costed-town-service-study')):
        for backend in ('vulkan','opengl'):
            output=BUILD/f'playable-release43-independent-{kind}-{backend}'
            command=[sys.executable,str(HERE/'smoke-cow.py'),'--build-dir',str(resources),'--executable',str(executable),'--output',str(output),
                '--background','--no-hidpi','--record-console','--synchronous-save','--blitter','40bpp-anim','--backend',backend,
                '--savegame',str(fixture/'save/hq-natural-final.sav'),'--ai-dir',str(fixture/'ai'),
                '--reference-object','4','--reference-object-tile',str(x),str(y),'--verify-voxel-meshes','hq_',
                '--verify-world-atlas','--verify-tile-picking','--zoom','0','--resolution','640','480','--timeout','600','--brief']
            if kind=='public-tunnel':command.append('--verify-live-tunnel')
            with (HERE/(output.name+'.log')).open('x') as log:
                process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1'),stdout=log,stderr=subprocess.STDOUT)
            records.append({'output':str(output.relative_to(ROOT)),'kind':kind,'backend':backend,'command':command,'exit_code':process.returncode})
            (HERE/'independent-native-runs.json').write_text(json.dumps(records,indent=2)+'\n')
            if process.returncode:raise SystemExit(process.returncode)
            runlog=(output/'run.log').read_text();result=json.loads((output/'result.json').read_text())
            assert f'focused voxel object 4 size {size} at {x},{y}' in runlog
            assert all(f'live voxel object 4 size {size} part {part} ground' in runlog for part in range(4))
            assert not re.search(rf'live voxel object 4 size {size} part \d body',runlog)
            assert '40 independent HQ owner LOD rebuild views preserve' in runlog
            assert result['synchronous_original_save_verified'] and result['original_console_save_success_recorded']
            if kind=='public-tunnel':
                assert '20 live tunnel scenery culling views preserve exact RGBA and picking' in runlog
                for part,tx in ((0,78),(1,79)):assert f'live HQ ground tunnel retention size 0 part {part} tile {tx},16, relative floor -32' in runlog
            subprocess.run([sys.executable,'tools/assets/compact_reviews.py',str(BUILD),'--validation-manifest',str(HERE/'independent-native-runs.json'),'--apply'],cwd=ROOT,check=True)
    assert digest(executable)==binary and digest(resources/'baseset/opentt3d-voxels.json')==catalogue
    with (HERE/'independent-codesign-after.log').open('x') as log:
        subprocess.run(['codesign','--verify','--deep','--strict','--verbose=2',str(app)],stdout=log,stderr=subprocess.STDOUT,check=True)
    evidence={}
    for row in packages+records:
        run=ROOT/row['output']
        for pattern in ('run.log','result.json','console-review.log','screenshot/*.png','save/*.sav'):
            for path in run.glob(pattern):evidence[str(path.relative_to(ROOT))]=digest(path)
    value={'audited_utc':datetime.now(timezone.utc).isoformat(),'tag':args.tag,'commit':args.commit,'app':str(app.relative_to(ROOT)),
        'independent_download_sha256':expected['sha256'],'binary_sha256':binary,'catalogue_sha256':catalogue,'models':1915,
        'resources_only_from_download':True,'package_controls':packages,'native_controls':records,'scoped_equalities':equal,
        'evidence_sha256':evidence,'accepted_scoped_native_runtime':True,'accepted_full_objective':False,
        'runtime_bank_or_larger_hq_coverage_added':0,'sustained_60fps_windows_arm64_gpu_input_replay_or_network_approved':False,'quality_approvals':0}
    (HERE/'independent-runtime-audit.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('package_controls','native_controls','scoped_equalities','evidence_sha256')}))


if __name__=='__main__':main()

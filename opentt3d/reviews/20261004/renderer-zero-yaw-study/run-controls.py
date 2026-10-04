"""Fresh immutable zero-heading renderer noninterference controls, without tolerances."""
import argparse
from datetime import datetime,timezone
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
SHORE=HERE.parent/'river-bank-shore-breadth'
BASE=BUILD/'breadth-original-river-shore-initial-frozen-build'
CANDIDATE=BUILD/'breadth-original-renderer-zero-yaw-frozen-build'
CLIMATES=('temperate','arctic','tropic','toyland')
sys.path.insert(0,str(ROOT/'tools/assets'))
from compare_galleries import captures,image


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def compare(a,b,pattern):
    left,right=({'world':a},{'world':b}) if a.is_file() and b.is_file() else (captures(a,pattern),captures(b,pattern))
    if not left or left.keys()!=right.keys():raise ValueError('Exact comparison requires every complete nonempty matching image')
    rows=[]
    for name in left:
        x,y=image(left[name]),image(right[name]);assert x.size==y.size
        old,new=x.tobytes(),y.tobytes()
        rows.append({'view':name,'original':str(left[name].relative_to(ROOT)),
            'candidate':str(right[name].relative_to(ROOT)),'different_pixels':sum(old[i:i+4]!=new[i:i+4] for i in range(0,len(old),4)),
            'original_file_sha256':digest(left[name]),'candidate_file_sha256':digest(right[name]),
            'rgba_exact':old==new})
    return {'images':len(rows),'different_images':sum(not row['rgba_exact'] for row in rows),
        'different_pixels':sum(row['different_pixels'] for row in rows),'rows':rows,'resizing_cropping_masks_alpha_compositing_or_tolerance':False}


def freeze():
    assert not CANDIDATE.exists()
    (CANDIDATE/'baseset').mkdir(parents=True)
    shutil.copy2(BUILD/'opentt3d',CANDIDATE/'opentt3d')
    shutil.copy2(BASE/'baseset/opentt3d-voxels.json',CANDIDATE/'baseset/opentt3d-voxels.json')
    for path in (BASE/'baseset').iterdir():
        if path.name!='opentt3d-voxels.json':(CANDIDATE/'baseset'/path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name in ('ai','game','lang'):(CANDIDATE/name).symlink_to((BASE/name).resolve(),target_is_directory=True)
    value={'frozen_utc':datetime.now(timezone.utc).isoformat(),'unchanged_catalogue_sha256':digest(CANDIDATE/'baseset/opentt3d-voxels.json'),
        'original_binary_sha256':digest(BASE/'opentt3d'),'candidate_binary_sha256':digest(CANDIDATE/'opentt3d'),
        'gl_backend_candidate_sha256':digest(ROOT/'src/renderer3d/gl_backend.cpp'),'runtime_bindings_added':0,'quality_approvals':0}
    for path in (HERE/'frozen-manifest.json',CANDIDATE/'manifest.json'):
        with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def run():
    manifest=json.loads((CANDIDATE/'manifest.json').read_text())
    assert digest(CANDIDATE/'opentt3d')==manifest['candidate_binary_sha256']
    assert digest(CANDIDATE/'baseset/opentt3d-voxels.json')==digest(BASE/'baseset/opentt3d-voxels.json')==manifest['unchanged_catalogue_sha256']
    assert not (HERE/'runs.json').exists();records=[];comparisons=[];saved=[]
    for row in json.loads((SHORE/'study-runs.json').read_text()):
        output=BUILD/f"breadth-original-renderer-zero-yaw-{row['climate']}-{row['backend']}-study"
        command=row['command'].copy()
        command[0]=sys.executable
        command[command.index('--build-dir')+1]=str(CANDIDATE)
        command[command.index('--output')+1]=str(output)
        with (HERE/(output.name+'.log')).open('x') as log:
            process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1',OPENTT3D_EXPORT_WATER_SOURCES='0'),stdout=log,stderr=subprocess.STDOUT)
        records.append({'output':str(output.relative_to(ROOT)),'original':row['output'],'backend':row['backend'],
            'climate':row['climate'],'command':command,'exit_code':process.returncode})
        (HERE/'runs.json').write_text(json.dumps(records,indent=2)+'\n')
        if process.returncode:raise SystemExit(process.returncode)
        original=ROOT/row['output'];result=json.loads((output/'result.json').read_text())
        assert result['background'] and result['original_allow_hidpi'] is False and result['image_size']==[640,480]
        assert result['original_console_save_success_recorded'] and result['synchronous_original_save_verified']
        for scope,a,b,pattern in (
            ('complete-world',original/'screenshot/smoke.png',output/'screenshot/smoke.png','*'),
            ('complete-atlas',original/'renderer3d-reference',output/'renderer3d-reference','model-world-atlas-*'),
            ('complete-shore-model-gallery',original/'renderer3d-reference',output/'renderer3d-reference','model-voxel-river_bank_shore_study_*')):
            comparisons.append({'scope':scope,'backend':row['backend'],'climate':row['climate'],**compare(a,b,pattern)})
        saved.append({'backend':row['backend'],'climate':row['climate'],
            'original_sha256':digest(original/'save/smoke-state.sav'),'candidate_sha256':digest(output/'save/smoke-state.sav'),
            'exact_original_save_bytes':(original/'save/smoke-state.sav').read_bytes()==(output/'save/smoke-state.sav').read_bytes()})
    paired=[]
    for climate in CLIMATES:
        a,b=[ROOT/next(row['output'] for row in records if row['climate']==climate and row['backend']==backend) for backend in ('vulkan','opengl')]
        paired.append({'climate':climate,'scope':'complete-cross-backend-world',**compare(a/'screenshot/smoke.png',b/'screenshot/smoke.png','*')})
        paired.append({'climate':climate,'scope':'complete-cross-backend-gallery',**compare(a/'renderer3d-reference',b/'renderer3d-reference','model-voxel-river_bank_shore_study_*')})
    value={'audited_utc':datetime.now(timezone.utc).isoformat(),'fresh_quiet_acknowledged_controls':len(records),
        'same_backend_image_comparisons':comparisons,'same_backend_images':sum(row['images'] for row in comparisons),
        'same_backend_different_images':sum(row['different_images'] for row in comparisons),
        'same_backend_different_pixels':sum(row['different_pixels'] for row in comparisons),
        'save_pairs':saved,'paired_backend_comparisons':paired,'paired_different_pixels':sum(row['different_pixels'] for row in paired),
        'candidate_noninterference_accepted':not any(row['different_images'] for row in comparisons) and all(row['exact_original_save_bytes'] for row in saved),
        'renderer_quality_or_sustained_60fps_accepted':False,'quality_approvals':0}
    with (HERE/'verification.json').open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    subprocess.run([sys.executable,'tools/assets/compact_reviews.py',str(BUILD),'--validation-manifest',str(HERE/'runs.json'),'--apply'],cwd=ROOT,check=True)
    print(json.dumps({key:value for key,value in value.items() if key not in ('same_backend_image_comparisons','save_pairs','paired_backend_comparisons')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('freeze','run','all','audit-complete-files'));args=parser.parse_args()
    if args.phase=='all':freeze();run()
    else:{'freeze':freeze,'run':run,'audit-complete-files':audit_complete_files}[args.phase]()


def audit_complete_files():
    previous=json.loads((HERE/'verification.json').read_text());records=json.loads((HERE/'runs.json').read_text())
    assert len(records)==8 and all(row['exit_code']==0 for row in records)
    comparisons=[];paired=[]
    for row in records:
        original,output=ROOT/row['original'],ROOT/row['output']
        for scope,a,b,pattern in (
            ('complete-world',original/'screenshot/smoke.png',output/'screenshot/smoke.png','*'),
            ('complete-atlas',original/'renderer3d-reference',output/'renderer3d-reference','model-world-atlas-*'),
            ('complete-shore-model-gallery',original/'renderer3d-reference',output/'renderer3d-reference','model-voxel-river_bank_shore_study_*')):
            comparisons.append({'scope':scope,'backend':row['backend'],'climate':row['climate'],**compare(a,b,pattern)})
    for climate in CLIMATES:
        a,b=[ROOT/next(row['output'] for row in records if row['climate']==climate and row['backend']==backend) for backend in ('vulkan','opengl')]
        paired.append({'climate':climate,'scope':'complete-cross-backend-world',**compare(a/'screenshot/smoke.png',b/'screenshot/smoke.png','*')})
        paired.append({'climate':climate,'scope':'complete-cross-backend-gallery',**compare(a/'renderer3d-reference',b/'renderer3d-reference','model-voxel-river_bank_shore_study_*')})
    assert sum(row['images'] for row in comparisons)==400
    saved=[]
    for row in records:
        original,output=ROOT/row['original'],ROOT/row['output']
        saved.append({'backend':row['backend'],'climate':row['climate'],
            'original_sha256':digest(original/'save/smoke-state.sav'),'candidate_sha256':digest(output/'save/smoke-state.sav'),
            'exact_original_save_bytes':(original/'save/smoke-state.sav').read_bytes()==(output/'save/smoke-state.sav').read_bytes()})
    value={**previous,'audited_utc':datetime.now(timezone.utc).isoformat(),
        'rejected_directory_lookup_audit_sha256':digest(HERE/'verification.json'),
        'same_backend_image_comparisons':comparisons,'same_backend_images':sum(row['images'] for row in comparisons),
        'same_backend_different_images':sum(row['different_images'] for row in comparisons),
        'same_backend_different_pixels':sum(row['different_pixels'] for row in comparisons),
        'save_pairs':saved,'paired_backend_comparisons':paired,'paired_different_pixels':sum(row['different_pixels'] for row in paired),
        'candidate_noninterference_accepted':not any(row['different_images'] for row in comparisons) and all(row['exact_original_save_bytes'] for row in saved),
        'all_worlds_and_galleries_nonempty_and_complete':True,'original_audit_world_claim_rejected':True}
    with (HERE/'complete-file-verification.json').open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('same_backend_image_comparisons','save_pairs','paired_backend_comparisons')}))


if __name__=='__main__':main()

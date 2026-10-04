"""Exact HQ gallery and original vehicle pose matrices before/after zero-yaw branch."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BUILD=ROOT/'build-macos'
sys.path.insert(0,str(ROOT/'tools/assets'))
spec=importlib.util.spec_from_file_location('zero_yaw_controls',HERE/'run-controls.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)


def main():
    assert not (HERE/'supplement-runs.json').exists()
    survey=next(row for row in json.loads((HERE.parent/'river-bank-shore-breadth/surveys.json').read_text()) if row['climate']=='temperate')
    fixture=ROOT/survey['output'];data=json.loads((fixture/'fixture.json').read_text());records=[];lookup={}
    for scope,frozen in (('original',control.BASE),('candidate',control.CANDIDATE)):
        for backend in ('vulkan','opengl'):
            output=BUILD/f'breadth-original-renderer-zero-yaw-supplement-{scope}-{backend}-study'
            command=[sys.executable,'tools/opentt3d/smoke.py','--build-dir',str(frozen),'--output',str(output),
                '--background','--no-hidpi','--record-console','--synchronous-save','--blitter','40bpp-anim','--backend',backend,
                '--savegame',str(fixture/data['save']),'--ai-dir',str(fixture/'ai'),'--center','64','64','--zoom','5',
                '--resolution','640','480','--verify-world-atlas','--verify-tile-picking','--verify-renderer','--renderer-verification-scope','scene',
                '--verify-voxel-poses','26','160','204','248','253','--gallery-voxel-prefix','hq_','--gallery-voxel-overview',
                '--verify-voxel-meshes','hq_','--timeout','900','--brief']
            with (HERE/(output.name+'.log')).open('x') as log:
                process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1',OPENTT3D_EXPORT_WATER_SOURCES='0'),stdout=log,stderr=subprocess.STDOUT)
            records.append({'scope':scope,'backend':backend,'output':str(output.relative_to(ROOT)),'command':command,'exit_code':process.returncode})
            (HERE/'supplement-runs.json').write_text(json.dumps(records,indent=2)+'\n')
            if process.returncode:raise SystemExit(process.returncode)
            lookup[scope,backend]=output
            subprocess.run([sys.executable,'tools/assets/compact_reviews.py',str(BUILD),'--validation-manifest',str(HERE/'supplement-runs.json'),'--apply'],cwd=ROOT,check=True)
    comparisons=[];saved=[]
    for backend in ('vulkan','opengl'):
        a,b=lookup['original',backend],lookup['candidate',backend]
        for scope,left,right,pattern in (('complete-world',a/'screenshot/smoke.png',b/'screenshot/smoke.png','*'),
            ('complete-atlas',a/'renderer3d-reference',b/'renderer3d-reference','model-world-atlas-*'),
            ('complete-hq-galleries',a/'renderer3d-reference',b/'renderer3d-reference','model-voxel-hq_*')):
            comparisons.append({'scope':scope,'backend':backend,**control.compare(left,right,pattern)})
        saved.append({'backend':backend,'original_sha256':control.digest(a/'save/smoke-state.sav'),'candidate_sha256':control.digest(b/'save/smoke-state.sav'),
            'exact_original_save_bytes':(a/'save/smoke-state.sav').read_bytes()==(b/'save/smoke-state.sav').read_bytes()})
    value={'audited_utc':datetime.now(timezone.utc).isoformat(),'fresh_quiet_acknowledged_controls':4,'hq_models':116,
        'vehicle_pose_engine_matrices':[26,160,204,248,253],'same_backend_images':sum(row['images'] for row in comparisons),
        'same_backend_different_images':sum(row['different_images'] for row in comparisons),
        'same_backend_different_pixels':sum(row['different_pixels'] for row in comparisons),'comparisons':comparisons,'save_pairs':saved,
        'noninterference_accepted':not any(row['different_images'] for row in comparisons) and all(row['exact_original_save_bytes'] for row in saved),
        'source_fidelity_8_or_sustained_60fps_approved':False,'quality_approvals':0}
    (HERE/'supplement-verification.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('comparisons','save_pairs')}))


if __name__=='__main__':main()

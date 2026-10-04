"""Preserve complete zero-yaw controls and independently recheck all nonempty worlds."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools/opentt3d'))
from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save


def main():
    target=HERE/'native-controls'
    if target.exists():raise ValueError('Preserve every initial and supplementary zero-yaw audit')
    (target/'strict-comparisons').mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('zero_yaw_portable_audit',HERE.parent/'river-relief-ownership/audit-world-controls.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    records=json.loads((HERE/'runs.json').read_text());supplement=json.loads((HERE/'supplement-runs.json').read_text())
    assert len(records)==8 and len(supplement)==4 and all(row['exit_code']==0 for row in records+supplement)
    verification=json.loads((HERE/'complete-file-verification.json').read_text())
    broad=json.loads((HERE/'supplement-verification.json').read_text())
    assert verification['candidate_noninterference_accepted'] and broad['noninterference_accepted']
    images=[];controls=[];lookup={};all_paths={row['output'] for row in records+supplement}|{row['original'] for row in records}
    for path in sorted(all_paths):
        source=ROOT/path;destination=target/source.name
        audit.retain_run(source,destination,images);shutil.copy2(source/'console-review.log',destination/'console-review.log')
        result=json.loads((destination/'result.json').read_text())
        commands=[line for line in (destination/'scripts/game_start.scr').read_text().splitlines() if not line.startswith(('script','echo '))]
        require_console_command_acknowledgements(destination/'console-review.log',commands)
        require_synchronous_fixture_save(destination/'save/smoke-state.sav')
        assert result['background'] and result['original_allow_hidpi'] is False and result['image_size']==[640,480]
        assert result['original_console_commands_acknowledged']==len(commands) and result['original_console_save_success_recorded']
        controls.append({'control':str(destination.relative_to(ROOT)),'original':path,'actual_commands_acknowledged':len(commands),'actual_save_success_text':True})
        lookup[path]=destination
    comparisons=[];saved=[]
    for row in records:
        a,b=lookup[row['original']],lookup[row['output']]
        for scope,left,right,pattern in (('world',a/'screenshot/smoke.png',b/'screenshot/smoke.png','*'),
            ('atlas',a/'renderer3d-reference',b/'renderer3d-reference','model-world-atlas-*'),
            ('shore-gallery',a/'renderer3d-reference',b/'renderer3d-reference','model-voxel-river_bank_shore_study_*')):
            value=audit.compare(left,right,pattern,target/'strict-comparisons'/f"{row['climate']}-{row['backend']}-{scope}.json")
            assert value['exit_code']==0;comparisons.append(value)
        saved.append({'scope':row['climate']+'-'+row['backend'],'original_sha256':audit.digest(a/'save/smoke-state.sav'),
            'candidate_sha256':audit.digest(b/'save/smoke-state.sav'),'exact_original_save_bytes':(a/'save/smoke-state.sav').read_bytes()==(b/'save/smoke-state.sav').read_bytes()})
    for backend in ('vulkan','opengl'):
        a,b=[lookup[next(row['output'] for row in supplement if row['scope']==scope and row['backend']==backend)] for scope in ('original','candidate')]
        for scope,left,right,pattern in (('world',a/'screenshot/smoke.png',b/'screenshot/smoke.png','*'),
            ('atlas',a/'renderer3d-reference',b/'renderer3d-reference','model-world-atlas-*'),
            ('hq-gallery',a/'renderer3d-reference',b/'renderer3d-reference','model-voxel-hq_*')):
            value=audit.compare(left,right,pattern,target/'strict-comparisons'/f'supplement-{backend}-{scope}.json')
            assert value['exit_code']==0;comparisons.append(value)
        saved.append({'scope':'supplement-'+backend,'original_sha256':audit.digest(a/'save/smoke-state.sav'),
            'candidate_sha256':audit.digest(b/'save/smoke-state.sav'),'exact_original_save_bytes':(a/'save/smoke-state.sav').read_bytes()==(b/'save/smoke-state.sav').read_bytes()})
    assert all(row['exact_original_save_bytes'] for row in saved)
    (target/'lossless-images.json').write_text(json.dumps(images,indent=2)+'\n')
    value={'audited_utc':datetime.now(timezone.utc).isoformat(),'retained_controls':len(controls),'fresh_candidate_and_supplement_controls':12,
        'explicitly_reused_shore_baseline_controls':8,'controls':controls,'same_backend_comparisons':comparisons,
        'same_backend_exact_images':sum(row['images'] for row in comparisons),'same_backend_different_images':0,'same_backend_different_pixels':0,
        'exact_original_save_pairs':saved,'lossless_pam_reconstructions':len(images),
        'complete_original_pam_bytes_reconstructed':sum(row['original_bytes'] for row in images),
        'zero_heading_noninterference_accepted':True,'full_renderer_source_fidelity_or_60fps_accepted':False,'quality_approvals':0}
    (target/'verification.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('controls','same_backend_comparisons','exact_original_save_pairs')}))


if __name__=='__main__':main()

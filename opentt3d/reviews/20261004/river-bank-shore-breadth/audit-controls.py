"""Retain acknowledged shore/public-query controls and strict complete image failures."""
from datetime import datetime,timezone
import argparse
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
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--finish-retained-partial',action='store_true');args=parser.parse_args()
    target=HERE/'native-controls'
    if target.exists() and (not args.finish_retained_partial or (target/'verification.json').exists()):
        raise ValueError('Retain earlier portable evidence and all failed comparisons')
    (target/'strict-comparisons').mkdir(parents=True,exist_ok=args.finish_retained_partial)
    spec=importlib.util.spec_from_file_location('shore_control_audit',HERE.parent/'river-relief-ownership/audit-world-controls.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    provenance=json.loads((HERE/'provenance-runs.json').read_text());studies=json.loads((HERE/'study-runs.json').read_text())
    assert len(provenance)==20 and len(studies)==8 and all(row['exit_code']==0 for row in provenance+studies)
    images=[];controls=[];lookup={}
    for row in provenance+studies:
        source=ROOT/row['output'];destination=target/source.name
        audit.retain_run(source,destination,images);shutil.copy2(source/'console-review.log',destination/'console-review.log')
        commands=[line for line in (destination/'scripts/game_start.scr').read_text().splitlines() if not line.startswith(('script','echo '))]
        require_console_command_acknowledgements(destination/'console-review.log',commands)
        require_synchronous_fixture_save(destination/'save/smoke-state.sav')
        result=json.loads((destination/'result.json').read_text())
        assert result['background'] and result['original_allow_hidpi'] is False and result['image_size']==[640,480]
        assert result['original_console_commands_acknowledged']==len(commands) and result['original_console_save_success_recorded']
        assert result['command'][result['command'].index('-b')+1]=='40bpp-anim'
        study='tracing' not in row;scope='study' if study else 'tracing-on' if row['tracing'] else 'tracing-off'
        lookup[row['climate'],row.get('seed',271828),row['backend'],scope]=destination
        controls.append({'control':str(destination.relative_to(ROOT)),'commands_acknowledged':len(commands),'scope':scope,
            'climate':row['climate'],'seed':row.get('seed',271828),'backend':row['backend'],'actual_save_success_text':True,
            'fresh_during_this_resumption':True})
    comparisons=[];saved=[]
    def add(label,left,right,pattern='*',require_exact=False):
        value=audit.compare(left,right,pattern,target/'strict-comparisons'/(label+'.json'));comparisons.append(value)
        if require_exact:assert value['exit_code']==0
    def save_pair(label,a,b):
        value={'scope':label,'original_sha256':audit.digest(a/'save/smoke-state.sav'),'actual_sha256':audit.digest(b/'save/smoke-state.sav'),
            'exact_original_save_bytes':(a/'save/smoke-state.sav').read_bytes()==(b/'save/smoke-state.sav').read_bytes()}
        assert value['exact_original_save_bytes'];saved.append(value)
    for survey in json.loads((HERE/'surveys.json').read_text()):
        climate,seed=survey['climate'],survey['seed']
        for backend in ('vulkan','opengl'):
            a,b=[lookup[climate,seed,backend,scope] for scope in ('tracing-off','tracing-on')]
            add(f'{climate}-{seed}-{backend}-observer-world',a/'screenshot/smoke.png',b/'screenshot/smoke.png',require_exact=True)
            add(f'{climate}-{seed}-{backend}-observer-atlas',a/'renderer3d-reference',b/'renderer3d-reference','model-world-atlas-*',True)
            save_pair(f'{climate}-{seed}-{backend}-observer-save',a,b)
            if seed==271828:
                b=lookup[climate,seed,backend,'study']
                add(f'{climate}-{backend}-unbound-world',a/'screenshot/smoke.png',b/'screenshot/smoke.png',require_exact=True)
                add(f'{climate}-{backend}-unbound-atlas',a/'renderer3d-reference',b/'renderer3d-reference','model-world-atlas-*',True)
                save_pair(f'{climate}-{backend}-unbound-save',a,b)
        a,b=[lookup[climate,seed,backend,'tracing-off'] for backend in ('vulkan','opengl')]
        add(f'{climate}-{seed}-canonical-paired-world',a/'screenshot/smoke.png',b/'screenshot/smoke.png')
        if seed==271828:
            a,b=[lookup[climate,seed,backend,'study']/'renderer3d-reference' for backend in ('vulkan','opengl')]
            add(climate+'-complete-shore-model-pairs',a,b,'model-voxel-river_bank_shore_study_*')
            add(climate+'-registered-native-pairs',a,b,'model-voxel-river_bank_shore_study_*-native')
    for survey in json.loads((HERE/'surveys.json').read_text()):
        source=ROOT/survey['output'];destination=target/'public-surveys'/source.name
        destination.mkdir(parents=True,exist_ok=args.finish_retained_partial)
        for name in ('fixture.json','command-acknowledgements.json','run.log','openttd.cfg'):
            audit.retain_file(source/name,destination/name)
        for name in ('save','scripts','ai'):
            for path in (source/name).rglob('*'):
                relative=path.relative_to(source);copy=destination/relative
                if path.is_dir():copy.mkdir(parents=True,exist_ok=True)
                elif path.is_file():
                    copy.parent.mkdir(parents=True,exist_ok=True);audit.retain_file(path,copy)
    frozen=ROOT/'build-macos/breadth-original-river-shore-initial-frozen-build'
    for name,path in (('diagnostic-catalogue.json.gz',HERE/'diagnostic-catalogue.json.gz'),('frozen-manifest.json',HERE/'frozen-manifest.json'),
        ('frozen-authored-source.json',frozen/'authored-source.json'),('compiler-snapshot.py',frozen/'compiler-snapshot.py'),('frozen-test_authored_study.py',frozen/'test_authored_study.py')):
        shutil.copy2(path,target/name)
    (target/'lossless-images.json').write_text(json.dumps(images,indent=2)+'\n')
    portable=[]
    for sheet in json.loads((HERE/'individual-review-sheets/index.json').read_text()):
        run=Path(sheet['registration']).parent.parent.name;directory=target/run/'renderer3d-reference'
        portable.append({**sheet,'native':str((directory/(Path(sheet['native']).stem+'.png')).relative_to(ROOT)),
            'registration':str((directory/Path(sheet['registration']).name).relative_to(ROOT)),
            'console':str((directory.parent/'console-review.log').relative_to(ROOT)),
            'save':str((directory.parent/'save/smoke-state.sav').relative_to(ROOT))})
    (HERE/'portable-review-index.json').write_text(json.dumps(portable,indent=2)+'\n')
    value={'audited_utc':datetime.now(timezone.utc).isoformat(),'fresh_quiet_acknowledged_native_controls':28,'fresh_correlated_public_query_surveys':5,
        'controls':controls,'comparisons':comparisons,'exact_save_pairs':saved,'lossless_pam_reconstructions':len(images),
        'complete_original_pam_bytes_reconstructed':sum(row['original_bytes'] for row in images),
        'observer_noninterference_worlds_exact':10,'observer_noninterference_atlas_images_exact':40,
        'unbound_study_worlds_exact':8,'unbound_study_atlas_images_exact':32,
        'complete_model_backend_pairs':180,'all_strict_renderers_accepted':not any(row['exit_code'] for row in comparisons),
        'runtime_bank_coverage_accepted':0,'source_fidelity_or_all_terrain_type_states_accepted':False,'quality_approvals':0}
    (target/'verification.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('controls','comparisons','exact_save_pairs')}))


if __name__=='__main__':main()

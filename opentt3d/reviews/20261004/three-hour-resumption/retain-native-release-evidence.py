"""Portable retention of the independently downloaded app's acknowledged native controls."""
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
    value=json.loads((HERE/'independent-runtime-audit.json').read_text())
    assert value['accepted_scoped_native_runtime'] and not value['accepted_full_objective'] and value['quality_approvals']==0
    records=value['native_controls'];packages=value['package_controls']
    expected=6 if value.get('ci_preview_only') else 12
    assert len(records)==expected and len(packages)==2 and all(row['exit_code']==0 for row in records+packages)
    target=HERE/'independent-native-controls';assert not target.exists();target.mkdir()
    spec=importlib.util.spec_from_file_location('independent_native_retainer',HERE.parent/'river-relief-ownership/audit-world-controls.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    images=[];controls=[]
    for row in records:
        source=ROOT/row['output'];destination=target/source.name
        audit.retain_run(source,destination,images)
        audit.retain_file(source/'console-review.log',destination/'console-review.log')
        result=json.loads((destination/'result.json').read_text())
        assert result['background'] and result['original_allow_hidpi'] is False and result['image_size']==[640,480]
        assert result['synchronous_original_save_verified'] and result['original_console_save_success_recorded']
        assert 'threaded_saves = false' in (destination/'openttd.cfg').read_text()
        commands=[line for line in (destination/'scripts/game_start.scr').read_text().splitlines() if not line.startswith(('script','echo '))]
        require_console_command_acknowledgements(destination/'console-review.log',commands)
        require_synchronous_fixture_save(destination/'save/smoke-state.sav')
        assert result['original_console_commands_acknowledged']==len(commands)
        controls.append({'original':row['output'],'portable':str(destination.relative_to(ROOT)),
            'backend':row['backend'],'commands_acknowledged':len(commands),'actual_synchronous_save_success_text':True})
    for row in packages:
        source=ROOT/row['output'];destination=target/source.name;destination.mkdir()
        for name in ('run.log','result.json','openttd.cfg','benchmark.json','input.sav'):
            audit.retain_file(source/name,destination/name)
        for name in ('scripts','save','screenshot'):shutil.copytree(source/name,destination/name)
        assert 'background Cocoa window active=false, key=false, visible=false, policy=2' in (destination/'run.log').read_text()
        controls.append({'original':row['output'],'portable':str(destination.relative_to(ROOT)),
            'scope':'default-package-compatibility-only','quiet_background_verified':True,
            'unlogged_package_commands_or_independent_animation_retroactively_acknowledged':False})
    (target/'lossless-images.json').write_text(json.dumps(images,indent=2)+'\n')
    receipt={'retained_utc':datetime.now(timezone.utc).isoformat(),'independently_downloaded_signed_app':value['app'],
        'tag':value['tag'],'commit':value['commit'],'binary_sha256':value['binary_sha256'],'catalogue_sha256':value['catalogue_sha256'],
        'fresh_quiet_acknowledged_native_controls':expected,'separate_unlogged_default_package_compatibility_controls':2,
        'ci_preview_only':value.get('ci_preview_only',False),'accepted_publication':False,
        'controls':controls,'lossless_pam_reconstructions':len(images),
        'complete_original_pam_bytes_reconstructed':sum(row['original_bytes'] for row in images),
        'whole_catalogue_quality_renderer_60fps_or_all_platform_acceptance':False,'quality_approvals':0}
    (target/'retention.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({key:value for key,value in receipt.items() if key!='controls'}))


if __name__=='__main__':main()

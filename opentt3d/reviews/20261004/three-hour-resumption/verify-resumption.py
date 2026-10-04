"""Verify immutable publication, portable native bytes and the complete resumption record."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
MANIFEST=HERE/'resumption-evidence-sha256.json'
RECEIPT=HERE/'resumption-portable-verification.json'
sys.path.insert(0,str(ROOT/'tools/opentt3d'))
from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seal',action='store_true');args=parser.parse_args()
    publication=json.loads((HERE/'public-release43-verification.json').read_text())
    artifacts=json.loads((HERE/'independent-artifact-audit.json').read_text())
    runtime=json.loads((HERE/'independent-runtime-audit.json').read_text())
    assert publication['published'] and publication['prerelease'] and publication['quality_approvals']==0
    assert publication['anonymous_public_manifest_bytes_exact'] and publication['no_packaging_rebuild_observed']
    assert publication['recommended_release']=='opentt3d-dev-20261003.42' and not publication['latest_or_recommendation_changed']
    assert publication['tag']==artifacts['tag']==runtime['tag']=='opentt3d-dev-20261004.43'
    assert publication['commit']==artifacts['commit']==runtime['commit']=='ccd153ba5be8b779b666e469db735d3985ffbdd9'
    assert artifacts['source_and_all_downloaded_artifacts_exact'] and runtime['accepted_scoped_native_runtime'] and not runtime['accepted_full_objective']
    assert len(artifacts['assets'])==19 and len(artifacts['packages'])==6
    assert hashlib.sha256((HERE/'public-anonymous-SHA256SUMS').read_bytes()).hexdigest()==artifacts['manifest_sha256']
    native=HERE/'independent-native-controls';retention=json.loads((native/'retention.json').read_text())
    assert retention['fresh_quiet_acknowledged_native_controls']==12 and retention['separate_unlogged_default_package_compatibility_controls']==2
    count,original_bytes=0,0
    for row in json.loads((native/'lossless-images.json').read_text()):
        path=ROOT/row['portable'];assert digest(path)==row['png_sha256']
        with Image.open(path) as picture:
            assert picture.mode=='RGBA' and list(picture.size)==row['size']
            payload=picture.info['opentt3d_pam_header'].encode('ascii')+picture.tobytes()
        assert len(payload)==row['original_bytes'] and hashlib.sha256(payload).hexdigest()==row['pam_sha256']
        count+=1;original_bytes+=len(payload)
    assert count==retention['lossless_pam_reconstructions'] and original_bytes==retention['complete_original_pam_bytes_reconstructed']
    for row in retention['controls']:
        run=ROOT/row['portable']
        if row.get('scope')=='default-package-compatibility-only':
            assert row['unlogged_package_commands_or_independent_animation_retroactively_acknowledged'] is False
            continue
        commands=[line for line in (run/'scripts/game_start.scr').read_text().splitlines() if not line.startswith(('script','echo '))]
        require_console_command_acknowledgements(run/'console-review.log',commands)
        require_synchronous_fixture_save(run/'save/smoke-state.sav')
        assert len(commands)==row['commands_acknowledged']
    for name,row in json.loads((HERE/'pre-integration-preservation.json').read_text())['original_working_files'].items():
        path=ROOT/row['retained'];payload=gzip.decompress(path.read_bytes())
        assert digest(path)==row['retained_sha256'] and hashlib.sha256(payload).hexdigest()==row['original_sha256']
        assert len(payload)==row['original_bytes']
    prior=json.loads((HERE/'all-sealed-evidence-integrity-corrected.json').read_text())
    assert prior['sealed_manifests']==21 and prior['file_records_checked']==46452 and not prior['mismatches']
    for row in prior['results']:
        manifest=ROOT/row['manifest'];assert digest(manifest)==row['manifest_sha256']
        files=json.loads(manifest.read_text())['files']
        for key,record in files.items():
            relative=Path(key);path=ROOT/relative if relative.parts[0]=='opentt3d' else manifest.parent/relative
            assert digest(path)==(record['sha256'] if isinstance(record,dict) else record)
    stop=json.loads((HERE/'STOPPING.json').read_text())
    assert stop['start_utc']=='2026-10-04T16:20:27Z' and stop['requested_deadline_utc']=='2026-10-04T19:20:27Z'
    assert stop['actual_stopping_utc'] and stop['reason'] and not stop['full_objective_met']
    assert stop['published_release']==publication['url'] and stop['recommended_release_changed'] is False
    files=sorted(path for path in HERE.rglob('*') if path.is_file() and path not in {MANIFEST,RECEIPT}
        and '__pycache__' not in path.parts and path.suffix!='.pyc' and not path.name.startswith('resumption-verify-command'))
    hashes={str(path.relative_to(HERE)):{'sha256':digest(path),'bytes':path.stat().st_size} for path in files}
    if args.seal:
        with MANIFEST.open('x') as stream:json.dump({'format':1,'files':hashes,'quality_approved':False},stream,indent=2);stream.write('\n')
    assert json.loads(MANIFEST.read_text())['files']==hashes,'Changed, incomplete or missing resumption evidence is not accepted'
    receipt={'verified_utc':datetime.now(timezone.utc).isoformat(),'portable_files':len(files),'tag':publication['tag'],
        'release_commit':publication['commit'],'published_url':publication['url'],'hosted_attachments_exact':19,
        'immutable_tagged_source_files_exact':artifacts['exact_source_files'],'exact_packaged_catalogues':6,
        'fresh_acknowledged_downloaded_app_native_controls':12,'lossless_pam_reconstructions':count,
        'complete_original_pam_bytes_reconstructed':original_bytes,'prior_sealed_manifests_exact':21,
        'prior_sealed_file_records_exact':46452,'original_working_files_exact':7,'actual_stopping_utc':stop['actual_stopping_utc'],
        'all_source_or_8_or_60fps_or_platform_gates_accepted':False,'quality_approvals':0,'recommended_release_changed':False}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()

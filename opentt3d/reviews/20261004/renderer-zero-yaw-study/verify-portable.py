"""Verify exact native colour/picking/pose evidence for the zero-heading identity branch."""
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
MANIFEST=HERE/'evidence-sha256.json'
RECEIPT=HERE/'portable-verification.json'
sys.path.insert(0,str(ROOT/'tools/opentt3d'))
from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save
sys.path.insert(0,str(ROOT/'tools/assets'))
from compare_galleries import captures,image


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seal',action='store_true');args=parser.parse_args()
    native=HERE/'native-controls';value=json.loads((native/'verification.json').read_text())
    corrected=json.loads((HERE/'complete-file-verification.json').read_text());supplement=json.loads((HERE/'supplement-verification.json').read_text())
    assert value['zero_heading_noninterference_accepted'] and corrected['candidate_noninterference_accepted'] and supplement['noninterference_accepted']
    assert corrected['same_backend_images']==400 and corrected['same_backend_different_images']==corrected['same_backend_different_pixels']==0
    assert supplement['hq_models']==116 and supplement['vehicle_pose_engine_matrices']==[26,160,204,248,253]
    assert supplement['same_backend_different_images']==supplement['same_backend_different_pixels']==0
    assert len(value['controls'])==20 and len(value['exact_original_save_pairs'])==10
    assert all(row['exact_original_save_bytes'] for row in value['exact_original_save_pairs'])
    count,original_bytes=0,0
    for row in json.loads((native/'lossless-images.json').read_text()):
        path=ROOT/row['portable'];assert digest(path)==row['png_sha256']
        with Image.open(path) as picture:
            assert picture.mode=='RGBA' and list(picture.size)==row['size']
            payload=picture.info['opentt3d_pam_header'].encode('ascii')+picture.tobytes()
        assert len(payload)==row['original_bytes'] and hashlib.sha256(payload).hexdigest()==row['pam_sha256']
        count+=1;original_bytes+=len(payload)
    assert count==value['lossless_pam_reconstructions'] and original_bytes==value['complete_original_pam_bytes_reconstructed']
    for row in value['controls']:
        run=ROOT/row['control'];result=json.loads((run/'result.json').read_text())
        assert result['background'] and result['original_allow_hidpi'] is False and result['image_size']==[640,480]
        assert result['command'][result['command'].index('-b')+1]=='40bpp-anim'
        assert 'threaded_saves = false' in (run/'openttd.cfg').read_text()
        commands=[line for line in (run/'scripts/game_start.scr').read_text().splitlines() if not line.startswith(('script','echo '))]
        require_console_command_acknowledgements(run/'console-review.log',commands);require_synchronous_fixture_save(run/'save/smoke-state.sav')
        assert result['original_console_commands_acknowledged']==len(commands) and result['original_console_save_success_recorded']
    compared=0
    for entry in value['same_backend_comparisons']:
        report=json.loads((ROOT/entry['report']).read_text());assert report['exit_code']==0 and report['images']>0
        a,b=ROOT/report['reference'],ROOT/report['actual']
        left,right=({'world':a},{'world':b}) if a.is_file() and b.is_file() else (captures(a,report['pattern']),captures(b,report['pattern']))
        assert left and left.keys()==right.keys() and len(left)==report['images']
        for name,path in left.items():
            x,y=image(path),image(right[name]);assert x.size==y.size and x.tobytes()==y.tobytes()
            compared+=1
    assert compared==value['same_backend_exact_images']
    assert digest(HERE/'verification.json')==corrected['rejected_directory_lookup_audit_sha256']
    assert corrected['original_audit_world_claim_rejected'] and corrected['all_worlds_and_galleries_nonempty_and_complete']
    assert not value['full_renderer_source_fidelity_or_60fps_accepted'] and value['quality_approvals']==0
    freeze=json.loads((HERE/'frozen-manifest.json').read_text())
    assert hashlib.sha256(gzip.decompress((HERE/'approved-gl-backend.cpp.gz').read_bytes())).hexdigest()==freeze['gl_backend_candidate_sha256']
    timing=json.loads((HERE/'bounded-timing.json').read_text())
    assert timing['frames_per_backend']==1800 and len(timing['observations'])==2
    assert [row['intervals_over_20_ms'] for row in timing['observations']]==[421,181]
    assert not any(row['sustained_60fps_accepted'] for row in timing['observations'])
    retention=json.loads((HERE/'bounded-timing-controls/retention.json').read_text())
    assert all(digest(HERE/'bounded-timing-controls'/name)==row['sha256'] for name,row in retention['files'].items())
    for row in retention['controls']:
        run=ROOT/row['portable'];result=json.loads((run/'result.json').read_text())
        assert result['original_console_save_success_recorded'] and result['synchronous_original_save_verified']
        require_synchronous_fixture_save(run/'save/smoke-state.sav')
        commands=[line for line in (run/'scripts/game_start.scr').read_text().splitlines() if not line.startswith(('script','echo '))]
        require_console_command_acknowledgements(run/'console-review.log',commands)
    files=sorted(path for path in HERE.rglob('*') if path.is_file() and path not in {MANIFEST,RECEIPT} and '__pycache__' not in path.parts
        and path.suffix!='.pyc' and not path.name.startswith('portable-verify-command'))
    hashes={str(path.relative_to(HERE)):{'sha256':digest(path),'bytes':path.stat().st_size} for path in files}
    if args.seal:MANIFEST.write_text(json.dumps({'format':1,'files':hashes,'quality_approved':False},indent=2)+'\n')
    assert json.loads(MANIFEST.read_text())['files']==hashes,'Do not silently accept changed or missing native evidence'
    receipt={'verified_utc':datetime.now(timezone.utc).isoformat(),'portable_files':len(files),'lossless_pam_reconstructions':count,
        'complete_original_pam_bytes_reconstructed':original_bytes,'complete_nonempty_same_backend_images_exact':compared,
        'fresh_candidate_and_supplement_controls':12,'explicitly_reused_shore_baseline_controls':8,'exact_original_save_pairs':10,
        'hq_models':116,'vehicle_pose_engine_matrices':[26,160,204,248,253],'all_prior_empty_world_claims_rejected_and_corrected':True,
        'zero_heading_identity_branch_noninterference_accepted':True,'source_fidelity_or_60fps_or_full_renderers_accepted':False,'quality_approvals':0}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()

"""Reverify exact shore volumes, public queries, raw bytes and below-eight reviews."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
MANIFEST=HERE/'evidence-sha256.json'
RECEIPT=HERE/'portable-verification.json'
sys.path.insert(0,str(ROOT/'tools/assets'))
from compare_galleries import image
from quality_audit import fingerprint,REVIEW_CHECKS
sys.path.insert(0,str(ROOT/'tools/opentt3d'))
from fixture_rivers import validate_survey
from smoke import require_console_command_acknowledgements,require_synchronous_fixture_save


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seal',action='store_true');args=parser.parse_args()
    native=HERE/'native-controls';freeze=json.loads((native/'frozen-manifest.json').read_text())
    payload=gzip.decompress((native/'diagnostic-catalogue.json.gz').read_bytes())
    assert hashlib.sha256(payload).hexdigest()==freeze['sha256']['baseset/opentt3d-voxels.json']
    catalogue=json.loads(payload);assert len(catalogue['models'])==2035
    base=json.loads(gzip.decompress((HERE/'canonical-catalogue.json.gz').read_bytes()))
    prior=json.loads(gzip.decompress((HERE.parent/'river-bank-snow-breadth/diagnostic-catalogue.json.gz').read_bytes()))
    assert len(base['models'])==1915 and catalogue['bindings']==base['bindings']==prior['bindings']
    assert all(catalogue['models'][name]==model for name,model in base['models'].items())
    assert all(fingerprint(model,prior['materials'])==fingerprint(catalogue['models'][name],catalogue['materials']) for name,model in prior['models'].items())
    assert all(int(layout)<12 for category in ('objects','object_ground') for layout in catalogue['bindings'][category])
    for original,name in (('compiler-snapshot.py','compiler-snapshot.py'),('authored-source.json','frozen-authored-source.json'),('test_authored_study.py','frozen-test_authored_study.py')):
        assert digest(native/name)==freeze['sha256'][original]
    spec=importlib.util.spec_from_file_location('portable_shore_compiler',native/'compiler-snapshot.py')
    compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
    study=compiler.compile_catalogue(json.loads((native/'frozen-authored-source.json').read_text()))
    assert len(study['models'])==20 and study['bindings']=={}
    assert all(fingerprint(model,study['materials'])==fingerprint(catalogue['models'][name],catalogue['materials']) for name,model in study['models'].items())
    count,original_bytes=0,0
    for row in json.loads((native/'lossless-images.json').read_text()):
        path=ROOT/row['portable'];assert digest(path)==row['png_sha256']
        with Image.open(path) as picture:
            assert picture.mode=='RGBA' and list(picture.size)==row['size']
            original=picture.info['opentt3d_pam_header'].encode('ascii')+picture.tobytes()
        assert len(original)==row['original_bytes'] and hashlib.sha256(original).hexdigest()==row['pam_sha256']
        count+=1;original_bytes+=len(original)
    assert count==994 and original_bytes==346242848
    verification=json.loads((native/'verification.json').read_text())
    assert len(verification['controls'])==28 and len(verification['exact_save_pairs'])==18
    assert all(row['exact_original_save_bytes'] for row in verification['exact_save_pairs'])
    assert not verification['all_strict_renderers_accepted'] and verification['runtime_bank_coverage_accepted']==verification['quality_approvals']==0
    for row in verification['controls']:
        run=ROOT/row['control'];result=json.loads((run/'result.json').read_text())
        assert result['background'] and result['original_allow_hidpi'] is False and result['image_size']==[640,480]
        assert result['command'][result['command'].index('-b')+1]=='40bpp-anim'
        assert 'threaded_saves = false' in (run/'openttd.cfg').read_text()
        commands=[line for line in (run/'scripts/game_start.scr').read_text().splitlines() if not line.startswith(('script','echo '))]
        require_console_command_acknowledgements(run/'console-review.log',commands);require_synchronous_fixture_save(run/'save/smoke-state.sav')
        assert result['original_console_commands_acknowledged']==len(commands) and result['original_console_save_success_recorded']
    surveys=json.loads((HERE/'surveys.json').read_text());assert len(surveys)==5
    public={}
    for row in surveys:
        run=native/'public-surveys'/Path(row['output']).name;data=json.loads((run/'fixture.json').read_text())
        assert digest(run/'fixture.json')==row['fixture_sha256'] and data['public_terrain_type_queries']
        assert data['survey_token']==row['survey_token'] and data['loaded_original_world_not_regenerated']
        validate_survey(data,data['tiles']);require_synchronous_fixture_save(run/data['save'])
        assert digest(run/data['save'])==data['save_sha256']==row['original_save_sha256']
        acknowledgements=json.loads((run/'command-acknowledgements.json').read_text())
        assert len(acknowledgements)==4 and str(data['survey_token']) in acknowledgements[1]['command']
        assert 'Map successfully saved' in acknowledgements[3]['acknowledgement'] and 'Map successfully saved' in (run/'run.log').read_text()
        assert data['input_save_sha256']==row['input_original_save_sha256']
        public[row['climate'],row['seed']]={tile['tile']:tile for tile in data['tiles']}
    for row in json.loads((HERE/'actual-terrain-selector-observations.json').read_text()):
        tile=public[row['climate_name'],row['seed']][row['tile']]
        assert row['public_terrain_type_query_performed'] and row['public_terrain_type']==tile['public_terrain_type']
        assert row['slope']==tile['slope'] and row['source_height']==tile['min_height_levels']*8 and row['tile_xy']==[tile['x'],tile['y']]
    sources=json.loads((HERE/'actual-source-index.json').read_text());assert len(sources)==20
    assert Counter(row['climate_name'] for row in sources)=={'temperate':6,'arctic':4,'tropic':4,'toyland':6}
    for source in sources:
        assert source['source_height']==0 and source['public_terrain_type_query_performed'] and source['source_wave_fringe_preserved']
        assert not source['quality_approved'] and not source['runtime_bound'] and digest(ROOT/source['source_pam'])==source['source_pam_sha256']
    reviews=json.loads((HERE/'current-quality-reviews.json').read_text())['models']
    assert len(reviews)==20 and Counter(row['score'] for row in reviews.values())=={4:10,5:10}
    for name,row in reviews.items():
        assert row['defects'] and set(row['checks'])==set(REVIEW_CHECKS) and not any(row['checks'].values())
        assert row['fingerprint']==fingerprint(catalogue['models'][name],catalogue['materials'])
        assert set(row['evidence'])==set(row['evidence_sha256']) and all(digest(ROOT/path)==sha for path,sha in row['evidence_sha256'].items())
    instances=json.loads((HERE/'diagnostic-source-instance-records.json').read_text())
    assert len(instances)==20 and all(row['score']==3 and not row['runtime_bound'] and not row['quality_approved'] for row in instances)
    spec=importlib.util.spec_from_file_location('raw_shore_recheck',HERE.parent/'river-sloped-bank-breadth/registered-bytes.py')
    raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
    source_audit=json.loads((HERE/'source-native-audit.json').read_text());assert source_audit['models']==source_audit['different_images']==20
    assert source_audit['all_raw_image_bytes_preserved_without_alpha_compositing'] and not source_audit['source_wave_pixels_removed']
    sheets={row['model']:row for row in json.loads((HERE/'portable-review-index.json').read_text())}
    sources={f"river_bank_shore_study_{row['climate_name']}_offset{row['requested_offset']:02d}":row for row in sources}
    for row in source_audit['rows']:
        source=sources[row['model']];sheet=sheets[row['model']]
        original=raw.registered(image(ROOT/source['source_pam']),source['native_offset'])
        model=raw.native(image(ROOT/sheet['native']),json.loads((ROOT/sheet['registration']).read_text()))
        (a,b),bounds=raw.pair(original,model);x,y=a.tobytes(),b.tobytes()
        assert list(bounds)==row['shared_bounds'] and list(original[1])==row['raw_source_bounds'] and list(model[1])==row['raw_native_bounds']
        assert sum(x[index:index+4]!=y[index:index+4] for index in range(0,len(x),4))==row['complete_rgba_changed_pixels']
        assert sum(bool(x[index+3])!=bool(y[index+3]) for index in range(0,len(x),4))==row['alpha_presence_differences_additional_diagnostic']
    gallery=json.loads((HERE/'backend-gallery-audit.json').read_text())
    assert gallery['images']==180 and gallery['different_images']==35 and gallery['different_pixels']==165
    assert all(row['exit_code']==0 for row in verification['comparisons'] if '-observer-' in row['label'] or '-unbound-' in row['label'])
    state=json.loads((HERE/'state-breadth-inventory.json').read_text())
    assert state['conditional_bank_shape_slots']==240 and state['earlier_conditional_slots_unobserved']==160 and state['new_conditional_shape_slots_claimed']==0
    gate=json.loads((HERE/'required-eight-gate-receipt.json').read_text());report=json.loads((HERE/'current-full-catalogue-quality.json').read_text())
    assert gate['exit_code']==1 and gate['quality_rows']==len(report['models'])==3070 and gate['coverage_gaps']==4 and not report['meets_objective']
    assert sum(row['status']=='individually-reviewed' for row in report['models'])==261 and not [row for row in report['models'] if row['score']>=8]
    files=sorted(path for path in HERE.rglob('*') if path.is_file() and path not in {MANIFEST,RECEIPT} and '__pycache__' not in path.parts
        and path.suffix!='.pyc' and not path.name.startswith('portable-verify-command'))
    hashes={str(path.relative_to(HERE)):{'sha256':digest(path),'bytes':path.stat().st_size} for path in files}
    if args.seal:MANIFEST.write_text(json.dumps({'format':1,'files':hashes,'quality_approved':False},indent=2)+'\n')
    assert json.loads(MANIFEST.read_text())['files']==hashes,'Changed or missing evidence is never silently accepted'
    value={'verified_utc':datetime.now(timezone.utc).isoformat(),'portable_files':len(files),'lossless_pam_reconstructions':count,
        'complete_original_pam_bytes_reconstructed':original_bytes,'fresh_quiet_acknowledged_controls':28,'fresh_correlated_public_query_surveys':5,
        'individual_shore_model_screenings':20,'independent_source_instance_screenings':20,'earlier_bank_models_exact':100,
        'canonical_1831_models_and_bindings_exact':True,'unbound_larger_hq_models_retained':84,'raw_source_native_failures_recomputed':True,
        'source_native_failed_pixels':source_audit['different_pixels'],'alpha_presence_differences_additional_diagnostic':source_audit['silhouette_differences_additional_diagnostic'],
        'complete_backend_model_failed_views':35,'complete_backend_model_failed_pixels':165,
        'runtime_bank_coverage_accepted':0,'quality_approvals':0,'required_eight_met':False,'recommended_release_changed':False}
    RECEIPT.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':main()

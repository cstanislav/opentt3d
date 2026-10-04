"""Separate individual shore-model and original-source-instance structural screenings."""
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PRIOR=HERE.parent/'river-bank-snow-breadth'
sys.path.insert(0,str(ROOT/'tools/assets'))
from inventory import inventory
from quality_audit import audit,definition_fingerprint,fingerprint,REVIEW_CHECKS,write_ratings_csv

COMMON=[
    'Unbound shore studies do not render in these original saved worlds. Exact original-world, atlas, save and original picking noninterference is not bank-specific live ownership, placement, ship clearance or state acceptance.',
    'The entire original sea wave fringe remains in the unmasked raw source/native comparison. Bank-only solid geometry does not establish a new independent bank/water split or original animated wave ownership.',
    'Original undoubled slope and four-cell maximum thickness are structural constraints only. Extra doubled-terrain support, all heights, neighbour joins, LOD retirement/restoration, custom/incomplete/intentional absence and bank-specific picking remain open.',
    'Fresh public AITile terrain-type queries observe particular normal/rainforest/snow tiles, not every desert/snowline/shore/grid/grass/parameter/callback input. Public snow code3 is not raw NewGRF0x81 code4. Missing conditional slots remain unobserved, never declared absent.',
    'Every source/backend mismatch is retained without cropping, resize, mask or tolerance. The every-runtime-asset3D/every-model8/10 and sustained60fps/memory/platform/input/replay/network objective remains unmet; no source instance inherits a model score or approval.'
]


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    if (HERE/'individual-decisions.json').exists():raise ValueError('Retain every earlier shore review')
    catalogue=json.loads(gzip.decompress((HERE/'diagnostic-catalogue.json.gz').read_bytes()))
    notes=json.loads((HERE/'review-observations.json').read_text())['models']
    sources=json.loads((HERE/'actual-source-index.json').read_text());sheets=json.loads((HERE/'portable-review-index.json').read_text())
    assert len(notes)==len(sources)==len(sheets)==20 and {row['model'] for row in sheets}==set(notes)
    reviewed={'format':1,'models':{}};instances=[]
    for source in sources:
        name=f"river_bank_shore_study_{source['climate_name']}_offset{source['requested_offset']:02d}";note=notes[name]
        assert note['score'] in (4,5) and note['defect'] and note['individually_inspected_source_native_orbit_street'] is True
        sheet=next(row for row in sheets if row['model']==name);directory=(ROOT/sheet['registration']).parent
        paths=[ROOT/sheet[key] for key in ('sheet','source_pam','registration','native','console','save')]
        paths.extend([HERE/'review-observations.json',HERE/'source-native-audit.json',HERE/'native-controls/verification.json',
            HERE/'authored-source.json',HERE/'source-retention-receipt.json',HERE/'surveys.json',HERE/'actual-source-index.json',
            HERE.parent/'river-sloped-bank-breadth/registered-bytes.py'])
        paths.extend(directory/('model-voxel-'+name+f'-{view}.png') for view in range(8))
        evidence=[str(path.relative_to(ROOT)) for path in paths];defects=[note['defect'],*COMMON]
        row={'score':note['score'],'fingerprint':fingerprint(catalogue['models'][name],catalogue['materials']),
            'checks':{check:False for check in REVIEW_CHECKS},'defects':defects,'evidence':evidence,
            'evidence_sha256':{path:digest(ROOT/path) for path in evidence},
            'notes':[f"Individually inspected particular shore-bank complete-source/native/four-orbit/four-street {note['score']}/10 structural screening, not aesthetic or runtime approval.",*defects]}
        reviewed['models'][name]=row
        instances.append({'source':source,'study_model':name,'representation':'unbound-diagnostic-source-instance','score':3,
            'fingerprint':definition_fingerprint({'source':source,'model_fingerprint':row['fingerprint']}),
            'checks':{check:False for check in REVIEW_CHECKS},'defects':defects,'evidence':evidence,'evidence_sha256':row['evidence_sha256'],
            'runtime_bound':False,'quality_approved':False,'note':'Independent actual-source instance structural screening; no geometry score or terrain/conditional coverage is inherited.'})
    (HERE/'current-quality-reviews.json').write_text(json.dumps(reviewed,indent=2)+'\n')
    (HERE/'diagnostic-source-instance-records.json').write_text(json.dumps(instances,indent=2)+'\n')
    combined=json.loads((PRIOR/'current-combined-quality-reviews.json').read_text())
    hq=json.loads((ROOT/'opentt3d/reviews/20261003/hq-large-column-repair/prototype-quality-reviews.json').read_text())
    assert len(hq['models'])==84 and not combined['models'].keys()&hq['models'].keys()
    assert all(row['fingerprint']==fingerprint(catalogue['models'][name],catalogue['materials']) for name,row in hq['models'].items())
    combined['models'].update(hq['models']);combined['models'].update(reviewed['models'])
    scope=inventory(catalogue);report=audit(catalogue,combined,scope=scope)
    assert len(report['models'])==3070 and len(report['coverage_gaps'])==4 and not report['meets_objective']
    assert sum(row['status']=='individually-reviewed' for row in report['models'])==261
    assert not [row for row in report['models'] if row['score']>=8]
    for name,value in (('current-combined-quality-reviews.json',combined),('exact-current-catalogue-inventory.json',scope),('current-full-catalogue-quality.json',report)):
        (HERE/name).write_text(json.dumps(value,indent=2)+'\n')
    write_ratings_csv(HERE/'current-full-catalogue-ratings.csv',report['models'])
    command=[sys.executable,'tools/assets/quality_audit.py','--catalogue','build-macos/breadth-original-river-shore-initial-frozen-build/baseset/opentt3d-voxels.json',
        '--reviews',str(HERE/'current-combined-quality-reviews.json'),'--inventory',str(HERE/'exact-current-catalogue-inventory.json'),
        '--output',str(HERE/'required-eight-quality.json'),'--require-eight']
    with (HERE/'required-eight.log').open('x') as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==1
    gate={'command':command,'exit_code':1,'required_eight_met':False,'quality_rows':3070,'individually_reviewed_rows':261,'coverage_gaps':4,'quality_approvals':0}
    (HERE/'required-eight-gate-receipt.json').write_text(json.dumps(gate,indent=2)+'\n')
    state={'reviewed_utc':datetime.now(timezone.utc).isoformat(),'conditional_bank_shape_slots':240,'earlier_conditional_slots_unobserved':160,
        'new_conditional_shape_slots_claimed':0,'earlier_unbound_bank_models_exact':100,'new_separate_shore_studies':20,
        'overlap_with_prior_particular_sea_level_observations_not_claimed_as_new_slots':True,
        'fresh_public_query_surveys':5,'all_desert_parameter_grid_grass_snowline_and_callback_inputs_accepted':False,
        'runtime_bank_coverage_accepted':0,'quality_approvals':0}
    (HERE/'state-breadth-inventory.json').write_text(json.dumps(state,indent=2)+'\n')
    value={'reviewed_utc':datetime.now(timezone.utc).isoformat(),'individual_shore_models':20,'independent_source_instance_screenings':20,
        'individual_model_scores':{name:row['score'] for name,row in reviewed['models'].items()},'exact_diagnostic_quality_rows':3070,
        'individually_reviewed_rows':261,'coverage_gaps':4,'unbound_larger_hq_reviews_retained':84,'earlier_bank_models_exact':100,
        'runtime_bindings_added':0,'quality_approvals':0,'required_eight_met':False,'recommended_release_changed':False}
    (HERE/'individual-decisions.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':main()

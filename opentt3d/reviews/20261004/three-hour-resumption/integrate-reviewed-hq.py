"""Keep every existing review and add exact unbound HQ reviews, without promotion."""
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools/assets'))
from inventory import inventory
from quality_audit import audit,fingerprint,write_ratings_csv


def main():
    receipt=HERE/'playable-quality-integration.json'
    if receipt.exists():raise ValueError('Retain the original integration and ratings audit')
    path=ROOT/'assets/3d/quality_reviews.json';payload=path.read_bytes();reviews=json.loads(payload)
    assert len(reviews['models'])==57
    with (HERE/'pre-integration-quality_reviews.json.gz').open('xb') as stream:stream.write(gzip.compress(payload,mtime=0))
    hq=json.loads((ROOT/'opentt3d/reviews/20261003/hq-large-column-repair/prototype-quality-reviews.json').read_text())
    assert len(hq['models'])==84 and not reviews['models'].keys()&hq['models'].keys()
    catalogue_path=ROOT/'build-macos/baseset/opentt3d-voxels.json';catalogue=json.loads(catalogue_path.read_text())
    assert len(catalogue['models'])==1915
    for category in ('objects','object_ground'):assert all(int(layout)<12 for layout in catalogue['bindings'][category])
    assert all(row['fingerprint']==fingerprint(catalogue['models'][name],catalogue['materials']) for name,row in hq['models'].items())
    reviews['models'].update(hq['models'])
    path.write_text(json.dumps(reviews,indent=2)+'\n')
    assert all(json.loads(payload)['models'][name]==reviews['models'][name] for name in json.loads(payload)['models'])
    scope=inventory(catalogue);report=audit(catalogue,reviews,scope=scope)
    assert len(report['models'])==2950 and sum(row['status']=='individually-reviewed' for row in report['models'])==141
    assert len(report['coverage_gaps'])==4 and not report['meets_objective'] and not [row for row in report['models'] if row['score']>=8]
    for name,value in (('playable-catalogue-inventory.json',scope),('playable-catalogue-quality.json',report)):
        (HERE/name).write_text(json.dumps(value,indent=2)+'\n')
    write_ratings_csv(ROOT/'opentt3d/MODEL_RATINGS.csv',report['models'])
    command=[sys.executable,'tools/assets/quality_audit.py','--catalogue',str(catalogue_path),'--reviews',str(path),
        '--inventory',str(HERE/'playable-catalogue-inventory.json'),'--output',str(HERE/'playable-required-eight-quality.json'),'--require-eight']
    with (HERE/'playable-required-eight.log').open('x') as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==1
    value={'integrated_utc':datetime.now(timezone.utc).isoformat(),'existing_reviews_preserved_exactly':57,'unbound_larger_hq_reviews_added_exactly':84,
        'playable_catalogue_models':1915,'playable_quality_rows':2950,'individually_reviewed_rows':141,'coverage_gaps':4,
        'prior_working_2998_row_diagnostic_ratings_retained_byte_exact_in_preservation_archive':True,
        'runtime_larger_hq_bindings_added':0,'quality_approvals':0,'required_eight_met':False,'required_eight_exit_code':1,
        'original_reviews_sha256':hashlib.sha256(payload).hexdigest(),'integrated_reviews_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'ratings_sha256':hashlib.sha256((ROOT/'opentt3d/MODEL_RATINGS.csv').read_bytes()).hexdigest(),'required_eight_command':command}
    receipt.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':main()

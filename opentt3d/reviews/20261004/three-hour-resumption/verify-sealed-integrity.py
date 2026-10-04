"""Recheck each sealed manifest using its explicit historical path schema."""
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def evidence_path(manifest,key):
    relative=Path(key)
    if not key or relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Sealed evidence keys must be nonempty relative paths without traversal')
    # Earlier complete manifests used repository-relative opentt3d/... keys.
    # Later portable manifests explicitly use their own directory as root.
    # Never guess an alternate root merely because a file is missing.
    return ROOT/relative if relative.parts[0]=='opentt3d' else manifest.parent/relative


def main():
    results=[];errors=[];records=0
    for manifest in sorted((ROOT/'opentt3d/reviews').rglob('evidence-sha256.json')):
        files=json.loads(manifest.read_text()).get('files')
        if not isinstance(files,dict) or not files:raise ValueError(f'Unsupported or empty manifest: {manifest}')
        mismatches=[];count=0
        for key,row in files.items():
            path=evidence_path(manifest,key)
            expected=row['sha256'] if isinstance(row,dict) else row
            if not path.is_file():mismatches.append({'file':key,'reason':'missing'});continue
            actual=digest(path)
            if actual!=expected or (isinstance(row,dict) and 'bytes' in row and path.stat().st_size!=row['bytes']):
                mismatches.append({'file':key,'reason':'changed','actual_sha256':actual,'expected_sha256':expected})
            count+=1
        records+=count
        results.append({'manifest':str(manifest.relative_to(ROOT)),'manifest_sha256':digest(manifest),
            'file_records_checked':count,'mismatches':mismatches})
        errors.extend(mismatches)
    assert len(results)==21
    assert records==46452 and not errors,'Do not silently reseal missing or changed original evidence'
    preservation=json.loads((HERE/'pre-integration-preservation.json').read_text())
    originals={}
    for name,row in preservation['original_working_files'].items():
        path=ROOT/row['retained'];payload=gzip.decompress(path.read_bytes())
        assert digest(path)==row['retained_sha256'] and len(payload)==row['original_bytes']
        assert hashlib.sha256(payload).hexdigest()==row['original_sha256']
        originals[name]=row['original_sha256']
    assert len(originals)==7
    previous=json.loads(gzip.decompress((HERE/'pre-integration-voxels.json.gz').read_bytes()))
    current=json.loads((ROOT/'assets/3d/voxels.json').read_text())
    assert all(previous[key]==current[key] for key in ('models','components','materials'))
    assert len(current['models'])==1915
    diagnostic=json.loads((ROOT/'assets/3d/hq-diagnostic-bindings.json').read_text())
    assert diagnostic['runtime_enabled'] is False
    bindings=json.loads(json.dumps(current['bindings']))
    for category,owners in diagnostic['bindings'].items():
        assert not bindings[category].keys()&owners.keys()
        bindings[category].update(owners)
    assert bindings==previous['bindings']
    original_reviews=json.loads(gzip.decompress((HERE/'pre-integration-quality_reviews.json.gz').read_bytes()))
    current_reviews=json.loads((ROOT/'assets/3d/quality_reviews.json').read_text())
    assert len(original_reviews['models'])==57 and len(current_reviews['models'])==141
    assert all(row==current_reviews['models'][name] for name,row in original_reviews['models'].items())
    hq=json.loads((ROOT/'opentt3d/reviews/20261003/hq-large-column-repair/prototype-quality-reviews.json').read_text())
    assert len(hq['models'])==84 and all(row==current_reviews['models'][name] for name,row in hq['models'].items())
    value={'verified_utc':datetime.now(timezone.utc).isoformat(),'sealed_manifests':len(results),
        'file_records_checked':records,'mismatches':errors,'results':results,'historical_manifest_or_stopping_clock_changes':False,
        'seven_original_working_files_reconstructed_exact':originals,'all_original_authored_models_components_materials_exact':True,
        'diagnostic_plus_runtime_bindings_reconstruct_original_exactly':True,'prior57_and_added84_original_reviews_exact':True,
        'quality_approvals_changed':False,'runtime_larger_hq_bindings_added':0}
    with (HERE/'all-sealed-evidence-integrity-corrected.json').open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('results','seven_original_working_files_reconstructed_exact')}))


if __name__=='__main__':main()

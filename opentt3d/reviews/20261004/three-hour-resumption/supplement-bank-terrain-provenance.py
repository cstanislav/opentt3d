"""Fresh public/source equivalence supplements never rewrite historical bank controls."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PRIOR=HERE.parent
SHORE=PRIOR/'river-bank-shore-breadth'
CLIMATES=('temperate','arctic','tropic','toyland')
IDENTITY=('base_set','base_graphics','climate','feature','feature_flags','offset_callback','palette','requested_offset','resolved_offset',
    'slope','source_file','source_height','source_offset','source_size','water_class','tile','tile_xy')


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def original_pam_digest(path):
    if path.suffix=='.pam':return digest(path)
    with Image.open(path) as picture:
        assert picture.mode=='RGBA'
        payload=picture.info['opentt3d_pam_header'].encode('ascii')+picture.tobytes()
    return hashlib.sha256(payload).hexdigest()


def main():
    target=HERE/'earlier-bank-fresh-terrain-supplement.json'
    if target.exists():raise ValueError('Retain all historical and fresh equivalence records')
    observed=json.loads((SHORE/'actual-terrain-selector-observations.json').read_text())
    rows=[];preserved={}
    for family in ('river-bank-breadth','river-sloped-bank-breadth','river-bank-snow-breadth'):
        source=PRIOR/family/'actual-source-index.json';before=digest(source)
        for old in json.loads(source.read_text()):
            matches=[row for row in observed if row['backend']=='vulkan' and not row['absent'] and
                row['source_image_sha256']==old['source_pam_sha256'] and all(row.get(key)==old.get(key) for key in IDENTITY)]
            new=matches[0] if matches else None
            record={'historical_study':family,'historical_source_index_sha256':before,'historical_tile':old['tile'],
                'climate':old['climate'],'requested_offset':old['requested_offset'],'slope':old['slope'],'source_height':old['source_height'],
                'historical_complete_source_pam':old['source_pam'],'historical_source_pam_sha256':old['source_pam_sha256'],
                'historical_control_retroactively_acknowledged':False,'historical_terrain_query_claim_rewritten':False,
                'fresh_exact_source_selection_tile_registration_and_bytes_observed':new is not None,
                'new_conditional_shape_slots_claimed':0,'model_rating_changed':False,'quality_approved':False,'runtime_bound':False}
            assert digest(ROOT/old['source_pam'])==old['source_pam_sha256']
            if new is not None:
                survey=SHORE/'native-controls/public-surveys'/Path(new['public_survey_fixture']).parent.name
                control=SHORE/'native-controls'/Path(new['native_control']).name
                data=json.loads((survey/'fixture.json').read_text());tile=next(tile for tile in data['tiles'] if tile['tile']==new['tile'])
                assert data['public_terrain_type_queries'] and data['survey_token']==new['public_survey_token']
                assert tile['public_terrain_type']==new['public_terrain_type'] and tile['slope']==old['slope'] and tile['min_height_levels']*8==old['source_height']
                picture=control/'renderer3d-reference'/new['source_image']
                if not picture.exists():picture=picture.with_suffix('.png')
                assert original_pam_digest(picture)==old['source_pam_sha256']
                record.update(fresh_public_terrain_type=new['public_terrain_type'],fresh_public_query_performed=True,
                    fresh_public_query_token=new['public_survey_token'],fresh_public_fixture=str((survey/'fixture.json').relative_to(ROOT)),
                    fresh_public_fixture_sha256=digest(survey/'fixture.json'),fresh_original_save=str((survey/data['save']).relative_to(ROOT)),
                    fresh_original_save_sha256=data['save_sha256'],fresh_complete_selected_source=str(picture.relative_to(ROOT)),
                    fresh_complete_selected_source_file_sha256=digest(picture),
                    fresh_complete_selected_original_pam_sha256=original_pam_digest(picture),fresh_source_observation=new)
            else:record.update(fresh_public_query_equivalence_unestablished=True,unmatched_observation_declared_absent=False)
            rows.append(record)
        assert digest(source)==before;preserved[str(source.relative_to(ROOT))]=before
    assert len(rows)==100
    matched=[row for row in rows if row['fresh_exact_source_selection_tile_registration_and_bytes_observed']]
    value={'observed_utc':datetime.now(timezone.utc).isoformat(),'historical_bank_source_instances_examined':100,
        'fresh_exact_same_tile_source_rgba_registration_and_public_query_matches':len(matched),
        'unmatched_historical_instances':len(rows)-len(matched),'matched_public_terrain_types':dict(Counter(row['fresh_public_terrain_type'] for row in matched)),
        'historical_source_indices_preserved_exactly':preserved,'historical_records_rewritten_or_retroactively_acknowledged':False,
        'additional_conditional_slots_or_aesthetic_approvals_claimed':0,'complete_terrain_type_snowline_parameter_custom_or_120_bank_runtime_coverage_accepted':False,
        'quality_approvals':0,'rows':rows}
    target.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({key:value for key,value in value.items() if key not in ('rows','historical_source_indices_preserved_exactly')}))


if __name__=='__main__':main()

"""Audit the available signed Mac CI artifact without bypassing failed Windows gates."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path,PurePosixPath
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BUILD=ROOT/'build-macos'
TAG='opentt3d-dev-20261004.43'
COMMIT='ccd153ba5be8b779b666e469db735d3985ffbdd9'
sys.path.insert(0,str(ROOT/'tools/assets'))
from compile_voxels import compile_catalogue


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    artifact=next(row for row in json.loads((HERE/'release43-available-ci-artifacts.json').read_text())['artifacts'] if row['name']=='release-macos-arm64')
    assert not artifact['expired'] and artifact['workflow_run']['head_sha']==COMMIT
    outer=BUILD/'playable-release43-ci-preview-outer.zip';assert not outer.exists()
    with outer.open('xb') as stream:
        subprocess.run(['gh','api',f"repos/cstanislav/opentt3d/actions/artifacts/{artifact['id']}/zip"],stdout=stream,check=True)
    assert digest(outer)==artifact['digest'].removeprefix('sha256:') and outer.stat().st_size==artifact['size_in_bytes']
    download=BUILD/'playable-release43-ci-preview-download';assert not download.exists();download.mkdir()
    with zipfile.ZipFile(outer) as package:
        assert set(package.namelist())=={f'{TAG}-macos-arm64.{suffix}' for suffix in ('json','zip','dmg')}
        package.extractall(download)
    report=json.loads((download/f'{TAG}-macos-arm64.json').read_text());assert report['tag']==TAG and report['commit']==COMMIT
    pin=json.loads(subprocess.check_output(['git','show',f'{COMMIT}:opentt3d/upstream.json'],cwd=ROOT));assert report['upstream']==pin
    authored=json.loads(subprocess.check_output(['git','show',f'{COMMIT}:assets/3d/voxels.json'],cwd=ROOT))
    compiler=subprocess.check_output(['git','show',f'{COMMIT}:tools/assets/compile_voxels.py'],cwd=ROOT)
    assert compiler==(ROOT/'tools/assets/compile_voxels.py').read_bytes()
    expected=compile_catalogue(authored)
    with zipfile.ZipFile(download/f'{TAG}-macos-arm64.zip') as package:
        assert all(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts for name in package.namelist())
        catalogue,=[name for name in package.namelist() if name.endswith('/baseset/opentt3d-voxels.json')]
        data=package.read(catalogue);assert json.loads(data)==expected and len(expected['models'])==1915
        metadata,=[name for name in package.namelist() if name.endswith('/release-info/build.json')]
        info=json.loads(package.read(metadata));assert info['tag']==TAG and info['commit']==COMMIT and info['upstream']==pin
        graphics,=[name for name in package.namelist() if name.endswith('/baseset/'+pin['graphics']['filename'])]
        assert hashlib.sha256(package.read(graphics)).hexdigest()==pin['graphics']['sha256']
    assets=[{'name':path.name,'bytes':path.stat().st_size,'sha256':digest(path)} for path in download.iterdir()]
    value={'audited_utc':datetime.now(timezone.utc).isoformat(),'tag':TAG,'commit':COMMIT,'artifact_id':artifact['id'],
        'outer_ci_artifact_sha256':digest(outer),'assets':assets,'catalogue_lf_sha256':hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest(),
        'compiled_immutable_tagged_authoring_and_pinned_graphics_exact':True,'accepted_partial_macos_ci_artifact':True,
        'source_and_all_downloaded_artifacts_exact':False,'accepted_publication':False,'quality_approvals':0,
        'reason':'Windows checkout failed; only this available Mac CI artifact is audited. This is not nineteen hosted assets, eight passed jobs, or publication acceptance.'}
    (HERE/'ci-preview-artifact-audit.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({key:value for key,value in value.items() if key!='assets'}))


if __name__=='__main__':main()

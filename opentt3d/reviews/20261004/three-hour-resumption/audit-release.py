"""Audit all hosted source blobs and exact packaged resource catalogues independently."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path,PurePosixPath
import subprocess
import tarfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tag',required=True);parser.add_argument('--commit',required=True);parser.add_argument('--run',type=int,required=True);args=parser.parse_args()
    download=ROOT/'build-macos/playable-release43-independent-download'
    assert not (HERE/'independent-artifact-audit.json').exists()
    release=json.loads((HERE/'packaged-draft.json').read_text());run=json.loads((HERE/'packaging-run.json').read_text());jobs=json.loads((HERE/'packaging-jobs.json').read_text())
    spec=importlib.util.spec_from_file_location('release_publication_validator',ROOT/'tools/opentt3d/publish_reviewed_release.py')
    publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
    pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp','repos/cstanislav/opentt3d/releases?per_page=100'],text=True))
    raw=publisher.select_release(pages,args.tag);manifest=(download/'SHA256SUMS').read_bytes();manifest_sha=hashlib.sha256(manifest).hexdigest()
    publisher.validate_draft(raw,run,jobs,args.tag,args.commit,args.run,manifest,manifest_sha)
    assert release['databaseId']==raw['id']
    assert subprocess.check_output(['git','rev-parse',f'{args.tag}^{{commit}}'],cwd=ROOT,text=True).strip()==args.commit
    remote=dict((line.split()[1],line.split()[0]) for line in subprocess.check_output(['git','ls-remote','origin',f'refs/tags/{args.tag}',f'refs/tags/{args.tag}^{{}}'],cwd=ROOT,text=True).splitlines())
    assert remote.get(f'refs/tags/{args.tag}^{{}}',remote[f'refs/tags/{args.tag}'])==args.commit
    tracked={entry.split(b'\t',1)[1].decode():entry.split(b'\t',1)[0].split()[2].decode() for entry in subprocess.check_output(['git','ls-tree','-rz',args.commit],cwd=ROOT).split(b'\0') if entry}
    source_archive=download/f'{args.tag}-source.tar.xz'
    with tarfile.open(source_archive) as source:
        names=[member.name for member in source.getmembers()];assert len(names)==len(set(names))
        for name,blob in tracked.items():
            member=source.getmember(f'{args.tag}/{name}');data=member.linkname.encode() if member.issym() else source.extractfile(member).read()
            assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==blob,name
        info=json.load(source.extractfile(f'{args.tag}/release-source.json'));assert info['tag']==args.tag and info['commit']==args.commit
        tagged_pin=json.load(source.extractfile(f'{args.tag}/opentt3d/upstream.json'))
        assert info['upstream']==tagged_pin
        graphics_path=f"{args.tag}/external/OpenGFX2-{info['upstream']['graphics']['commit']}.tar.gz"
        graphics=source.extractfile(graphics_path).read();assert hashlib.sha256(graphics).hexdigest()==info['graphics_source_sha256']
        extras={member.name for member in source.getmembers() if member.isfile() or member.issym()}-{f'{args.tag}/{name}' for name in tracked}
        assert extras=={f'{args.tag}/release-source.json',graphics_path}
        authored=json.load(source.extractfile(f'{args.tag}/assets/3d/voxels.json'));assert len(authored['models'])==1915
        diagnostic=json.load(source.extractfile(f'{args.tag}/assets/3d/hq-diagnostic-bindings.json'));assert diagnostic['runtime_enabled'] is False
        for category in ('objects','object_ground'):assert all(int(layout)<12 for layout in authored['bindings'][category])
        compiler_source=source.extractfile(f'{args.tag}/tools/assets/compile_voxels.py').read()
        namespace={'__file__':str(ROOT/'tools/assets/compile_voxels.py'),'__name__':'release_audit_compiler'}
        exec(compile(compiler_source,'immutable-tagged-compiler','exec'),namespace)
        expected=namespace['compile_catalogue'](authored)
    assets=[];packages=[];normalized=set()
    for asset in raw['assets']:
        path=download/asset['name'];sha=digest(path);assert sha==asset['digest'].removeprefix('sha256:') and path.stat().st_size==asset['size']
        assets.append({'name':asset['name'],'id':asset['id'],'bytes':asset['size'],'sha256':sha})
    for target in ('macos-arm64','macos-x86_64','windows-x64','windows-x86','windows-arm64','linux-x86_64'):
        report=json.loads((download/f'{args.tag}-{target}.json').read_text())
        assert report['tag']==args.tag and report['commit']==args.commit and report['platform']==target
        assert report['upstream']==tagged_pin
        archive=download/report['archive_verified']
        resources={}
        if archive.suffix=='.zip':
            with zipfile.ZipFile(archive) as package:
                for name in package.namelist():
                    path=PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts
                catalogue,=[name for name in package.namelist() if name.endswith('/baseset/opentt3d-voxels.json')]
                metadata,=[name for name in package.namelist() if name.endswith('/release-info/build.json')]
                for suffix in ('/lang/english.lng','/baseset/opntitle.dat','/PLAYING.md','/COPYING.md',
                    '/baseset/'+tagged_pin['graphics']['filename']):
                    resource,=[name for name in package.namelist() if name.endswith(suffix)]
                    payload=package.read(resource);assert payload
                    resources[suffix]={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
                baseset_prefix=catalogue.rsplit('/baseset/',1)[0]+'/baseset/'
                assert [name for name in package.namelist() if name.startswith(baseset_prefix) and name.endswith('.tar')]==[resource]
                data=package.read(catalogue);metadata=json.loads(package.read(metadata))
        else:
            with tarfile.open(archive) as package:
                for member in package.getmembers():
                    path=PurePosixPath(member.name);assert not path.is_absolute() and '..' not in path.parts
                catalogue,=[member for member in package.getmembers() if member.name.endswith('/baseset/opentt3d-voxels.json')]
                metadata,=[member for member in package.getmembers() if member.name.endswith('/release-info/build.json')]
                for suffix in ('/lang/english.lng','/baseset/opntitle.dat','/PLAYING.md','/COPYING.md',
                    '/baseset/'+tagged_pin['graphics']['filename']):
                    resource,=[member for member in package.getmembers() if member.name.endswith(suffix)]
                    payload=package.extractfile(resource).read();assert payload
                    resources[suffix]={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
                baseset_prefix=catalogue.name.rsplit('/baseset/',1)[0]+'/baseset/'
                assert [member.name for member in package.getmembers() if member.name.startswith(baseset_prefix) and member.name.endswith('.tar')]==[resource.name]
                data=package.extractfile(catalogue).read();metadata=json.load(package.extractfile(metadata))
        assert metadata['tag']==args.tag and metadata['commit']==args.commit
        assert metadata['upstream']==tagged_pin
        assert resources['/baseset/'+tagged_pin['graphics']['filename']]['sha256']==tagged_pin['graphics']['sha256']
        assert json.loads(data)==expected,'Packaged volumes/materials/bindings differ from immutable tagged authoring'
        lf_sha=hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest();normalized.add(lf_sha)
        packages.append({'platform':target,'models':1915,'catalogue_lf_sha256':lf_sha,'raw_catalogue_sha256':hashlib.sha256(data).hexdigest(),
            'compiled_tagged_source_cells_materials_bindings_exact':True,'pinned_graphics_metadata_required_resources':resources,
            'windows_arm64_execution_inferred':False})
    assert len(normalized)==1
    value={'audited_utc':datetime.now(timezone.utc).isoformat(),'tag':args.tag,'commit':args.commit,'packaging_run':args.run,
        'independent_artifact_reviewer_sha256':digest(Path(__file__)),
        'release_id':raw['id'],'packaging_jobs_passed':8,'assets':assets,'manifest_sha256':manifest_sha,'exact_source_files':len(tracked),
        'source_archive_sha256':digest(source_archive),'extra_source_files':sorted(extras),'packages':packages,
        'catalogue_lf_sha256':next(iter(normalized)),'source_and_all_downloaded_artifacts_exact':True,
        'unaccepted_hq_and_bank_runtime_bindings_added':0,'independent_downloaded_native_runtime_still_required':True,
        'accepted_publication':False,'every_model_8_or_60fps_or_all_platforms_accepted':False,'quality_approvals':0}
    (HERE/'independent-artifact-audit.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('assets','packages','extra_source_files')}))


if __name__=='__main__':main()

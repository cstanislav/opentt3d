"""Wait for exact packaging, then independently download every immutable attachment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
REPO='cstanislav/opentt3d'


def api(path):return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/{path}'],text=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',required=True);parser.add_argument('--commit',required=True);parser.add_argument('--run',type=int,required=True)
    args=parser.parse_args();output=ROOT/'build-macos/playable-release43-independent-download'
    assert not output.exists()
    with (HERE/'packaging-completion-watch.log').open('x') as log:
        subprocess.run(['gh','run','watch',str(args.run),'--repo',REPO,'--exit-status','--interval','60'],stdout=log,stderr=subprocess.STDOUT,check=True)
    run=api(f'actions/runs/{args.run}');jobs=api(f'actions/runs/{args.run}/jobs?per_page=100')
    assert run['head_sha']==args.commit and run['status']=='completed' and run['conclusion']=='success'
    assert jobs['total_count']==len(jobs['jobs'])==8 and all(job['conclusion']=='success' for job in jobs['jobs'])
    for name,value in (('packaging-run.json',run),('packaging-jobs.json',jobs)):
        with (HERE/name).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    release=json.loads(subprocess.check_output(['gh','release','view',args.tag,'--repo',REPO,
        '--json','tagName,targetCommitish,isDraft,isPrerelease,databaseId,assets,url,name,body'],text=True))
    assert release['tagName']==args.tag and release['targetCommitish']==args.commit and release['isDraft'] and release['isPrerelease']
    with (HERE/'packaged-draft.json').open('x') as stream:json.dump(release,stream,indent=2);stream.write('\n')
    subprocess.run(['gh','release','download',args.tag,'--repo',REPO,'--dir',str(output)],check=True)
    assert len([path for path in output.iterdir() if path.is_file()])==19
    checksums={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (output/'SHA256SUMS').read_text().splitlines()}
    assert len(checksums)==18
    for asset in release['assets']:
        path=output/asset['name'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert path.stat().st_size==asset['size'] and asset['digest']=='sha256:'+digest
        if path.name!='SHA256SUMS':assert checksums[path.name]==digest
    print(json.dumps({'tag':args.tag,'commit':args.commit,'packaging_jobs_passed':8,'independently_downloaded_assets':19,
        'output':str(output.relative_to(ROOT)),'manifest_sha256':hashlib.sha256((output/'SHA256SUMS').read_bytes()).hexdigest(),
        'published':False,'full_quality_or_platform_acceptance':False}))


if __name__=='__main__':main()

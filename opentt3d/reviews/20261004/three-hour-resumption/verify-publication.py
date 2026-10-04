"""Confirm guarded publication left reviewed bytes and both earlier releases immutable."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
REPO='cstanislav/opentt3d'


def api(path):return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/{path}'],text=True))


def stable_assets(assets):
    keys=('id','name','size','digest','created_at','updated_at','state')
    return sorted([{key:row[key] for key in keys if key in row} for row in assets],key=lambda row:row['name'])


def view(tag):
    return json.loads(subprocess.check_output(['gh','release','view',tag,'--repo',REPO,
        '--json','tagName,targetCommitish,isDraft,isPrerelease,databaseId,assets,url,name,body'],text=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--publication-run',type=int,required=True);args=parser.parse_args()
    audit=json.loads((HERE/'independent-artifact-audit.json').read_text())
    runtime=json.loads((HERE/'independent-runtime-audit.json').read_text())
    assert audit['source_and_all_downloaded_artifacts_exact'] and runtime['accepted_scoped_native_runtime']
    assert audit['tag']==runtime['tag'] and audit['commit']==runtime['commit']
    assert runtime['quality_approvals']==0 and not runtime['accepted_full_objective']
    with (HERE/'publication-completion-watch.log').open('x') as log:
        subprocess.run(['gh','run','watch',str(args.publication_run),'--repo',REPO,'--exit-status','--interval','20'],stdout=log,stderr=subprocess.STDOUT,check=True)
    run=api(f'actions/runs/{args.publication_run}');jobs=api(f'actions/runs/{args.publication_run}/jobs?per_page=100')
    assert run['status']=='completed' and run['conclusion']=='success'
    assert run['path'].split('@',1)[0]=='.github/workflows/opentt3d-publish-reviewed.yml'
    assert jobs['total_count']==len(jobs['jobs'])==1 and jobs['jobs'][0]['conclusion']=='success'
    for name,value in (('publication-run.json',run),('publication-jobs.json',jobs)):
        with (HERE/name).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    artifact=ROOT/'build-macos/playable-release43-publication-artifact';assert not artifact.exists()
    subprocess.run(['gh','run','download',str(args.publication_run),'--repo',REPO,'--name','independently-reviewed-publication','--dir',str(artifact)],check=True)
    receipt=json.loads((artifact/'publication-receipt.json').read_text())
    assert receipt['published'] and receipt['tag']==audit['tag'] and receipt['commit']==audit['commit']
    assert receipt['packaging_run']==audit['packaging_run'] and receipt['packaging_jobs_passed']==8
    assert receipt['manifest_sha256']==audit['manifest_sha256']
    release=api(f"releases/{audit['release_id']}")
    assert release['draft'] is False and release['prerelease'] and release['tag_name']==audit['tag'] and release['target_commitish']==audit['commit']
    before=json.loads((HERE/'packaged-draft.json').read_text())
    assert release['id']==before['databaseId'] and release['name']==before['name'] and release['body']==before['body']
    expected={row['name']:{'id':row['id'],'size':row['bytes'],'sha256':row['sha256']} for row in audit['assets']}
    actual={row['name']:{'id':row['id'],'size':row['size'],'sha256':row['digest'].removeprefix('sha256:')} for row in release['assets']}
    assert expected==actual and len(actual)==19
    assert receipt['attachments']=={name:{'size':row['size'],'digest':'sha256:'+row['sha256']} for name,row in actual.items()}
    prior=json.loads((HERE/'prior-releases-before.json').read_text())['releases'];prior_checks=[]
    for old in prior:
        new=view(old['tagName'])
        # Download counters may change due unrelated users; they are not release
        # metadata or immutable package bytes and are deliberately not frozen.
        keys=('tagName','targetCommitish','isDraft','isPrerelease','databaseId','name','body')
        assert all(new[key]==old[key] for key in keys)
        assert stable_assets(new['assets'])==stable_assets(old['assets'])
        prior_checks.append({'tag':old['tagName'],'release_id':old['databaseId'],'draft':new['isDraft'],
            'tag_commit_title_notes_asset_ids_sizes_digests_exact':True,'assets':len(new['assets'])})
    builds=json.loads(subprocess.check_output(['gh','run','list','--repo',REPO,'--workflow','opentt3d-release.yml',
        '--commit',audit['commit'],'--limit','50','--json','databaseId,headSha,status,conclusion,event'],text=True))
    assert len(builds)==1 and builds[0]['databaseId']==audit['packaging_run']
    subprocess.run(['gh','release','download',audit['tag'],'--repo',REPO,'--pattern','SHA256SUMS',
        '--dir',str(ROOT/'build-macos/playable-release43-public-manifest')],check=True)
    manifest=ROOT/'build-macos/playable-release43-public-manifest/SHA256SUMS'
    assert hashlib.sha256(manifest.read_bytes()).hexdigest()==audit['manifest_sha256']
    assert subprocess.check_output(['git','rev-parse',f"{audit['tag']}^{{commit}}"],cwd=ROOT,text=True).strip()==audit['commit']
    remote=dict((line.split()[1],line.split()[0]) for line in subprocess.check_output(['git','ls-remote','origin',
        f"refs/tags/{audit['tag']}",f"refs/tags/{audit['tag']}^{{}}"],cwd=ROOT,text=True).splitlines())
    assert remote.get(f"refs/tags/{audit['tag']}^{{}}",remote[f"refs/tags/{audit['tag']}"])==audit['commit']
    (HERE/'guarded-publication-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    value={'verified_utc':datetime.now(timezone.utc).isoformat(),'tag':audit['tag'],'commit':audit['commit'],'url':release['html_url'],
        'release_id':release['id'],'published':True,'prerelease':True,'latest_or_recommendation_changed':False,
        'guarded_publication_run':args.publication_run,'original_packaging_run':audit['packaging_run'],
        'original_packaging_jobs_passed':8,'attachment_ids_sizes_digests_exact':True,'immutable_attachments':19,
        'manifest_sha256':audit['manifest_sha256'],'source_package_and_downloaded_native_audits_pass':True,
        'release_title_notes_commit_and_tag_unchanged':True,'no_packaging_rebuild_observed':True,'packaging_runs':builds,
        'prior_releases':prior_checks,'recommended_release':'opentt3d-dev-20261003.42','quality_approvals':0,
        'every_runtime_asset_3d_every_model8_and_sustained60fps_met':False}
    with (HERE/'public-release43-verification.json').open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({key:value for key,value in value.items() if key not in ('prior_releases','packaging_runs')}))


if __name__=='__main__':main()

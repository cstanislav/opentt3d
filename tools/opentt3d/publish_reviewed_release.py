#!/usr/bin/env python3
"""Publish an independently reviewed draft without rebuilding its audited bytes.

Run from the manual publication workflow with GITHUB_TOKEN. Events produced by
that token do not start the release-published packaging workflow a second time.
The reviewer supplies the exact already-audited commit/run/checksum-manifest hash.
Without --publish this command only checks the live draft and writes a receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

REPO = "cstanislav/opentt3d"


def expected_assets(tag):
    names = {"SHA256SUMS",f"{tag}-source.tar.xz"}
    for platform,suffixes in (("linux-x86_64",("json","tar.xz")),
                             ("macos-arm64",("json","dmg","zip")),("macos-x86_64",("json","dmg","zip")),
                             ("windows-x64",("json","exe","zip")),("windows-x86",("json","exe","zip")),
                             ("windows-arm64",("json","exe","zip"))):
        names.update(f"{tag}-{platform}.{suffix}" for suffix in suffixes)
    return names


def validate_draft(release,run,jobs,tag,commit,run_id,manifest,manifest_sha256):
    if not re.fullmatch(r"opentt3d-dev-\d{8}\.\d+",tag) or not re.fullmatch(r"[0-9a-f]{40}",commit) or not re.fullmatch(r"[0-9a-f]{64}",manifest_sha256):
        raise ValueError("Publication needs an exact immutable tag, commit and audited checksum hash")
    if release.get("draft") is not True or release.get("prerelease") is not True or release.get("tag_name") != tag or release.get("target_commitish") != commit:
        raise ValueError("Publication requires the exact reviewed development draft; existing public releases are immutable")
    if (run.get("id") != run_id or run.get("head_sha") != commit or run.get("status") != "completed" or run.get("conclusion") != "success" or
            run.get("path","").split("@",1)[0] != ".github/workflows/opentt3d-release.yml" or run.get("repository",{}).get("full_name") != REPO):
        raise ValueError("The exact packaging workflow/commit has not passed")
    if jobs.get("total_count") != 8 or len(jobs.get("jobs",[])) != 8 or any(job.get("status") != "completed" or job.get("conclusion") != "success" for job in jobs["jobs"]):
        raise ValueError("All eight original packaging jobs must pass without skipped gates")
    if hashlib.sha256(manifest).hexdigest() != manifest_sha256:
        raise ValueError("The independently audited checksum manifest has changed")
    checksums = {}
    for line in manifest.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)",line)
        if not match or match[2] in checksums:
            raise ValueError("Invalid or duplicate checksum manifest member")
        checksums[match[2]] = match[1]
    assets = release.get("assets",[])
    names = {asset.get("name") for asset in assets}
    if len(assets) != 19 or names != expected_assets(tag) or set(checksums) != names-{"SHA256SUMS"}:
        raise ValueError("The complete independently audited attachment set is required")
    for asset in assets:
        digest = manifest_sha256 if asset["name"] == "SHA256SUMS" else checksums[asset["name"]]
        if asset.get("state") != "uploaded" or type(asset.get("size")) is not int or asset["size"] <= 0 or asset.get("digest") != "sha256:"+digest:
            raise ValueError(f"The audited attachment changed or is incomplete: {asset['name']}")
    return {asset["name"]:{"size":asset["size"],"digest":asset["digest"]} for asset in assets}


def api(path):
    return json.loads(subprocess.check_output(["gh","api",f"repos/{REPO}/{path}"],text=True))


def select_release(pages,tag):
    """GitHub's tag endpoint omits drafts even when authenticated listing sees them."""
    matches = [release for page in pages for release in page if release.get("tag_name") == tag]
    if len(matches) != 1 or type(matches[0].get("id")) is not int:
        raise ValueError("Exactly one authenticated release must match the immutable reviewed tag")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag",required=True)
    parser.add_argument("--commit",required=True)
    parser.add_argument("--run",required=True,type=int)
    parser.add_argument("--manifest-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--publish",action="store_true",help="Explicitly publish the checked draft; default is read-only")
    args = parser.parse_args()
    if (not re.fullmatch(r"opentt3d-dev-\d{8}\.\d+",args.tag) or not re.fullmatch(r"[0-9a-f]{40}",args.commit) or
            not re.fullmatch(r"[0-9a-f]{64}",args.manifest_sha256) or args.run <= 0):
        parser.error("Supply the exact reviewed tag, commit, positive run ID and checksum hash")
    commit = subprocess.check_output(["git","rev-parse",f"refs/tags/{args.tag}^{{commit}}"],text=True).strip()
    if commit != args.commit: raise ValueError("The immutable reviewed tag moved")
    pages = json.loads(subprocess.check_output(["gh","api","--paginate","--slurp",f"repos/{REPO}/releases?per_page=100"],text=True))
    release = select_release(pages,args.tag)
    run = api(f"actions/runs/{args.run}")
    jobs = api(f"actions/runs/{args.run}/jobs?per_page=100")
    with tempfile.TemporaryDirectory(prefix="opentt3d-reviewed-release-") as temporary:
        subprocess.run(["gh","release","download",args.tag,"--repo",REPO,"--pattern","SHA256SUMS","--dir",temporary],check=True)
        manifest = (Path(temporary)/"SHA256SUMS").read_bytes()
    attachments = validate_draft(release,run,jobs,args.tag,args.commit,args.run,manifest,args.manifest_sha256)
    if args.publish:
        if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("GITHUB_REPOSITORY") != REPO or not os.environ.get("GH_TOKEN"):
            raise ValueError("Publish through the reviewed GITHUB_TOKEN workflow; local personal-token publication would rebuild audited packages")
        subprocess.run(["gh","api","--method","PATCH",f"repos/{REPO}/releases/{release['id']}","--input","-"],
                       input=json.dumps({"draft":False}),text=True,stdout=subprocess.PIPE,check=True)
        published = api(f"releases/{release['id']}")
        actual = {asset["name"]:{"size":asset["size"],"digest":asset["digest"]} for asset in published["assets"]}
        unchanged = ("id","tag_name","target_commitish","prerelease","name","body")
        if published["draft"] or any(published.get(field) != release.get(field) for field in unchanged) or attachments != actual:
            raise ValueError("Publication changed an immutable reviewed package or tag")
        release = published
    receipt = {"tag":args.tag,"commit":args.commit,"packaging_run":args.run,"packaging_jobs_passed":8,
               "manifest_sha256":args.manifest_sha256,"attachments":attachments,"published":not release["draft"],
               "url":release["html_url"],"scope":"Only the draft flag changes. No package, checksum, tag, release title or notes are replaced. Independent source/resource/runtime audits are a prerequisite supplied by the reviewer, not inferred from CI alone."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()

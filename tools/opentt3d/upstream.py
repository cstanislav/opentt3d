#!/usr/bin/env python3
"""Check stable upstream releases or prepare a normal merge on an update branch."""

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "opentt3d/upstream.json"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def record(tag):
    commit = git("rev-parse", f"{tag}^{{commit}}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT).returncode:
        # A --no-commit merge records its second parent in MERGE_HEAD.
        merge_head = git("rev-parse", "--verify", "MERGE_HEAD")
        if merge_head != commit:
            raise SystemExit("Target tag is not the current merge or an ancestor of HEAD")
    if git("diff", "--name-only", "--diff-filter=U"):
        raise SystemExit("Resolve the outstanding merge conflicts before recording the new pin")
    data = json.loads(PIN.read_text())
    data["openttd"].update(tag=tag, commit=commit)
    PIN.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Pinned OpenTTD {tag} at {commit}. Review the merge and run builds, tests and asset coverage before committing.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "prepare", "record"))
    parser.add_argument("tag", nargs="?")
    args = parser.parse_args()
    data = json.loads(PIN.read_text())
    if args.action == "check":
        latest = json.loads(subprocess.check_output(["gh", "api", "repos/OpenTTD/OpenTTD/releases/latest"], text=True))
        result = {"pinned": data["openttd"]["tag"], "latest_stable": latest["tag_name"],
                  "update_available": latest["tag_name"] != data["openttd"]["tag"], "url": latest["html_url"]}
        print(json.dumps(result, indent=2))
        return
    if args.tag is None or re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,2}", args.tag) is None:
        parser.error("Specify a stable version such as 15.3 or 16.0")
    if args.action == "record":
        record(args.tag)
        return
    version = lambda tag: tuple((list(map(int, tag.split("."))) + [0, 0])[:3])
    if version(args.tag) < version(data["openttd"]["tag"]):
        raise SystemExit("The update target must not be older than the pinned stable release")
    if git("status", "--porcelain"):
        raise SystemExit("The working tree must be clean before preparing an upstream merge")
    if git("remote", "get-url", "upstream") != data["openttd"]["repository"]:
        raise SystemExit("The upstream remote does not match the pinned upstream repository")
    subprocess.run(["git", "fetch", "upstream", "tag", args.tag], cwd=ROOT, check=True)
    commit = git("rev-parse", f"{args.tag}^{{commit}}")
    if commit == data["openttd"]["commit"]:
        print(f"Already based on OpenTTD {args.tag}")
        return
    subprocess.run(["git", "switch", "-c", f"update/openttd-{args.tag}"], cwd=ROOT, check=True)
    result = subprocess.run(["git", "merge", "--no-ff", "--no-commit", commit], cwd=ROOT)
    if result.returncode:
        raise SystemExit(f"Merge requires resolution. Afterwards run: python3 tools/opentt3d/upstream.py record {args.tag}")
    record(args.tag)


if __name__ == "__main__":
    main()

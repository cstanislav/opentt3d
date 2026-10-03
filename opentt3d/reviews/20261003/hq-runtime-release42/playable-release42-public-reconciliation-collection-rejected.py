"""Reconcile guarded publication without changing any immutable release content."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess

ROOT = Path("build-macos")
TAG = "opentt3d-dev-20261003.42"
COMMIT = "1247c88d5e180ac6fbd88bdf9b71bfafd468f7a5"
PORTABLE = Path("opentt3d/reviews/20261003/hq-runtime-release42")

def load(name):
    return json.loads((ROOT / name).read_text())

before = load("playable-release42-assets.json")
after = load("playable-release42-published-assets.json")
artifact = load("playable-release42-artifact-audit.json")
runtime = load("playable-release42-independent-runtime-audit.json")
publication = load("playable-release42-publication-run.json")
receipt = load("playable-release42-publication-receipt/publication-receipt.json")
assert before["isDraft"] and not after["isDraft"] and after["isPrerelease"]
for key in ("tagName", "targetCommitish", "databaseId", "isPrerelease", "name", "body"):
    assert before[key] == after[key], key
assert after["tagName"] == TAG and after["targetCommitish"] == COMMIT
identities = lambda row: {a["name"]: (a["id"], a["size"], a["digest"]) for a in row["assets"]}
assert len(after["assets"]) == 19 and identities(before) == identities(after)
assert artifact["accepted_exact_artifacts"] and runtime["accepted_scoped_runtime"]
assert artifact["commit"] == runtime["commit"] == receipt["commit"] == COMMIT
assert publication["status"] == "completed" and publication["conclusion"] == "success"
assert all(job["conclusion"] == "success" for job in publication["jobs"])
assert receipt["published"] and receipt["packaging_run"] == 37132182765
assert receipt["manifest_sha256"] == artifact["manifest_sha256"]
assert receipt["attachments"] == {a["name"]: {"size": a["size"], "digest": a["digest"]} for a in after["assets"]}
runs = load("playable-release42-no-rebuild-runs.json")
assert [r["databaseId"] for r in runs if r["headSha"] == COMMIT] == [37132182765]
assert not any(r["event"] == "release" and r["createdAt"] >= publication["createdAt"] for r in runs)
remote = dict((line.split()[1], line.split()[0]) for line in subprocess.check_output(
    ["git", "ls-remote", "origin", f"refs/tags/{TAG}", f"refs/tags/{TAG}^{{}}"], text=True).splitlines())
assert remote[f"refs/tags/{TAG}^{{}}"] == COMMIT
withheld_before = load("playable-release41-withheld-assets.json")
withheld_after = load("playable-release41-after42-still-withheld.json")
assert withheld_after["isDraft"] and identities(withheld_before) == identities(withheld_after)
for key in ("tagName", "targetCommitish", "databaseId", "isPrerelease", "name", "body"):
    assert withheld_before[key] == withheld_after[key], key

for name in ("playable-release42-publication-receipt/publication-receipt.json", "playable-release42-publication-run.json",
             "playable-release42-no-rebuild-runs.json", "playable-release42-initial-draft.json",
             "playable-release42-exact-draft.json", "playable-release42-exact-tagged-draft.json",
             "playable-release42-initial-metadata-rejection.md", "playable-release42-independent-harness-import-rejection.md",
             "playable-release42-smoke-cow-import-rejected.py", "playable-release42-independent-mac-controls.log"):
    destination = PORTABLE / Path(name).name
    assert not destination.exists(), destination
    shutil.copy2(ROOT / name, destination)

summary = {
    "audited_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "tag": TAG, "commit": COMMIT, "url": after["url"], "published_at": after["publishedAt"],
    "packaging_run": 37132182765, "publication_run": 37136166083,
    "exact_source_files": 2262, "assets": 19, "checksums": 18, "models": 1831,
    "manifest_sha256": artifact["manifest_sha256"], "catalogue_sha256": runtime["catalogue_sha256"],
    "independent_binary_sha256": runtime["binary_sha256"],
    "independent_package_controls": len(runtime["package_controls"]),
    "independent_native_controls": len(runtime["native_controls"]),
    "prior_gallery_images_exact": sum(row["prior_gallery_images_rgba_exact"] for row in runtime["preservation"]),
    "prior_source_layers_exact": sum(row["prior_source_layers_byte_exact"] for row in runtime["preservation"]),
    "attachment_id_size_digest_exact": True, "title_notes_and_tag_unchanged": True,
    "no_release_event_rebuild_in_observed_workflow_history": True, "withheld41_unchanged": True,
    "accepted_recommended_development_release": True, "accepted_full_objective": False,
    "scope": "The exact-tag rebuilt, independently downloaded app resolves the scoped release-source isolation gate. It does not retroactively certify the earlier mixed-working-source binary. Larger84-owner artwork/compiler/tests and screening ratings stay excluded; zero eight-point approvals. Wider strict backend, natural sizes2..4/all climates, locks/rivers/disasters, fleet/emitter, sustained60fps/memory, Windows ARM64 execution/GPU/input and replay/network remain open. This is a reconciliation timestamp, not an actual stopping time.",
}
output = ROOT / "playable-release42-recommended-public-receipt.json"
assert not output.exists()
output.write_text(json.dumps(summary, indent=2) + "\n")
shutil.copy2(output, PORTABLE / output.name)
manifest = PORTABLE / "evidence-sha256.json"
prior = json.loads(manifest.read_text())
for name, digest in prior["files"].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
prior["files"].update({str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in PORTABLE.iterdir() if path.is_file() and path != manifest})
prior["scope"] = summary["scope"]
manifest.write_text(json.dumps(prior, indent=2) + "\n")
print(json.dumps(summary))

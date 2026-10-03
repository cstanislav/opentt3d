"""Bind additive quality-scope reports/tests and unchanged runtime/asset identities."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/river-ground-quality-scope")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
assert not (out / "evidence-sha256.json").exists()
summary = json.loads((out / "verification.json").read_text())
assert [row["ledger_entries"] for row in summary["scopes"]] == [2866,2950,2998]
for name,count in (("breadth-original-river-ground-quality-working-assets.log",257),
                   ("breadth-original-river-ground-quality-clean-tests.log",241)):
    assert f"Ran {count} tests" in (root / name).read_text() and "\nOK\n" in (root / name).read_text()
for scope in summary["scopes"]:
    for prefix,suffix in (("inventory","inventory.json"),("quality","quality.json"),("ratings","ratings.csv")):
        assert digest(out / (scope["scope"]+"-"+suffix)) == scope[prefix+"_sha256"]
    for field in ("prior_inventory","prior_quality","review_input"):
        hash_field = "reviews_sha256" if field == "review_input" else field+"_sha256"
        assert digest(Path(scope[field])) == scope[hash_field]
assert Path("opentt3d/MODEL_RATINGS.csv").read_bytes() == (out / "rejected-hq-lock-ratings.csv").read_bytes()
assert not subprocess.check_output(["git","diff","--name-only","--","src"],text=True).strip()
identity = {}
for name in ("assets/3d/quality_reviews.json","assets/3d/voxels.json","tools/assets/compile_voxels.py"):
    content = subprocess.check_output(["git","show",f"HEAD:{name}"])
    identity[name] = {"committed_sha256":hashlib.sha256(content).hexdigest(),"working_sha256":digest(Path(name)),
                      "scope":"Canonical identity; uncommitted rejected HQ artwork/compiler stay excluded."}
assert identity["assets/3d/quality_reviews.json"]["committed_sha256"] == identity["assets/3d/quality_reviews.json"]["working_sha256"]
identity["renderer_source_diff"] = []
identity["recommended_release"] = "opentt3d-dev-20261003.42"
identity["audit_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(out / "unchanged-runtime-identity.json").write_text(json.dumps(identity,indent=2)+"\n")
for name in ("tools/assets/original_water.py","tools/assets/quality_audit.py","tools/assets/inventory.py",
             "tools/assets/test_original_water.py","tools/assets/test_quality_audit.py","tools/assets/live_water.py","tools/assets/test_live_river.py"):
    target = out / "source-snapshot" / name
    assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(name,target)
for name in ("breadth-original-river-ground-quality-working-assets.log","breadth-original-river-ground-quality-clean-tests.log",
             "breadth-original-river-ground-quality-clean-test-receipt.json","breadth-original-river-ground-quality-clean-tests.py",
             "breadth-original-river-ground-quality-original-tests.log","breadth-original-river-ground-quality-audit-tests.log",
             "breadth-original-river-ground-quality-scope.log"):
    target = out / name
    assert not target.exists()
    shutil.copy2(root / name,target)
shutil.copy2(Path(__file__),out / "reproduce-evidence-seal.py")
files = {str(path):digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files":files,"scope":summary["scope"]},indent=2)+"\n")
print(json.dumps({"portable_files":len(files),"working_asset_tests":257,"isolated_committed_artwork_tests":241,"approvals":0}))

"""Retain exact matching canonical/candidate inventories, CSVs and rejected test layout."""
from pathlib import Path
import hashlib, json, shutil

root = Path("build-macos")
out = Path("opentt3d/reviews/20261003/water-quality-scope")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()


def copy(source, target):
    assert not target.exists(), target
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert digest(source) == digest(target)


assert "Ran 247 tests" in (root / "breadth-original-water-full-scope-all-asset-tests.log").read_text()
assert "\nOK\n" in (root / "breadth-original-water-full-scope-all-asset-tests.log").read_text()
assert json.loads((root / "breadth-original-water-quality-clean-test-receipt.json").read_text())["asset_tests"] == 231
verification = json.loads((root / "breadth-original-water-full-scope-verification.json").read_text())
for row in verification["ledgers"]:
    assert row["require_eight_exit"] == 1 and row["approvals"] == 0 and row["water_state_entries"] == 544
    for suffix in ("inventory.json","ratings.csv","quality.json","inventory.log","quality.log"):
        copy(root / f"breadth-original-water-full-scope-{row['scope']}-{suffix}",out / f"{row['scope']}-{suffix}")
for name in ("breadth-original-water-full-scope-verification.json","breadth-original-water-full-scope-ledgers.py",
             "breadth-original-water-full-scope-prior-working-ratings.csv","breadth-original-water-full-scope-all-asset-tests.log",
             "breadth-original-water-quality-clean-asset-tests.log","breadth-original-water-quality-clean-test-receipt.json",
             "breadth-original-water-quality-clean-tests.py","breadth-original-water-quality-test-placement-rejected.py",
             "breadth-original-water-quality-test-placement-rejection.md","breadth-original-water-full-scope-quality-tests.log"):
    copy(root / name,out / name)
for name in ("tools/assets/quality_audit.py","tools/assets/test_quality_audit.py"):
    copy(Path(name),out / "source-snapshot" / name)
copy(Path(__file__),out / "reproduce-portable-evidence.py")
files = {str(path):digest(path) for path in out.rglob("*") if path.is_file()}
(out / "evidence-sha256.json").write_text(json.dumps({"files":files,"scope":verification["scope"]},indent=2)+"\n")
print(json.dumps({"portable_files":len(files),"ledgers":[row["ledger_entries"] for row in verification["ledgers"]],"approvals":0}))

"""Re-run every retained catalogue-wide required-eight gate; all must still fail."""
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
prior = ROOT / "opentt3d/reviews/20261003/water-bond-foam-study"
foam = ROOT / "opentt3d/reviews/20261003/water-foam-palette-study"
target = ROOT / "build-macos/breadth-original-lock-world-support-quality-gates"
assert not target.exists()
target.mkdir()
with gzip.open(HERE / "canonical-diagnostic-catalogue.json.gz", "rt") as source:
    canonical = json.load(source)
with gzip.open(foam / "separate-rejected-hq-lock-catalogue.json.gz", "rt") as source:
    mixed = json.load(source)
hq = {**mixed, "models": {name: model for name, model in mixed["models"].items() if not name.startswith("lock_study_")}}
reviews = json.loads((foam / "combined-quality-reviews.json").read_text())
receipts = []
for label, catalogue in (("canonical", canonical), ("rejected-hq", hq), ("rejected-hq-lock", mixed)):
    current = {**reviews, "models": {name: value for name, value in reviews["models"].items() if name in catalogue["models"] or
                                     not name.startswith("hq_") and not name.startswith("lock_study_")}}
    catalogue_path, reviews_path = target / f"{label}-catalogue.json", target / f"{label}-reviews.json"
    catalogue_path.write_text(json.dumps(catalogue, separators=(",", ":")) + "\n")
    reviews_path.write_text(json.dumps(current, separators=(",", ":")) + "\n")
    output = HERE / f"{label}-required-eight-quality.json"
    with (HERE / f"{label}-required-eight.log").open("x") as log:
        result = subprocess.run([sys.executable, "tools/assets/quality_audit.py", "--catalogue", str(catalogue_path),
                                 "--reviews", str(reviews_path), "--inventory", str(prior / f"{label}-inventory.json"),
                                 "--output", str(output), "--require-eight"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert result.returncode == 1 and json.loads(output.read_text()) == json.loads((HERE / f"{label}-quality.json").read_text())
    report = json.loads(output.read_text())
    assert not report["meets_objective"] and len(report["coverage_gaps"]) == 4
    receipts.append({"scope": label, "exit_code": result.returncode, "rows": len(report["models"]), "approvals": 0,
                     "coverage_gaps": 4, "stale_reviews_or_evidence": False, "meets_objective": False})
(HERE / "required-eight-verification.json").write_text(json.dumps({"audited_utc": datetime.now(timezone.utc).isoformat(), "gates": receipts}, indent=2) + "\n")
print(json.dumps(receipts))

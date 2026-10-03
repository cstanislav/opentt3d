"""Keep original water state scope in canonical and separately rejected-candidate ledgers."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess

root = Path("build-macos")
prefix = "breadth-original-water-full-scope"
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
catalogues = {"canonical":root / "playable-release42-independent-extracted/OpenTT3D.app/Contents/Resources/baseset/opentt3d-voxels.json",
              "hq-rejected-candidate":root / "breadth-original-hq-medium-perimeter-owner-catalogue.json"}
reviews = {"canonical":Path("assets/3d/quality_reviews.json"),
           "hq-rejected-candidate":root / "breadth-original-hq-medium-perimeter-owner-combined-rejected-reviews.json"}
assert digest(catalogues["canonical"]) == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
assert digest(catalogues["hq-rejected-candidate"]) == "7a4979f3fa7ecf27981867a785d358391d60c6446d13c4d7efb848dec0b0936e"
old_csv = root / (prefix+"-prior-working-ratings.csv")
assert not old_csv.exists()
shutil.copy2("opentt3d/MODEL_RATINGS.csv",old_csv)
rows = []
for mode,catalogue in catalogues.items():
    inventory = root / f"{prefix}-{mode}-inventory.json"
    assert not inventory.exists()
    with (root / f"{prefix}-{mode}-inventory.log").open("x") as log:
        subprocess.run(["python3","tools/assets/inventory.py","--catalogue",str(catalogue),"--output",str(inventory)],stdout=log,stderr=subprocess.STDOUT,check=True)
    report = root / f"{prefix}-{mode}-quality.json"
    csv = root / f"{prefix}-{mode}-ratings.csv"
    assert not report.exists() and not csv.exists()
    with (root / f"{prefix}-{mode}-quality.log").open("x") as log:
        result = subprocess.run(["python3","tools/assets/quality_audit.py","--catalogue",str(catalogue),"--reviews",str(reviews[mode]),
            "--inventory",str(inventory),"--output",str(report),"--csv",str(csv),"--require-eight"],stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 1 and report.is_file()
    quality = json.loads(report.read_text())
    assert quality["runtime_scope"]["water_structures"] == json.loads(inventory.read_text())["water_structures"]
    assert not quality["meets_objective"] and not any(row["score"] >= 8 for row in quality["models"])
    assert len(quality["models"]) == (2846 if mode == "canonical" else 2930)
    assert sum(row["status"] == "individually-reviewed" for row in quality["models"]) == (57 if mode == "canonical" else 141)
    assert len([row for row in quality["models"] if row["model"].startswith("missing/lock/")]) == 192
    assert len([row for row in quality["models"] if row["model"].startswith("unresolved/river-bank/")]) == 240
    assert b"\r" not in csv.read_bytes()
    rows.append({"scope":mode,"catalogue_sha256":digest(catalogue),"source_models":len(json.loads(catalogue.read_text())["models"]),
        "inventory_sha256":digest(inventory),"reviews_sha256":digest(reviews[mode]),"quality_report_sha256":digest(report),
        "csv_sha256":digest(csv),"ledger_entries":len(quality["models"]),"individual_records":57 if mode == "canonical" else 141,
        "water_state_entries":544,"structural_lock_gaps":192,"conditional_river_selectors":240,"require_eight_exit":result.returncode,"approvals":0})
shutil.copy2(root / f"{prefix}-hq-rejected-candidate-ratings.csv","opentt3d/MODEL_RATINGS.csv")
receipt = root / (prefix+"-verification.json")
assert not receipt.exists()
receipt.write_text(json.dumps({"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"ledgers":rows,
    "tools_sha256":{name:digest(Path(name)) for name in ("tools/assets/inventory.py","tools/assets/quality_audit.py","tools/assets/test_quality_audit.py")},
    "scope":"No artwork, bindings, canonical reviews or .42 package changed. Canonical and quarantined larger-HQ ledgers remain distinct. Default and conditional water source scope is retained, not live custom/geometry/animation/visual approval. Working CSV includes rejected HQ candidates and is not a released model catalogue."},indent=2)+"\n")
print(json.dumps({"ledgers":rows,"required_eight":False}))

"""Verify exact portable foam-study evidence; quality acceptance must still fail."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = ROOT / "opentt3d/reviews/20261003/water-bond-foam-study"
sys.path.insert(0,str(ROOT / "tools/assets"))
from compile_voxels import compile_catalogue
from quality_audit import audit, fingerprint


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal",action="store_true")
    args = parser.parse_args()
    manifest_path = HERE / "evidence-sha256.json"
    if args.seal:
        manifest_path.write_text(json.dumps({"files":{str(path.relative_to(ROOT)):digest(path)
            for path in sorted(HERE.rglob("*")) if path.is_file() and path != manifest_path},"approvals":0},indent=2)+"\n")
    manifest = json.loads(manifest_path.read_text())
    for filename,expected in manifest["files"].items():
        assert digest(ROOT / filename) == expected,filename
    for directory in (PRIOR,ROOT / "opentt3d/reviews/20261003/hq-large-column-repair"):
        old_manifest = json.loads((directory / "evidence-sha256.json").read_text())
        assert all(digest(ROOT / filename) == expected for filename,expected in old_manifest["files"].items())
    images = json.loads((HERE / "lossless-native-images.json").read_text())["images"]
    assert len(images) == 108
    for row in images:
        path = ROOT / row["image"]
        assert digest(path) == row["sha256"]
        with Image.open(path) as source:
            assert list(source.size) == row["size"]
            header = source.info["opentt3d_pam_header"].encode("ascii")
            rgba = source.convert("RGBA").tobytes()
        assert hashlib.sha256(header+rgba).hexdigest() == row["pam_sha256"]
        assert len(header+rgba) == row["raw_bytes"]
    with gzip.open(HERE / "separate-rejected-hq-lock-catalogue.json.gz","rt") as source:
        catalogue = json.load(source)
    current = compile_catalogue(json.loads((HERE / "authored-source.json").read_text()))
    assert len(current["models"]) == 48 and not current["bindings"]
    assert all(fingerprint(model,current["materials"]) == fingerprint(catalogue["models"][name],catalogue["materials"])
               for name,model in current["models"].items())
    with gzip.open(PRIOR / "separate-rejected-hq-lock-catalogue.json.gz","rt") as source:
        previous = json.load(source)
    changed = {name for name,model in catalogue["models"].items()
               if fingerprint(model,catalogue["materials"]) != fingerprint(previous["models"][name],previous["materials"])}
    decisions = json.loads((HERE / "individual-decisions.json").read_text())["decisions"]
    assert changed == {row["model"] for row in decisions} and len(changed) == 6
    assert catalogue["bindings"] == previous["bindings"]
    reviews = json.loads((HERE / "combined-quality-reviews.json").read_text())
    scope = json.loads((PRIOR / "rejected-hq-lock-inventory.json").read_text())
    report = audit(catalogue,reviews,scope=scope)
    assert json.loads(json.dumps(report)) == json.loads((HERE / "rejected-hq-lock-quality.json").read_text())
    assert len(report["models"]) == 2998 and sum(row["status"] == "individually-reviewed" for row in report["models"]) == 189
    assert all(row["status"] not in ("stale-review","stale-evidence") and row["score"] < 8 for row in report["models"])
    assert not report["meets_objective"] and len(report["coverage_gaps"]) == 4
    assert b"\r" not in (HERE / "rejected-hq-lock-ratings.csv").read_bytes()
    print(json.dumps({"files_verified":len(manifest["files"]),"prior_seals_unchanged":True,"complete_pam_reconstructions":108,
                      "changed_owners":len(changed),"unchanged_models":len(catalogue["models"])-len(changed),
                      "quality_rows":2998,"individual_records":189,"approvals":0,"coverage_gaps":4,"meets_objective":False}))


if __name__ == "__main__":
    main()

"""Verify complete portable lossless evidence and conservative quality scopes."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
HQ = ROOT / "opentt3d/reviews/20261003/hq-large-column-repair"
sys.path.insert(0,str(ROOT / "tools/assets"))
from compile_voxels import compile_catalogue
from quality_audit import audit, fingerprint


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal",action="store_true",help="Refresh file hashes after adding documentation; never alter evidence bytes or reviews")
    args = parser.parse_args()
    if args.seal:
        for directory in (HQ,HERE):
            manifest = directory / "evidence-sha256.json"
            manifest.write_text(json.dumps({"files":{str(path.relative_to(ROOT)):digest(path)
                for path in sorted(directory.rglob("*")) if path.is_file() and path != manifest},"approvals":0},indent=2)+"\n")
    checked = 0
    for directory in (HQ,HERE):
        manifest = json.loads((directory / "evidence-sha256.json").read_text())
        for filename,expected in manifest["files"].items():
            assert digest(ROOT / filename) == expected,filename
            checked += 1
    images = json.loads((HERE / "lossless-native-images.json").read_text())["images"]
    assert len(images) == 1296
    for row in images:
        path = ROOT / row["image"]
        assert digest(path) == row["sha256"]
        with Image.open(path) as source:
            assert list(source.size) == row["size"]
            header = source.info["opentt3d_pam_header"].encode("ascii")
            rgba = source.convert("RGBA").tobytes()
        assert hashlib.sha256(header+rgba).hexdigest() == row["pam_sha256"],path
        assert len(header+rgba) == row["raw_bytes"]
    original_hq = json.loads((HQ / "before-source.json").read_text())
    candidate_hq = json.loads((HQ / "authored-source.json").read_text())
    names = {name for name,model in candidate_hq["models"].items() if name.startswith("hq_")}
    def compile_hq(source):
        return compile_catalogue({**source,"models":{name:value for name,value in source["models"].items() if name in names},
            "bindings":{category:{layout:states for layout,states in source["bindings"][category].items() if int(layout) >= 4}
                        for category in ("objects","object_ground")}})
    before,after = compile_hq(original_hq),compile_hq(candidate_hq)
    changed = {name for name,model in before["models"].items()
               if fingerprint(model,before["materials"]) != fingerprint(after["models"][name],after["materials"])}
    decisions = json.loads((HQ / "individual-decisions.json").read_text())["decisions"]
    assert changed == {row["model"] for row in decisions} and len(changed) == 6
    with gzip.open(HERE / "separate-rejected-hq-lock-catalogue.json.gz","rt") as source:
        merged = json.load(source)
    study = compile_catalogue(json.loads((HERE / "authored-source.json").read_text()))
    assert len(study["models"]) == 48 and not study["bindings"]
    assert all(fingerprint(model,study["materials"]) == fingerprint(merged["models"][name],merged["materials"])
               for name,model in study["models"].items())
    assert all(fingerprint(model,after["materials"]) == fingerprint(merged["models"][name],merged["materials"])
               for name,model in after["models"].items())
    with (HERE / "rejected-hq-lock-ratings.csv").open(newline="") as source:
        rows = list(csv.reader(source))
    assert len(rows) == 2999 and all(len(row) == 5 for row in rows)
    assert b"\r" not in (HERE / "rejected-hq-lock-ratings.csv").read_bytes()
    reviews = json.loads((HERE / "combined-quality-reviews.json").read_text())
    scope = json.loads((HERE / "rejected-hq-lock-inventory.json").read_text())
    current = audit(merged,reviews,scope=scope)
    assert json.loads(json.dumps(current)) == json.loads((HERE / "rejected-hq-lock-quality.json").read_text())
    assert all(row["status"] not in ("stale-evidence","stale-review") for row in current["models"])
    assert not current["meets_objective"] and len(current["coverage_gaps"]) == 4
    assert all(row["score"] < 8 for row in current["models"])
    print(json.dumps({"portable_files_verified":checked,"complete_pam_reconstructions":len(images),
                      "changed_hq_owners":len(changed),"unbound_lock_studies":48,"quality_rows":len(current["models"]),
                      "approvals":0,"coverage_gaps":4,"meets_objective":False}))


if __name__ == "__main__":
    main()

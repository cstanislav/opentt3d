"""Verify every portable byte and complete original PAM reconstruction; never approve art."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANIFEST = HERE / "evidence-sha256.json"
RECEIPT = HERE / "portable-verification.json"


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--seal",action="store_true")
    args = parser.parse_args()
    images,bytes_reconstructed = 0,0
    for inventory in HERE.glob("*-controls/lossless-images.json"):
        for row in json.loads(inventory.read_text()):
            path = ROOT / row["portable"]
            assert digest(path) == row["png_sha256"]
            with Image.open(path) as image:
                assert image.mode == "RGBA" and list(image.size) == row["size"]
                header = image.info["opentt3d_pam_header"].encode("ascii"); payload = header+image.tobytes()
            assert hashlib.sha256(payload).hexdigest() == row["pam_sha256"] and len(payload) == row["original_bytes"]
            images += 1; bytes_reconstructed += len(payload)
    for directory in ("retained-initial-world-controls","complete-water-world-controls","observer-separated-world-controls"):
        target = HERE / directory
        value = json.loads((target / "verification.json").read_text())
        assert value["quiet_world_controls"] == 40 and not value["strict_renderers_accepted"] and value["quality_approvals"] == 0
        for scope in ("canonical","complete","missing-owner","missing-water","changed-source"):
            manifest = json.loads((target / (scope+"-frozen-manifest.json")).read_text())
            for name,sha in manifest["sha256"].items():
                if name == "opentt3d": continue
                with gzip.open(target / (scope+"-"+Path(name).name+".gz"),"rb") as stream:
                    assert hashlib.file_digest(stream,"sha256").hexdigest() == sha
    source = json.loads((HERE / "resolved-source-paint.json").read_text())
    assert source["resolved_counts"] == {"relief":10,"water":7} and source["visible_original_water_pixels_exact"] == 5854
    fixed = json.loads((HERE / "fixed-pixel-preservation-controls/verification.json").read_text())
    assert fixed["quiet_controls"] == 40 and fixed["image_size"] == [640,480] and fixed["original_allow_hidpi"] is False
    assert all(row["exit_code"] == 0 for row in fixed["comparisons"] if "cross-backend" not in row["label"])
    assert all(row["dimension_mismatches"] == 0 for row in fixed["comparisons"])
    assert json.loads((HERE / "canonical-full-required-eight-receipt.json").read_text())["objective_met"] is False
    assert json.loads((HERE / "canonical-full-required-eight-quality.json").read_text())["meets_objective"] is False
    assert json.loads((HERE / "supported-required-eight-quality-retry.json").read_text())["meets_objective"] is False
    for name in ("supported-quality-reviews.json",):
        reviews = json.loads((HERE / name).read_text())
        assert len(reviews["models"]) == 8
        for row in reviews["models"].values():
            assert row["score"] == 5 and row["defects"] and not any(row["checks"].values())
            assert all(digest(ROOT / path) == sha for path,sha in row["evidence_sha256"].items())
    instances = json.loads((HERE / "supported-instance-records.json").read_text())
    assert len(instances) == 16 and all(row["score"] == 5 and not row["quality_approved"] for row in instances)
    assert all(digest(ROOT / path) == sha for row in instances for path,sha in row["evidence_sha256"].items())
    excluded = {MANIFEST,RECEIPT}
    files = sorted(path for path in HERE.rglob("*") if path.is_file() and path not in excluded and "__pycache__" not in path.parts
                   and path.suffix != ".pyc" and not path.name.startswith("portable-verify-command"))
    current = {str(path.relative_to(HERE)):{"sha256":digest(path),"bytes":path.stat().st_size} for path in files}
    if args.seal:
        MANIFEST.write_text(json.dumps({"format":1,"files":current,"quality_approved":False},indent=2)+"\n")
    recorded = json.loads(MANIFEST.read_text())
    assert recorded["files"] == current, "Evidence changed or is missing; inspect instead of silently accepting it"
    value = {"verified_utc":datetime.now(timezone.utc).isoformat(),"portable_files":len(files),"lossless_pam_reconstructions":images,
        "complete_original_pam_bytes_reconstructed":bytes_reconstructed,"all_file_hashes_exact":True,
        "quality_approvals":0,"required_eight_objective_met":False,"canonical_artwork_or_bindings_changed":False,
        "stopping_clock_unchanged":True}
    RECEIPT.write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value))


if __name__ == "__main__": main()

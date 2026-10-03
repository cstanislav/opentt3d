"""Seal explicit negative/provisional decisions and exact portable native evidence.

Run after both control drivers complete and every changed owner is individually
inspected. This never approves artwork, changes bindings or publishes a binary.
"""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BUILD = ROOT / "build-macos"
HQ = ROOT / "opentt3d/reviews/20261003/hq-large-column-repair"
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures, image
from compile_voxels import compile_catalogue
from inventory import inventory
from quality_audit import audit, fingerprint, write_ratings_csv


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source,"sha256").hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def write(path,value):
    if path.exists():
        assert json.loads(path.read_text()) == json.loads(json.dumps(value)),path
        return
    with path.open("x") as destination:
        json.dump(value,destination,indent=2)
        destination.write("\n")


def retain(source,target):
    assert source.is_file(),source
    if target.exists():
        assert digest(source) == digest(target),target
        return target
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert digest(source) == digest(target)
    return target


def compare(left,right,pattern,output):
    if output.exists():
        report = json.loads(output.read_text())
        assert report["reference"] == str(left) and report["actual"] == str(right),output
        return {"report":relative(output),"exit_code":int(bool(report["differences"])),"images":report["images"],
                "different_images":len(report["differences"]),"different_pixels":sum(row.get("changed_pixels",0) for row in report["differences"])}
    with output.with_suffix(".log").open("x") as log:
        result = subprocess.run([sys.executable,"tools/assets/compare_galleries.py",str(left),str(right),"--pattern",pattern,
                                 "--output",str(output)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode in (0,1) and output.is_file()
    report = json.loads(output.read_text())
    return {"report":relative(output),"exit_code":result.returncode,"images":report["images"],
            "different_images":len(report["differences"]),"different_pixels":sum(row.get("changed_pixels",0) for row in report["differences"])}


def main():
    hq_prefix,water_prefix = "breadth-original-hq-large-brick-corner","breadth-original-lock-bond-foam-study"
    hq_freeze = BUILD / (hq_prefix + "-frozen-build")
    water_freeze = BUILD / (water_prefix + "-frozen-build")
    hq_models = json.loads((hq_freeze / "baseset/opentt3d-voxels.json").read_text())
    water_models = json.loads((water_freeze / "baseset/opentt3d-voxels.json").read_text())
    before_hq = json.loads((BUILD / "breadth-original-hq-medium-perimeter-owner-catalogue.json").read_text())
    canonical_path = BUILD / "playable-release42-independent-extracted/OpenTT3D.app/Contents/Resources/baseset/opentt3d-voxels.json"
    canonical = json.loads(canonical_path.read_text())
    hq_decisions = json.loads((HQ / "individual-decisions.json").read_text())["decisions"]
    water_decisions = json.loads((HERE / "individual-decisions.json").read_text())["decisions"]
    hq_names = {row["model"] for row in hq_decisions}
    water_names = {row["model"] for row in water_decisions}
    assert len(hq_names) == len(hq_decisions) == 6 and len(water_names) == len(water_decisions) == 48
    assert hq_names == {name for name,model in before_hq["models"].items()
                        if fingerprint(model,before_hq["materials"]) != fingerprint(hq_models["models"][name],hq_models["materials"])}
    assert all(row["score"] < 8 and row["defects"] for row in hq_decisions + water_decisions)
    compactions = {}
    for path in BUILD.glob("review-compaction-*.json"):
        with path.open() as source:
            header = source.read(2048)
        if not any(prefix in header for prefix in (hq_prefix,water_prefix)):
            continue
        receipt = json.loads(path.read_text())
        for row in receipt["images"]:
            compactions[str(BUILD / row["image"])] = row
    native_records = []
    for prefix,out,names in ((hq_prefix,HQ,hq_names),(water_prefix,HERE,water_names)):
        freeze = BUILD / (prefix + "-frozen-build")
        manifest = json.loads((freeze / "manifest.json").read_text())
        assert all(digest(freeze / name) == identity for name,identity in manifest["sha256"].items())
        retain(freeze / "manifest.json",out / "frozen-manifest.json")
        runs_path = BUILD / (prefix + "-runs.json")
        runs = json.loads(runs_path.read_text())
        assert len(runs) == (8 if prefix == hq_prefix else 2) and all(row["exit_code"] == 0 for row in runs)
        retain(runs_path,out / "native-runs.json")
        for row in runs:
            run = Path(row["output"])
            label = run.name.removeprefix(prefix + "-")
            target = out / "native-controls" / label
            for filename in ("run.log","result.json","openttd.cfg","screenshot/smoke.png"):
                retain(run / filename,target / filename)
            assert json.loads((run / "result.json").read_text())["synchronous_original_save_verified"]
            gallery = run / "renderer3d-reference"
            for name,path in captures(gallery,"model-voxel-*").items():
                if not any(name == "model-voxel-" + owner + "-native" or
                           name in {f"model-voxel-{owner}-{view}" for view in range(8)} for owner in names):
                    continue
                portable = retain(path,target / "renderer3d-reference" / path.name)
                expected = compactions[str(path)]
                with Image.open(portable) as source:
                    header = source.info["opentt3d_pam_header"].encode("ascii")
                    pixels = source.convert("RGBA").tobytes()
                    size = list(source.size)
                original_hash = hashlib.sha256(header+pixels).hexdigest()
                assert original_hash == expected["pam_sha256"]
                native_records.append({"image":relative(portable),"sha256":digest(portable),"pam_sha256":original_hash,
                                       "size":size,"raw_bytes":expected["raw_bytes"],"png_bytes":portable.stat().st_size})
            for owner in names:
                retain(gallery / f"model-voxel-{owner}-native.json",target / "renderer3d-reference" / f"model-voxel-{owner}-native.json")
            if prefix == hq_prefix:
                for filename in ("objects.json","voxel-object-layouts.json"):
                    retain(gallery / filename,target / "renderer3d-reference" / filename)
                if row["backend"] == "vulkan":
                    exported = json.loads((gallery / "objects.json").read_text())
                    for tile in exported:
                        for layer in [tile["ground"]] + tile["body"]:
                            retain(gallery / layer["image"],target / "renderer3d-reference" / layer["image"])
        for decision in (hq_decisions if prefix == hq_prefix else water_decisions):
            name = decision["model"]
            if prefix == hq_prefix:
                climate = next(climate for climate in ("temperate","arctic","tropic") if "_"+climate+"_" in name)
                sheet = BUILD / (prefix + "-studies") / climate / "owners" / (name + ".png")
            else:
                sheet = BUILD / (prefix + "-sheets/owners") / (name + ".png")
            retain(sheet,out / "owners" / sheet.name)
    assert len(native_records) == 1296  # Six owners in8 HQ controls;48 owners in2 lock controls;9 views each.
    write(HERE / "lossless-native-images.json",{"images":native_records,"scope":"Complete lossless native images, not thumbnail/crop evidence. Original PAM headers/RGBA reconstruct exact compaction-receipt hashes."})
    retain(hq_freeze / "assets/3d/voxels.json",HQ / "authored-source.json")
    retain(hq_freeze / "tools/assets/test_hq_complete_voxels.py",HQ / "owner-tests.py")
    for out,prefix,logs in ((HQ,hq_prefix,("control-driver.log","compile.log","compaction.log","tests.log")),
                            (HERE,water_prefix,("control-driver.log","structural-tests.log","compaction.log"))):
        for suffix in logs:
            retain(BUILD / (prefix + "-" + suffix),out / suffix)
    for suffix in ("paired-gallery-strict.json","paired-gallery-strict.log","native-gallery-strict.json","native-gallery-strict.log",
                   "vulkan-prior-world-strict.json","vulkan-prior-world-strict.log","opengl-prior-world-strict.json","opengl-prior-world-strict.log","verification.json"):
        retain(BUILD / (water_prefix + "-" + suffix),HERE / ("native-verification.json" if suffix == "verification.json" else suffix))
    hq_comparisons,unchanged = [],[]
    for climate in ("temperate","arctic","tropic","toyland"):
        left = BUILD / f"{hq_prefix}-{climate}-vulkan/renderer3d-reference"
        right = BUILD / f"{hq_prefix}-{climate}-opengl/renderer3d-reference"
        hq_comparisons.append({"climate":climate,"scope":"strict complete paired HQ gallery",**compare(left,right,"model-voxel-*",HQ / (climate + "-paired-gallery-strict.json"))})
        hq_comparisons.append({"climate":climate,"scope":"strict native-only paired HQ gallery",**compare(left,right,"model-voxel-*-native",HQ / (climate + "-paired-native-strict.json"))})
        for backend in ("vulkan","opengl"):
            old_run = BUILD / f"breadth-original-hq-medium-perimeter-owner-{climate}-{backend}"
            new_run = BUILD / f"{hq_prefix}-{climate}-{backend}"
            hq_comparisons.append({"climate":climate,"backend":backend,"scope":"strict original size0 saved world preservation",**compare(old_run / "screenshot/smoke.png",new_run / "screenshot/smoke.png","*",HQ / (climate + "-" + backend + "-prior-world-strict.json"))})
            old = captures(old_run / "renderer3d-reference","model-voxel-hq_*")
            new = captures(new_run / "renderer3d-reference","model-voxel-hq_*")
            assert old.keys() == new.keys()
            for name,path in new.items():
                if any(name.startswith("model-voxel-" + owner + "-") for owner in hq_names):
                    continue
                a,b = image(old[name]),image(path)
                assert a.size == b.size and a.tobytes() == b.tobytes(),(climate,backend,name)
                unchanged.append({"climate":climate,"backend":backend,"image":name,"prior_sha256":digest(old[name]),"current_sha256":digest(path),"rgba_sha256":hashlib.sha256(b.tobytes()).hexdigest()})
    write(HQ / "strict-comparisons.json",hq_comparisons)
    write(HQ / "unchanged-native-images.json",{"images":unchanged,"count":len(unchanged),"scope":"Unchanged independent models only; exact full RGBA images. Joined geometry/source fidelity/backend/state approval is separate."})
    reviews = json.loads((ROOT / "assets/3d/quality_reviews.json").read_text())
    old_reviews = json.loads((ROOT / "opentt3d/reviews/20261003/hq-larger-rejected/prototype-quality-reviews.json").read_text())
    hq_reviews = {**old_reviews,"models":dict(old_reviews["models"])}
    lock_reviews = {"format":1,"models":{},"scope":"Explicit individual provisional/negative decisions for unbound models only; all acceptance checks are false."}
    for out,decisions,catalogue,destination in ((HQ,hq_decisions,hq_models,hq_reviews),(HERE,water_decisions,water_models,lock_reviews)):
        for decision in decisions:
            name = decision["model"]
            evidence = relative(out / "owners" / (name + ".png"))
            defects = decision["defects"] + ["Strict wider renderer acceptance remains rejected; no natural larger-HQ world or runtime lock/terrain/phases/custom/ship acceptance is established for this study."]
            destination["models"][name] = {"score":decision["score"],"fingerprint":fingerprint(catalogue["models"][name],catalogue["materials"]),
                "checks":{check:False for check in ("source","orbit","street","world","states","consistency")},
                "inspection_completed":["own-source","registered-native","orbit0..3","street0..3"],
                "evidence":[evidence],"evidence_sha256":{evidence:digest(ROOT / evidence)},"notes":["Individually inspected candidate only; not runtime artwork or 8/10 approval."]+defects,"defects":defects}
    write(HQ / "prototype-quality-reviews.json",hq_reviews)
    write(HERE / "prototype-quality-reviews.json",lock_reviews)
    merged = json.loads((hq_freeze / "baseset/opentt3d-voxels.json").read_text())
    study = compile_catalogue(json.loads((HERE / "authored-source.json").read_text()))
    offset = len(merged["materials"])
    merged["materials"].extend(study["materials"])
    for name,model in study["models"].items():
        merged["models"][name] = {**model,"runs":[run[:4]+[run[4]+offset] for run in model["runs"]]}
    assert len(merged["models"]) == 1963 and merged["bindings"] == hq_models["bindings"]
    merged_path = HERE / "separate-rejected-hq-lock-catalogue.json.gz"
    if merged_path.exists():
        with gzip.open(merged_path,"rt") as retained:
            assert json.load(retained) == merged
    else:
        with gzip.open(merged_path,"wt") as destination:
            destination.write(json.dumps(merged,separators=(",", ":")) + "\n")
    combined = {**reviews,"models":{**reviews["models"],**hq_reviews["models"],**lock_reviews["models"]}}
    write(HERE / "combined-quality-reviews.json",combined)
    summaries = []
    for label,catalogue,review in (("canonical",canonical,reviews),("rejected-hq",hq_models,{**reviews,"models":{**reviews["models"],**hq_reviews["models"]}}),
                                    ("rejected-hq-lock",merged,combined)):
        scope = inventory(catalogue)
        report = audit(catalogue,review,scope=scope)
        assert not report["meets_objective"] and len(report["coverage_gaps"]) == 4
        assert all(row["score"] < 8 for row in report["models"])
        write(HERE / (label + "-inventory.json"),scope)
        write(HERE / (label + "-quality.json"),report)
        write_ratings_csv(HERE / (label + "-ratings.csv"),report["models"])
        individual = sum(row["status"] == "individually-reviewed" for row in report["models"])
        expected_rows,expected_reviews = {"canonical":(2866,57),"rejected-hq":(2950,141),"rejected-hq-lock":(2998,189)}[label]
        assert (len(report["models"]),individual) == (expected_rows,expected_reviews)
        summaries.append({"scope":label,"rows":expected_rows,"individual_records":individual,"approvals":0,"coverage_gaps":4,"scores":report["score_counts"]})
        if label == "rejected-hq-lock":
            if not (HERE / "pre-updated-working-ratings.csv").exists():
                retain(ROOT / "opentt3d/MODEL_RATINGS.csv",HERE / "pre-updated-working-ratings.csv")
            write_ratings_csv(ROOT / "opentt3d/MODEL_RATINGS.csv",report["models"])
            assert b"\r" not in (ROOT / "opentt3d/MODEL_RATINGS.csv").read_bytes()
    for name in ("assets","native","harness","boundary"):
        retain(BUILD / ("breadth-original-hq-lock-detail-" + name + ".log"),HERE / (name + "-tests.log"))
    summary = {"sealed_utc":datetime.now(timezone.utc).isoformat(),"native_controls":10,"changed_hq_owners":6,"changed_unbound_lock_owners":48,
               "portable_lossless_native_images":len(native_records),"unchanged_hq_full_views_exact":len(unchanged),
               "quality_scopes":summaries,"runtime_source_changed":False,"released_artwork_changed":False,"approvals":0,
               "scope":"Source-guided candidate geometry/paint progress only. All54 changed owners are individually reviewed with retained defects. Strict renderer/source/world/state/consistency and the complete catalogue-wide8/10/performance/platform goal remain unmet. Recommended.42 remains unchanged."}
    write(HERE / "verification.json",summary)
    for out in (HQ,HERE):
        write(out / "evidence-sha256.json",{"files":{relative(path):digest(path) for path in sorted(out.rglob("*")) if path.is_file()},"approvals":0})
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

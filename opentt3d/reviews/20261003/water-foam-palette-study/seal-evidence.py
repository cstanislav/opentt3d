"""Retain six individual foam repairs and exact evidence; never approve runtime coverage."""
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
PRIOR = ROOT / "opentt3d/reviews/20261003/water-bond-foam-study"
BUILD = ROOT / "build-macos"
PREFIX = "breadth-original-lock-foam-palette-study"
sys.path.insert(0,str(ROOT / "tools/assets"))
from compare_galleries import captures, image
from compile_voxels import compile_catalogue
from quality_audit import audit, fingerprint, write_ratings_csv


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source,"sha256").hexdigest()


def retain(source,target):
    assert source.is_file(),source
    if target.exists():
        assert digest(source) == digest(target),target
        return
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)


def write(path,value):
    if path.exists():
        assert json.loads(path.read_text()) == json.loads(json.dumps(value)),path
        return
    with path.open("x") as destination:
        json.dump(value,destination,indent=2)
        destination.write("\n")


def main():
    decisions = json.loads((HERE / "individual-decisions.json").read_text())["decisions"]
    names = {row["model"] for row in decisions}
    assert len(names) == len(decisions) == 6 and all(row["score"] == 6 and row["defects"] for row in decisions)
    current = compile_catalogue(json.loads((HERE / "authored-source.json").read_text()))
    before = compile_catalogue(json.loads((HERE / "before-authored-source.json").read_text()))
    changed = {name for name,model in current["models"].items()
               if fingerprint(model,current["materials"]) != fingerprint(before["models"][name],before["materials"])}
    assert changed == names and len(current["models"]) == 48 and not current["bindings"]
    freeze = BUILD / (PREFIX + "-frozen-build")
    frozen = json.loads((freeze / "manifest.json").read_text())
    assert all(digest(freeze / name) == expected for name,expected in frozen["sha256"].items())
    retain(freeze / "manifest.json",HERE / "frozen-manifest.json")
    runs = json.loads((BUILD / (PREFIX + "-runs.json")).read_text())
    assert len(runs) == 2 and all(row["exit_code"] == 0 for row in runs)
    retain(BUILD / (PREFIX + "-runs.json"),HERE / "native-runs.json")
    native,unchanged = [],[]
    for run in runs:
        directory = Path(run["output"])
        backend = run["backend"]
        target = HERE / "native-controls" / backend
        for filename in ("run.log","openttd.cfg","result.json","screenshot/smoke.png"):
            retain(directory / filename,target / filename)
        assert json.loads((directory / "result.json").read_text())["synchronous_original_save_verified"]
        gallery = directory / "renderer3d-reference"
        old_gallery = PRIOR / "native-controls" / backend / "renderer3d-reference"
        old,new = captures(old_gallery,"model-voxel-lock_study_*"),captures(gallery,"model-voxel-lock_study_*")
        assert old.keys() == new.keys() and len(new) == 432
        for name,path in new.items():
            if not any(name.startswith("model-voxel-" + owner + "-") for owner in names):
                a,b = image(old[name]),image(path)
                assert a.size == b.size and a.tobytes() == b.tobytes(),name
                unchanged.append({"backend":backend,"image":name,"prior_sha256":digest(old[name]),"current_sha256":digest(path),
                                  "rgba_sha256":hashlib.sha256(b.tobytes()).hexdigest()})
                continue
            portable = target / "renderer3d-reference" / path.name
            retain(path,portable)
            with Image.open(portable) as source:
                header = source.info["opentt3d_pam_header"].encode("ascii")
                rgba = source.convert("RGBA").tobytes()
                size = list(source.size)
            native.append({"image":str(portable.relative_to(ROOT)),"sha256":digest(portable),
                           "pam_sha256":hashlib.sha256(header+rgba).hexdigest(),"raw_bytes":len(header+rgba),"size":size})
        for name in names:
            retain(gallery / f"model-voxel-{name}-native.json",target / "renderer3d-reference" / f"model-voxel-{name}-native.json")
    assert len(native) == 108 and len(unchanged) == 756
    receipts = {}
    for path in BUILD.glob("review-compaction-*.json"):
        with path.open() as source:
            header = source.read(2048)
        if PREFIX not in header:
            continue
        for row in json.loads(path.read_text())["images"]:
            receipts[str(BUILD / row["image"])] = row["pam_sha256"]
    for row in native:
        relative = Path(row["image"]).relative_to(HERE.relative_to(ROOT) / "native-controls")
        path = BUILD / (PREFIX + "-" + relative.parts[0]) / "renderer3d-reference" / relative.name
        assert row["pam_sha256"] == receipts[str(path)]
    write(HERE / "lossless-native-images.json",{"images":native,"count":108,"scope":"Full lossless native images reconstruct original PAM hashes exactly; thumbnails are not used for equality."})
    write(HERE / "unchanged-native-images.json",{"images":unchanged,"count":756,"scope":"All42 unchanged owners retain every one of their nine full views in both backends, exact to the sealed prior evidence."})
    for row in decisions:
        name = row["model"]
        retain(BUILD / (PREFIX + "-sheets/owners") / (name + ".png"),HERE / "owners" / (name + ".png"))
    logs = (("control-driver.log","control-driver.log"),("study-structural-tests.log","structural-tests.log"),
            ("study-compaction.log","compaction.log"),("canonical-assets.log","canonical-assets.log"),
            ("canonical-assets.json","canonical-assets.json"),("local-tests.log","local-tests.log"))
    for source,target in logs:
        retain(BUILD / ("breadth-original-lock-foam-palette-" + source),HERE / target)
    for suffix in ("paired-gallery-strict.json","paired-gallery-strict.log","native-gallery-strict.json","native-gallery-strict.log",
                   "vulkan-prior-world-strict.json","vulkan-prior-world-strict.log","opengl-prior-world-strict.json","opengl-prior-world-strict.log","verification.json"):
        retain(BUILD / (PREFIX + "-" + suffix),HERE / ("native-verification.json" if suffix == "verification.json" else suffix))
    strict = json.loads((HERE / "paired-gallery-strict.json").read_text())
    assert strict["images"] == 432 and len(strict["differences"]) == 9
    assert sum(row["changed_pixels"] for row in strict["differences"]) == 9
    native_pairs = json.loads((HERE / "native-gallery-strict.json").read_text())
    assert native_pairs["images"] == 48 and not native_pairs["differences"]
    assert all(not json.loads((HERE / (backend + "-prior-world-strict.json")).read_text())["differences"]
               for backend in ("vulkan","opengl"))
    reviews = json.loads((PRIOR / "prototype-quality-reviews.json").read_text())
    for decision in decisions:
        name = decision["model"]
        evidence = str((HERE / "owners" / (name + ".png")).relative_to(ROOT))
        defects = decision["defects"] + ["Nine strict orbit/street backend pixels remain rejected. Runtime locks, independent water phases, terrain joins, full custom families, ships and complete source/world/state/consistency acceptance are not established."]
        reviews["models"][name] = {"score":6,"fingerprint":fingerprint(current["models"][name],current["materials"]),
            "checks":{check:False for check in ("source","orbit","street","world","states","consistency")},
            "inspection_completed":["own-source","registered-native","orbit0..3","street0..3"],"evidence":[evidence],
            "evidence_sha256":{evidence:digest(ROOT / evidence)},"notes":["Individually inspected unbound source-palette study; not8/10 approval."]+defects,"defects":defects}
    assert all(reviews["models"][name] == json.loads((PRIOR / "prototype-quality-reviews.json").read_text())["models"][name]
               for name in current["models"] if name not in names)
    write(HERE / "prototype-quality-reviews.json",reviews)
    combined = json.loads((PRIOR / "combined-quality-reviews.json").read_text())
    combined["models"].update(reviews["models"])
    write(HERE / "combined-quality-reviews.json",combined)
    with gzip.open(PRIOR / "separate-rejected-hq-lock-catalogue.json.gz","rt") as source:
        merged = json.load(source)
    offset = len(merged["materials"])
    merged["materials"].extend(current["materials"])
    for name,model in current["models"].items():
        merged["models"][name] = {**model,"runs":[run[:4]+[run[4]+offset] for run in model["runs"]]}
    assert len(merged["models"]) == 1963
    compressed = HERE / "separate-rejected-hq-lock-catalogue.json.gz"
    if compressed.exists():
        with gzip.open(compressed,"rt") as source:
            assert json.load(source) == merged
    else:
        with gzip.open(compressed,"wt") as source:
            source.write(json.dumps(merged,separators=(",", ":"))+"\n")
    scope = json.loads((PRIOR / "rejected-hq-lock-inventory.json").read_text())
    assert scope["voxel_bindings"] == merged["bindings"]
    report = audit(merged,combined,scope=scope)
    assert len(report["models"]) == 2998 and sum(row["status"] == "individually-reviewed" for row in report["models"]) == 189
    assert not report["meets_objective"] and len(report["coverage_gaps"]) == 4 and all(row["score"] < 8 for row in report["models"])
    assert all(row["status"] not in ("stale-evidence","stale-review") for row in report["models"])
    write(HERE / "rejected-hq-lock-quality.json",report)
    write_ratings_csv(HERE / "rejected-hq-lock-ratings.csv",report["models"])
    # Preserve the immediately prior working CSV before updating the candidate.
    if not (HERE / "before-working-ratings.csv").exists():
        retain(ROOT / "opentt3d/MODEL_RATINGS.csv",HERE / "before-working-ratings.csv")
    write_ratings_csv(ROOT / "opentt3d/MODEL_RATINGS.csv",report["models"])
    assert b"\r" not in (ROOT / "opentt3d/MODEL_RATINGS.csv").read_bytes()
    gates = BUILD / (PREFIX + "-required-eight")
    gates.mkdir(exist_ok=True)
    catalogue = gates / "catalogue.json"
    if not catalogue.exists():
        catalogue.write_text(json.dumps(merged,separators=(",", ":"))+"\n")
    with (gates / "gate.log").open("w") as log:
        result = subprocess.run([sys.executable,"tools/assets/quality_audit.py","--catalogue",str(catalogue),
            "--reviews",str(HERE / "combined-quality-reviews.json"),"--inventory",str(PRIOR / "rejected-hq-lock-inventory.json"),
            "--output",str(gates / "quality.json"),"--require-eight"],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 1 and json.loads((gates / "quality.json").read_text()) == json.loads(json.dumps(report))
    retain(gates / "gate.log",HERE / "required-eight-gate.log")
    summary = {"sealed_utc":datetime.now(timezone.utc).isoformat(),"changed_unbound_owners":6,"prior_models_exact":42,
               "unchanged_full_native_views":756,"new_portable_lossless_native_images":108,"native_controls":2,
               "native_pairs_exact":48,"strict_changed_images":9,"strict_changed_pixels":9,"prior_saved_worlds_exact":2,
               "rows":2998,"individual_records":189,"approvals":0,"coverage_gaps":4,"required_eight_exit_code":1,
               "runtime_bound":False,"runtime_source_changed":False,"released_artwork_changed":False,
               "scope":"Animated glitter palette250 and explicitly authored half-unit foam width improve six independently reviewed owners. Original dimensions/nonfoam paint/geometry and forty-two other owners remain exact. Native/source phase is not full lifecycle, runtime geometry, custom/terrain/ship or8/10 acceptance; recommended.42 remains unchanged."}
    write(HERE / "verification.json",summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

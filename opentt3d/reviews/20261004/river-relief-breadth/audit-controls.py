"""Compare full native captures exactly and retain lossless portable copies without deletion."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image, PngImagePlugin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compact_reviews import load_pam, verify_png


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",required=True)
    parser.add_argument("--phase",choices=("initial","revised"),required=True)
    args = parser.parse_args()
    build = ROOT / "build-macos"
    target = HERE / (args.phase+"-native-controls")
    if target.exists(): parser.error("Retain the previous audit and choose a new phase/prefix")
    (target / "strict-comparisons").mkdir(parents=True)
    rows = json.loads((build / (args.prefix+"-runs.json")).read_text())
    assert len(rows) == 8 and all(row["exit_code"] == 0 for row in rows)
    assert len({row["binary_sha256"] for row in rows}) == 1
    images = []
    for row in rows:
        source = ROOT / row["output"]
        destination = target / source.name
        destination.mkdir()
        for name in ("run.log","result.json","openttd.cfg"):
            shutil.copy2(source / name,destination / name)
        for directory in ("scripts","save","screenshot"):
            shutil.copytree(source / directory,destination / directory)
        gallery = destination / "renderer3d-reference"
        gallery.mkdir()
        for path in (source / "renderer3d-reference").iterdir():
            if path.suffix != ".pam":
                if path.is_file(): shutil.copy2(path,gallery / path.name)
                continue
            header,size,pixels = load_pam(path)
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("opentt3d_pam_header",header.decode("ascii"))
            portable = gallery / (path.stem+".png")
            Image.frombytes("RGBA",size,pixels).save(portable,pnginfo=metadata)
            verify_png(portable,header,size,pixels)
            assert hashlib.sha256(header+pixels).hexdigest() == digest(path)
            images.append({"original":str(path.relative_to(ROOT)),"portable":str(portable.relative_to(ROOT)),
                "pam_sha256":digest(path),"png_sha256":digest(portable),"original_bytes":path.stat().st_size,
                "portable_bytes":portable.stat().st_size,"size":list(size),"exact_pam_reconstruction":True,"original_retained":True})
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    shutil.copy2(build / (args.prefix+"-runs.json"),target / "runs.json")
    shutil.copy2(build / (args.prefix+"-controls.log"),target / "controls.log")
    frozen = build / (args.prefix+"-frozen-build")
    shutil.copy2(frozen / "manifest.json",target / "frozen-manifest.json")
    shutil.copy2(frozen / "authored-source.json",target / "frozen-authored-source.json")
    shutil.copy2(frozen / "compiler-snapshot.py",target / "compiler-snapshot.py")
    with gzip.open(target / "diagnostic-catalogue.json.gz","wb") as destination:
        destination.write((frozen / "baseset/opentt3d-voxels.json").read_bytes())
    assert gzip.decompress((target / "diagnostic-catalogue.json.gz").read_bytes()) == (frozen / "baseset/opentt3d-voxels.json").read_bytes()
    runs = {(row["climate"],row["backend"],row["scope"]):target / Path(row["output"]).name for row in rows}
    plan = []
    for pattern,label in (("model-voxel-river_relief_study_*","all-model-views"),("model-voxel-river_relief_study_*-native","registered-native")):
        plan.append((label,runs["temperate","vulkan","study"] / "renderer3d-reference",
                     runs["temperate","opengl","study"] / "renderer3d-reference",pattern))
    for climate in ("temperate","toyland"):
        for backend in ("vulkan","opengl"):
            plan.append((f"{climate}-{backend}-canonical-preservation",runs[climate,backend,"canonical"] / "screenshot/smoke.png",
                         runs[climate,backend,"study"] / "screenshot/smoke.png","*"))
        for scope in ("canonical","study"):
            plan.append((f"{climate}-{scope}-paired-world",runs[climate,"vulkan",scope] / "screenshot/smoke.png",
                         runs[climate,"opengl",scope] / "screenshot/smoke.png","*"))
    comparisons = []
    for label,left,right,pattern in plan:
        report = target / "strict-comparisons" / (label+".json")
        with (target / "strict-comparisons" / (label+".log")).open("x") as log:
            result = subprocess.run([sys.executable,"tools/assets/compare_galleries.py",str(left),str(right),
                "--pattern",pattern,"--output",str(report),"--pixel-details","12"],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        assert result.returncode in (0,1) and report.is_file()
        value = json.loads(report.read_text())
        comparisons.append({"label":label,"exit_code":result.returncode,"images":value["images"],
            "different_images":len(value["differences"]),"different_pixels":sum(row.get("changed_pixels",0) for row in value["differences"]),
            "report":str(report.relative_to(ROOT)),"strict_complete_rgba":True,"masks_or_tolerance_used":False})
    summary = {"audited_utc":datetime.now(timezone.utc).isoformat(),"phase":args.phase,"quiet_controls":8,
        "lossless_pam_reconstructions":len(images),"original_bytes_reconstructed":sum(row["original_bytes"] for row in images),
        "portable_image_bytes":sum(row["portable_bytes"] for row in images),"full_world_images":8,"comparisons":comparisons,
        "runtime_bound":False,"native_checks_are_not_aesthetic_acceptance":True,"geometry_approvals":0,"all_original_build_files_retained":True}
    (target / "verification.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

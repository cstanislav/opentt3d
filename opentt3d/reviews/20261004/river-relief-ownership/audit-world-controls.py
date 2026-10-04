"""Retain exact worlds/source owners and compare entire RGBA images without exemptions."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from PIL import Image, PngImagePlugin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from compact_reviews import load_pam, verify_png
from compare_galleries import captures, image


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def compare(left,right,pattern,report):
    a,b = ({"world":left},{"world":right}) if left.is_file() else (captures(left,pattern),captures(right,pattern))
    assert a and a.keys() == b.keys(), "Complete, nonempty image sets are required"
    differences, pixels = [],0
    for name in sorted(a):
        first,second = image(a[name]),image(b[name])
        if first.size != second.size:
            differences.append({"name":name,"changed_pixels":None,"reference_size":list(first.size),
                "actual_size":list(second.size),"reason":"Complete image dimensions differ; no resizing, masks or tolerance permitted"})
            continue
        x,y = first.tobytes(),second.tobytes(); pixels += first.width*first.height
        if x == y: continue
        changes = [i for i in range(0,len(x),4) if x[i:i+4] != y[i:i+4]]
        differences.append({"name":name,"changed_pixels":len(changes),"pixels":[{
            "pixel":[i//4%first.width,i//4//first.width],"reference":list(x[i:i+4]),"actual":list(y[i:i+4])} for i in changes[:12]]})
    value = {"reference":str(left.relative_to(ROOT)),"actual":str(right.relative_to(ROOT)),"pattern":pattern,
        "images":len(a),"pixels":pixels,"differences":differences,"masks_or_tolerance_used":False,
        "strict_complete_rgba":True,"exit_code":int(bool(differences))}
    report.write_text(json.dumps(value,indent=2)+"\n")
    return {"label":report.stem,"report":str(report.relative_to(ROOT)),"images":len(a),
        "different_images":len(differences),"different_pixels":sum(row["changed_pixels"] or 0 for row in differences),
        "dimension_mismatches":sum(row["changed_pixels"] is None for row in differences),
        "exit_code":value["exit_code"],"strict_complete_rgba":True,"masks_or_tolerance_used":False}


def retain_file(source,target):
    if target.exists():
        assert digest(source) == digest(target), "Retain unexpected different portable files"
    else: shutil.copy2(source,target)


def retain_run(source,target,images):
    target.mkdir(exist_ok=True)
    for name in ("run.log","result.json","openttd.cfg"): retain_file(source / name,target / name)
    for name in ("scripts","save","screenshot"):
        for path in (source / name).rglob("*"):
            relative = path.relative_to(source)
            if path.is_dir(): (target / relative).mkdir(parents=True,exist_ok=True)
            elif path.is_file():
                (target / relative).parent.mkdir(parents=True,exist_ok=True)
                retain_file(path,target / relative)
    destination = target / "renderer3d-reference"; destination.mkdir(exist_ok=True)
    for path in sorted((source / "renderer3d-reference").iterdir()):
        if path.suffix == ".pam":
            header,size,pixels = load_pam(path)
            meta = PngImagePlugin.PngInfo(); meta.add_text("opentt3d_pam_header",header.decode("ascii"))
            portable = destination / (path.stem+".png")
            if not portable.exists(): Image.frombytes("RGBA",size,pixels).save(portable,pnginfo=meta)
            verify_png(portable,header,size,pixels)
            pam_sha = digest(path); original_bytes = path.stat().st_size
            assert hashlib.sha256(header+pixels).hexdigest() == pam_sha
        elif path.suffix == ".png":
            with Image.open(path) as picture:
                header_text = picture.info.get("opentt3d_pam_header")
                if header_text is None:
                    retain_file(path,destination / path.name); continue
                header = header_text.encode("ascii"); size = picture.size; pixels = picture.tobytes()
            portable = destination / path.name; retain_file(path,portable)
            verify_png(portable,header,size,pixels)
            pam_sha = hashlib.sha256(header+pixels).hexdigest(); original_bytes = len(header)+len(pixels)
        else:
            if path.is_file(): retain_file(path,destination / path.name)
            continue
        images.append({"original":str(path.relative_to(ROOT)),"portable":str(portable.relative_to(ROOT)),
            "pam_sha256":pam_sha,"png_sha256":digest(portable),"original_bytes":original_bytes,
            "portable_bytes":portable.stat().st_size,"size":list(size),"exact_pam_reconstruction":True,
            "original_retained_or_losslessly_compacted":True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",required=True); parser.add_argument("--output",required=True)
    parser.add_argument("--finish-retained-partial",action="store_true",help="Verify existing portable files and finish an explicitly retained incomplete audit")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]+",args.output): parser.error("Use a fresh simple audit directory name")
    target = HERE / args.output
    if target.exists() and (not args.finish_retained_partial or (target / "verification.json").exists()): parser.error("Retain prior audits")
    (target / "strict-comparisons").mkdir(parents=True,exist_ok=args.finish_retained_partial)
    rows = json.loads((HERE / (args.prefix+"-runs.json")).read_text())
    assert len(rows) == 40 and all(row["exit_code"] == 0 for row in rows)
    images,emitted,selector_rows = [],[],[]
    for row in rows:
        source = ROOT / row["output"]; destination = target / source.name
        retain_run(source,destination,images)
        log = (destination / "run.log").read_text()
        instances = re.findall(r"diagnostic voxel river relief slope (\d+) climate (\d+) source (\d+) captured at (\d+),(\d+) original height (\d+)",log)
        emitted.extend({"slope":int(slope),"climate":int(climate),"source":int(sprite),"tile_xy":[int(x),int(y)],
            "source_height":int(z),"backend":row["backend"],"seed":row["seed"],"run":str(destination.relative_to(ROOT))}
            for slope,climate,sprite,x,y,z in instances)
        selectors = json.loads((destination / "renderer3d-reference/river-selectors.json").read_text())
        selector_rows.append({"run":str(destination.relative_to(ROOT)),"observations":len(selectors["observations"]),
                              "original_source_callbacks_retained":True})
        expected = row["scope"] == "complete" and row["graphics"] == "OpenGFX2 Classic"
        assert bool(instances) == expected
        if row["gallery"]:
            assert "20 supported river diagnostic LOD views" in log and "20 supported river LOD rebuild views" in log
            assert len(captures(destination / "renderer3d-reference","model-voxel-river-supported-*")) == 36
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    (target / "actual-emitted-instances.json").write_text(json.dumps(emitted,indent=2)+"\n")
    (target / "selector-observations.json").write_text(json.dumps(selector_rows,indent=2)+"\n")
    shutil.copy2(HERE / (args.prefix+"-runs.json"),target / "runs.json")
    for scope in ("canonical","complete","missing-owner","missing-water","changed-source"):
        frozen = ROOT / "build-macos" / (args.prefix+"-"+scope+"-frozen-build")
        manifest = json.loads((frozen / "manifest.json").read_text())
        assert all(digest(frozen / name) == sha for name,sha in manifest["sha256"].items())
        shutil.copy2(frozen / "manifest.json",target / (scope+"-frozen-manifest.json"))
        for name in manifest["sha256"]:
            if name == "opentt3d": continue
            portable = target / (scope+"-"+Path(name).name+".gz")
            def valid_companion():
                try:
                    with gzip.open(portable,"rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest() == manifest["sha256"][name]
                except (OSError,EOFError): return False
            if portable.exists() and not valid_companion():
                rejected = portable.with_name(portable.name+".retained-incomplete")
                if rejected.exists(): raise ValueError("Retain previous incomplete companion")
                portable.rename(rejected)
            if not portable.exists():
                with (frozen / name).open("rb") as source, portable.open("xb") as encoded:
                    with gzip.GzipFile(fileobj=encoded,mode="wb",mtime=0) as destination: shutil.copyfileobj(source,destination,1024*1024)
            assert valid_companion()
    runs = {(row["climate"],row["seed"],row["backend"],row["scope"],row["graphics"]):target / Path(row["output"]).name for row in rows}
    comparisons = []
    def add(label,left,right,pattern="*"):
        result = compare(left,right,pattern,target / "strict-comparisons" / (label+".json"))
        comparisons.append(result); return result
    for climate,seed in (("temperate",271828),("arctic",271828),("tropic",271828),("toyland",271828),("tropic",161803)):
        for scope in ("canonical","complete"):
            a,b = [runs[climate,seed,backend,scope,"OpenGFX2 Classic"] for backend in ("vulkan","opengl")]
            add(f"{climate}-{seed}-{scope}-paired-world",a / "screenshot/smoke.png",b / "screenshot/smoke.png")
            add(f"{climate}-{seed}-{scope}-paired-atlas",a / "renderer3d-reference",b / "renderer3d-reference","model-world-atlas-*")
    for climate in ("temperate","toyland"):
        for backend in ("vulkan","opengl"):
            a = runs[climate,271828,backend,"canonical","OpenGFX2 Classic"]
            for scope in ("missing-owner","missing-water","changed-source"):
                b = runs[climate,271828,backend,scope,"OpenGFX2 Classic"]
                result = add(f"{climate}-{backend}-{scope}-fallback",a / "screenshot/smoke.png",b / "screenshot/smoke.png")
                assert result["exit_code"] == 0, "Incomplete/changed families must retain complete original worlds"
            a,b = [runs[climate,271828,backend,scope,"OpenGFX"] for scope in ("canonical","complete")]
            result = add(f"{climate}-{backend}-alternate-fallback",a / "screenshot/smoke.png",b / "screenshot/smoke.png")
            assert result["exit_code"] == 0, "Alternate sets must retain complete original worlds"
        a,b = [runs[climate,271828,backend,"complete","OpenGFX2 Classic"] / "renderer3d-reference" for backend in ("vulkan","opengl")]
        add(climate+"-all-relief-model-views",a,b,"model-voxel-river_relief_study_*")
        add(climate+"-registered-native-relief",a,b,"model-voxel-river_relief_study_*-native")
    for climate in ("temperate","arctic","tropic","toyland"):
        a,b = [runs[climate,271828,backend,"complete","OpenGFX2 Classic"] / "renderer3d-reference" for backend in ("vulkan","opengl")]
        add(climate+"-all-supported-views",a,b,"model-voxel-river-supported-*")
        add(climate+"-registered-native-supported",a,b,"model-voxel-river-supported-*-native")
    combinations = sorted({(row["climate"],row["slope"]) for row in emitted})
    assert len(combinations) == 16
    result = {"audited_utc":datetime.now(timezone.utc).isoformat(),"quiet_world_controls":40,"full_worlds":40,
        "lossless_pam_reconstructions":len(images),"original_bytes_reconstructed":sum(row["original_bytes"] for row in images),
        "actual_emitted_instances":len(emitted),"actual_climate_slope_combinations":combinations,
        "source_heights":sorted({row["source_height"] for row in emitted}),"comparisons":comparisons,
        "supported_lod_views":160,"supported_lod_retirement_views":160,"generic_cpu_palette_instance_views":1536,
        "diagnostic_bound_only":True,"canonical_artwork_or_bindings_changed":False,
        "native_model_equality_is_not_aesthetic_approval":True,"independent_phase_ship_and_live_relief_picking_accepted":False,
        "strict_renderers_accepted":not any(row["exit_code"] for row in comparisons),"quality_approvals":0}
    (target / "verification.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__": main()

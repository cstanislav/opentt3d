"""Strict per-backend original-world preservation; never substitute native gallery equality."""
from pathlib import Path
import datetime, hashlib, json, sys

sys.path.insert(0,"tools/assets")
from compare_galleries import image

root = Path("build-macos")
out = root / "breadth-original-river-selector-classic-world-verification.json"
assert not out.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
runs = json.loads((root / "breadth-original-river-selector-runs.json").read_text())
assert len(runs) == 16 and all(row["exit_code"] == 0 for row in runs)
rows = []
for climate in ("temperate","arctic","tropic","toyland"):
    for backend in ("vulkan","opengl"):
        off = next(row for row in runs if row["climate"] == climate and row["backend"] == backend and not row["tracing"])
        on = next(row for row in runs if row["climate"] == climate and row["backend"] == backend and row["tracing"])
        for mode,reference,actual in (("default-off-prior",Path(off["reference_output"]),Path(off["output"])),
                                      ("tracing-on-off",Path(off["output"]),Path(on["output"])):
            a_path,b_path = reference / "screenshot/smoke.png",actual / "screenshot/smoke.png"
            a,b = image(a_path),image(b_path)
            assert a.size == b.size
            x,y = a.tobytes(),b.tobytes()
            changed = [index//4 for index in range(0,len(x),4) if x[index:index+4] != y[index:index+4]]
            row = {"climate":climate,"backend":backend,"mode":mode,"images":1,"pixels":a.width*a.height,
                   "changed_pixels":len(changed),"reference":str(a_path),"actual":str(b_path),
                   "reference_sha256":digest(a_path),"actual_sha256":digest(b_path)}
            if changed:
                first = changed[0]
                row.update(first_pixel=[first%a.width,first//a.width],reference_rgba=list(x[first*4:first*4+4]),actual_rgba=list(y[first*4:first*4+4]))
            rows.append(row)
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"comparisons":rows,
    "images":16,"pixels":sum(row["pixels"] for row in rows),"changed_pixels":sum(row["changed_pixels"] for row in rows),
    "masks":False,"tolerance":0,"geometry_approvals":0,
    "scope":"Eight default-off vs prior observer and eight tracing-on/off actual saved world comparisons, each with original synchronous save acknowledgement/file checks. Strict whole-world RGBA equality only; not animation/full-family/raised geometry/ships or quality acceptance."}
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"world_images":16,"changed_pixels":summary["changed_pixels"],"tolerance":0,"masks":False}))
assert summary["changed_pixels"] == 0

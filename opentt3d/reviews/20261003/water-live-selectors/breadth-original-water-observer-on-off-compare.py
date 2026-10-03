"""Retain strict observer-on/default-off world comparisons; never mask differences."""
from pathlib import Path
import datetime, hashlib, json, subprocess

root = Path("build-macos").resolve()
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
rows = []
for climate in ("temperate","arctic","tropic","toyland"):
    for backend in ("vulkan","opengl"):
        on = root / f"breadth-original-lock-live-source-{climate}-0-0-{backend}"
        off = root / f"breadth-original-water-observer-preservation-{climate}-{backend}-observer-off"
        assert json.loads((on / "result.json").read_text())["synchronous_original_save_verified"]
        assert json.loads((off / "result.json").read_text())["synchronous_original_save_verified"]
        assert (on / "renderer3d-reference/water-live.json").is_file()
        assert not (off / "renderer3d-reference/water-live.json").exists()
        report = root / f"breadth-original-water-observer-{climate}-{backend}-on-off-strict.json"
        assert not report.exists()
        result = subprocess.run([python,"tools/assets/compare_galleries.py",str(on / "screenshot/smoke.png"),
            str(off / "screenshot/smoke.png"),"--output",str(report)],stdout=subprocess.DEVNULL)
        assert result.returncode in (0,1) and report.is_file()
        comparison = json.loads(report.read_text())
        rows.append({"climate":climate,"backend":backend,"on_output":str(on),"off_output":str(off),"exit_code":result.returncode,
            "different_images":len(comparison["differences"]),"different_pixels":sum(row.get("changed_pixels",0) for row in comparison["differences"]),
            "report":str(report),"report_sha256":digest(report)})
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"comparisons":rows,
    "all_worlds_strict_exact":all(row["exit_code"] == 0 for row in rows),
    "scope":"Actual recorded diagnostic-on and default-off controls load the same original paused natural-lock saves and use the same centers/atlas/picking checks. Vulkan uses presented capture on both; OpenGL compares the native presented and external-executable viewport paths too. Exact equality is measured, never presumed; no tolerance, UI mask, source-state forcing, geometry or quality approval."}
output = root / "breadth-original-water-observer-on-off-verification.json"
assert not output.exists()
output.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"worlds":len(rows),"all_worlds_strict_exact":summary["all_worlds_strict_exact"],"differences":sum(row["different_pixels"] for row in rows)}))
if not summary["all_worlds_strict_exact"]:
    raise SystemExit(1)

"""Retain full close worlds and strict paired comparisons for each individual model."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    spec = importlib.util.spec_from_file_location("river_world_audit",HERE / "audit-world-controls.py")
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    target = HERE / "close-world-controls"
    if target.exists(): raise ValueError("Retain prior close world audits")
    (target / "strict-comparisons").mkdir(parents=True)
    rows = json.loads((HERE / "close-world-runs.json").read_text())
    assert len(rows) == 32 and all(row["exit_code"] == 0 for row in rows)
    images = []
    for row in rows: audit.retain_run(ROOT / row["output"],target / Path(row["output"]).name,images)
    runs = {(row["climate"],row["slope"],row["backend"],row["scope"]):target / Path(row["output"]).name for row in rows}
    comparisons = []
    for climate in ("temperate","toyland"):
        for slope in (3,6,9,12):
            for scope in ("canonical","complete"):
                a,b = [runs[climate,slope,backend,scope] for backend in ("vulkan","opengl")]
                comparisons.append(audit.compare(a / "screenshot/smoke.png",b / "screenshot/smoke.png","*",
                    target / "strict-comparisons" / f"{climate}-{slope}-{scope}-paired-world.json"))
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    (target / "runs.json").write_text(json.dumps(rows,indent=2)+"\n")
    result = {"audited_utc":datetime.now(timezone.utc).isoformat(),"quiet_controls":32,"individual_models":8,
        "lossless_pam_reconstructions":len(images),"original_bytes_reconstructed":sum(row["original_bytes"] for row in images),
        "comparisons":comparisons,"live_relief_specific_picking_phase_and_ship_acceptance":False,"approvals":0,
        "all_renderer_pairs_accepted":not any(row["exit_code"] for row in comparisons)}
    (target / "verification.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__": main()

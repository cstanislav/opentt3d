"""Retain tracing-on/off worlds and preserve the earlier incomplete camera controls."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def load_driver():
    spec = importlib.util.spec_from_file_location("river_world_audit",HERE / "audit-world-controls.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    audit = load_driver()
    target = HERE / "component-world-controls"
    if target.exists(): raise ValueError("Retain prior component controls")
    (target / "strict-comparisons").mkdir(parents=True)
    rows = json.loads((HERE / "components-runs.json").read_text())
    assert len(rows) == 16 and all(row["exit_code"] == 0 for row in rows)
    images = []
    for row in rows: audit.retain_run(ROOT / row["output"],target / Path(row["output"]).name,images)
    runs = {(row["climate"],row["backend"],row["traced"]):target / Path(row["output"]).name for row in rows}
    comparisons = []
    for climate in ("temperate","arctic","tropic","toyland"):
        for backend in ("vulkan","opengl"):
            a,b = [runs[climate,backend,traced] for traced in (True,False)]
            result = audit.compare(a / "screenshot/smoke.png",b / "screenshot/smoke.png","*",
                target / "strict-comparisons" / (climate+"-"+backend+"-tracing-preservation.json"))
            assert result["exit_code"] == 0
            comparisons.append(result)
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    (target / "runs.json").write_text(json.dumps(rows,indent=2)+"\n")
    result = {"audited_utc":datetime.now(timezone.utc).isoformat(),"quiet_controls":16,"lossless_pam_reconstructions":len(images),
        "original_bytes_reconstructed":sum(row["original_bytes"] for row in images),"comparisons":comparisons,
        "native_components_are_not_ownership_or_quality_approval":True,"approvals":0}
    (target / "verification.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__": main()

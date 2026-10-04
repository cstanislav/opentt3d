"""Require exact full same-backend worlds/atlases, preserving cross-backend failures."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    spec = importlib.util.spec_from_file_location("river_world_audit",HERE / "audit-world-controls.py")
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    target = HERE / "fixed-pixel-preservation-controls"
    if target.exists(): raise ValueError("Retain prior controls")
    (target / "strict-comparisons").mkdir(parents=True)
    rows = json.loads((HERE / "fixed-pixel-preservation-runs.json").read_text())
    assert len(rows) == 40 and all(row["exit_code"] == 0 for row in rows)
    images = []
    for row in rows: audit.retain_run(ROOT / row["output"],target / Path(row["output"]).name,images)
    runs = {(row["climate"],row["backend"],row["revision"],row["scope"],row["traced"]):target / Path(row["output"]).name for row in rows}
    comparisons = []
    def compare_pair(label,a,b,require_equal):
        for suffix,left,right,pattern in (("world",a / "screenshot/smoke.png",b / "screenshot/smoke.png","*"),
            ("atlas",a / "renderer3d-reference",b / "renderer3d-reference","model-world-atlas-*")):
            value = audit.compare(left,right,pattern,target / "strict-comparisons" / (label+"-"+suffix+".json"))
            if require_equal: assert value["exit_code"] == 0
            comparisons.append(value)
    for climate in ("temperate","arctic","tropic","toyland"):
        for backend in ("vulkan","opengl"):
            for scope in ("canonical","complete"):
                a,b = [runs[climate,backend,revision,scope,True] for revision in ("complete-water","observer-separated")]
                compare_pair(climate+"-"+backend+"-"+scope+"-observer-revision",a,b,True)
            a,b = [runs[climate,backend,"observer-separated","complete",traced] for traced in (True,False)]
            compare_pair(climate+"-"+backend+"-complete-tracing",a,b,True)
        for scope in ("canonical","complete"):
            a,b = [runs[climate,backend,"observer-separated",scope,True] for backend in ("vulkan","opengl")]
            compare_pair(climate+"-"+scope+"-cross-backend",a,b,False)
    (target / "lossless-images.json").write_text(json.dumps(images,indent=2)+"\n")
    (target / "runs.json").write_text(json.dumps(rows,indent=2)+"\n")
    value = {"audited_utc":datetime.now(timezone.utc).isoformat(),"quiet_controls":40,"image_size":[640,480],
        "original_allow_hidpi":False,"lossless_pam_reconstructions":len(images),
        "original_bytes_reconstructed":sum(row["original_bytes"] for row in images),"same_backend_revision_world_pairs":16,
        "same_backend_revision_atlas_views":64,"runtime_tracing_world_pairs":8,"runtime_tracing_atlas_views":32,
        "comparisons":comparisons,"quality_approvals":0,"cross_backend_accepted":False,
        "canonical_artwork_or_bindings_changed":False,"normal_application_hidpi_default_changed":False}
    (target / "verification.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value))


if __name__ == "__main__": main()

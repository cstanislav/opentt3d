"""Retain observed climate/selector sources, including flat controls; author no geometry."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = ROOT / "opentt3d/reviews/20261003/river-natural-selector-breadth"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    target = HERE / "climate-source-index.json"
    if target.exists(): raise ValueError("Retain the previous source matrix")
    prior = json.loads((PRIOR / "registered-source-sheets/index.json").read_text())
    paths = {row["sha256"]:ROOT / row["portable_image"] for row in json.loads((PRIOR / "source-file-map.json").read_text())}
    selected = json.loads((HERE / "source-index.json").read_text())
    portable = {row["sha256"]:row["portable_source"] for row in selected}
    rows = []
    for climate in ("temperate","arctic","tropic","toyland"):
        for slope in (0,3,6,9,12):
            row = next(row for row in prior if row["base_set_family"] == "classic" and
                       row["climate_name"] == climate and row["feature"] == "CF_RIVER_SLOPE" and row["slope"] == slope)
            sha = row["sha256"]
            if sha not in portable:
                assert slope == 0,"An uninspected climate relief source differs; do not reuse a different source model"
                destination = HERE / "sources" / (climate+"-flat-control.pam")
                if destination.exists(): raise ValueError("Retain the existing source")
                shutil.copy2(paths[sha],destination)
                assert digest(destination) == sha
                portable[sha] = str(destination.relative_to(ROOT))
            else:
                assert digest(ROOT / portable[sha]) == sha
            suffix = {3:"sw",6:"se",9:"nw",12:"ne"}.get(slope)
            model = f"river_relief_study_{'island' if climate == 'toyland' else 'rock'}_{suffix}" if suffix else None
            rows.append({**row,"portable_source":portable[sha],"study_model":model,
                "source_bytes_equal_to_inspected_study":slope != 0,"flat_control_has_no_authored_relief":slope == 0,
                "runtime_bound":False,"quality_approved":False,
                "scope":"One actual observed selector/source per slope/climate. Flat is a full retained water control, not an authored raised asset. Equal source bytes do not transfer state/instance approval or establish all heights, neighbourhoods, phases or custom completeness."})
    assert len(rows) == 20 and sum(row["study_model"] is not None for row in rows) == 16
    target.write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps({"observed_climate_sources":20,"relief_source_instances":16,"flat_controls":4,"unique_complete_source_files":len(portable),"runtime_bound":False,"approvals":0}))


if __name__ == "__main__":
    main()

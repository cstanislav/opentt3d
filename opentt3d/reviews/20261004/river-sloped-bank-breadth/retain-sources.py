"""Retain actual selected sloped bank owners, without fabricating unselected corners."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = ROOT / "opentt3d/reviews/20261003/river-natural-selector-breadth/source-file-map.json"
FLAT = HERE.parent / "river-bank-breadth"
CLIMATES = ("temperate","arctic","tropic","toyland")
GROUPS = {12:(6,"se",(0,2)),24:(12,"ne",(1,3)),36:(3,"sw",(1,3)),48:(9,"nw",(0,2))}
sys.path.insert(0,str(ROOT / "tools/assets"))
from compact_reviews import load_pam


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    target = HERE / "sources"
    if target.exists(): raise ValueError("Retain earlier actual source selections")
    target.mkdir(); prior = json.loads(PRIOR.read_text()); sources = []; observations = {}
    for climate,label in enumerate(CLIMATES):
        for start,(slope,direction,edges) in GROUPS.items():
            for edge in edges:
                requested = start+edge
                choices = [row for row in prior if row["base_set_family"] == "classic" and row["backend"] == "vulkan" and
                    row["feature"] == "CF_RIVER_EDGE" and row["climate"] == label and row["requested_offset"] == requested and row["resolved_offset"] == requested]
                positive = [row for row in choices if row["source_height"] > 0]
                entry = min(positive or choices,key=lambda row:row["source_height"])
                selector_path = Path(entry["original_image"]).parent / "river-selectors.json"
                if selector_path not in observations: observations[selector_path] = json.loads(selector_path.read_text())["observations"]
                selected = next(row for row in observations[selector_path] if row["feature"] == "CF_RIVER_EDGE" and
                    row["tile"] == entry["tile"] and row["requested_offset"] == requested and row["resolved_offset"] == requested)
                assert selected["slope"] == slope and selected["climate"] == climate and selected["base_set"] == "OpenGFX2 Classic"
                assert selected["offset_callback"] and not selected["absent"] and selected["feature_flags"] == 0
                original = ROOT / entry["portable_image"]; assert digest(original) == entry["sha256"]
                header,size,pixels = load_pam(original)
                assert any(pixels[index+3] for index in range(0,len(pixels),4))
                assert all(value%4 == 0 for value in selected["source_offset"]+selected["source_size"])
                assert list(size) == [value//4 for value in selected["source_size"]]
                destination = target / f"{label}-{direction}-edge{edge:02d}.pam"; shutil.copy2(original,destination)
                sources.append({**selected,"direction":direction,"edge":edge,"group_start":start,
                    "source_state":"elevated" if selected["source_height"] > 0 else "sea-level-observation",
                    "native_offset":[value//4 for value in selected["source_offset"]],"native_size":list(size),
                    "source_pam":str(destination.relative_to(ROOT)),"source_pam_sha256":digest(destination),
                    "original_selection_provenance":entry,"prior_source_file_map_sha256":digest(PRIOR),
                    "source_selector_observation_sha256":digest(selector_path),"quality_approved":False,
                    "scope":"One actual already-selected Classic sloped bank owner. Neither the remaining ten conditional slots per slope nor other height/terrain/shore/snow/desert/grid/custom/phase/absence states are inferred."})
    assert len(sources) == 32 and len({(row["climate"],row["slope"],row["edge"]) for row in sources}) == 32
    (HERE / "actual-source-index.json").write_text(json.dumps(sources,indent=2)+"\n")
    full = json.loads((FLAT / "complete-bank-family-inventory.json").read_text())
    states = []
    for original in full["states"]:
        source = next((row for row in sources if row["climate"] == original["climate"] and row["requested_offset"] == original["offset"]),None)
        states.append({**original,"sloped_actual_source":source,"sloped_candidate_authored":False,
            "sloped_slot_unobserved_in_this_increment":original["offset"] >= 12 and source is None,
            "unobserved_is_not_intentional_absence":True,"runtime_source_coverage_accepted":False,"quality_approved":False})
    counts = Counter(row["source_state"] for row in sources)
    value = {"retained_utc":datetime.now(timezone.utc).isoformat(),"actual_sloped_bank_owners":32,"source_states":dict(counts),
        "full_conditional_bank_instances":240,"earlier_flat_candidates":48,"sloped_slots_without_actual_observation_here":160,
        "states":states,"existing_flat_evidence_sha256":digest(FLAT / "evidence-sha256.json"),
        "earlier_flat_increment_commit":"333da9864","runtime_bank_coverage_accepted":0,"quality_approvals":0}
    (HERE / "complete-conditional-family-inventory.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({key:value[key] for key in ("actual_sloped_bank_owners","source_states","full_conditional_bank_instances","sloped_slots_without_actual_observation_here","runtime_bank_coverage_accepted","quality_approvals")}))


if __name__ == "__main__": main()

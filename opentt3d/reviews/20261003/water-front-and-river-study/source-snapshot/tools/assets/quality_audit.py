#!/usr/bin/env python3
"""Rate every authored model conservatively; visual evidence never follows a rename/edit.

The default score is a structural screening score, not a visual approval. A score
of eight requires an individual review tied to exact occupied cells/six-face paint
and checked source, orbit, street, world, state and material-consistency evidence.
Missing original families stay in the same report rather than disappearing behind
the authored-model count. This tool never writes simulation or artwork data.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_CHECKS = ("source", "orbit", "street", "world", "states", "consistency")


def fingerprint(model, materials):
    """Material IDs can be renumbered; exact face colours/positions cannot."""
    runs = []
    for run in model["runs"]:
        value = run[:4]+[materials[run[4]-1]]
        if runs and runs[-1][1:3] == value[1:3] and runs[-1][0]+runs[-1][3] == value[0] and runs[-1][4] == value[4]:
            runs[-1][3] += value[3]
        else:
            runs.append(value)
    value = {key:model[key] for key in ("size", "origin", "cell_size")}
    value["runs"] = runs
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def definition_fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",", ":")).encode()).hexdigest()


def original_object_layer_model(catalogue, objects, tile, role, index, climate):
    """Only a complete original family selects volume; a partial HQ stays original.

    This reports binding availability, not source, world or aesthetic acceptance.
    Independently projected ordinary terrain is not a raised HQ artwork binding.
    """
    kind,stage = tile["object_id"],tile["size_stage"] or 0
    if not 0 <= kind < 5 or not 0 <= climate < 4 or (kind == 0 and climate == 3) or (kind == 1 and climate >= 2):
        return None
    family = [row for row in objects["tiles"] if row["object_id"] == kind and (row["size_stage"] or 0) == stage]
    if len(family) != (4 if kind == 4 else 1) or {row["part"] for row in family} != (set(range(4)) if kind == 4 else {0}):
        return None
    bindings = catalogue["bindings"]
    def bound(category, layout):
        name = bindings.get(category,{}).get(str(layout),{}).get(str(climate))
        return name if name in catalogue["models"] else None
    for row in family:
        layout = kind if kind < 4 else 4+stage*4+row["part"]
        if len(row["body"]) > 1 or (row["body"] and not bound("objects",layout)):
            return None
        if kind == 4 and not bound("object_ground",layout):
            return None
    if index != 0 or (role == "ground" and kind < 4):
        return None
    layout = kind if kind < 4 else 4+stage*4+tile["part"]
    return bound("objects" if role == "body" else "object_ground",layout)


def original_water_rows(water, renderer_sources):
    """Keep all original owners/conditional bank selectors, not just authored models.

    These read-only default tables are not live NewGRF provenance. No binding or
    model review can turn source entries into runtime lock coverage by itself.
    """
    if not isinstance(water,dict) or water.get("format") != 1:
        raise ValueError("Original water inventory must retain the complete source table")
    locks = water.get("locks")
    if (not isinstance(locks,list) or len(locks) != 12 or
            any(not isinstance(lock,dict) or type(lock.get("part")) is not int or type(lock.get("direction")) is not int for lock in locks) or
            {(lock["part"],lock["direction"]) for lock in locks} != {(part,direction) for part in range(3) for direction in range(4)}):
        raise ValueError("Original water inventory needs all three parts/four directions")
    rows = []

    def row(name, source, climate, representation, score, notes, renderer=False):
        value = {"source":source,"climate":climate,"selection":water["runtime_selection"],"source_sha256":water["source_sha256"]}
        if renderer:
            value["renderer"] = renderer_sources
        rows.append({"model":name,"representation":representation,"score":score,
            "status":"individual-visual-review-pending" if renderer else "original-sprite-fallback" if name.startswith("missing/lock/") else "live-source-selection-pending",
            "fingerprint":definition_fingerprint(value),"required_runtime_review":True,
            "owners":[],"checks":{},"evidence":[],"notes":[notes]})

    for lock in sorted(locks,key=lambda lock:(lock["part"],lock["direction"])):
        owners = lock.get("body")
        if not isinstance(owners,list) or len(owners) != 2 or [owner.get("face") for owner in owners if isinstance(owner,dict)] != ["rear","front"]:
            raise ValueError("Original locks retain separate rear/front source owners")
        for face,owner in enumerate(owners):
            variants = owner.get("default_sprite_variants")
            if not isinstance(variants,list) or len(variants) != 2 or any(type(sprite) is not int or sprite <= 0 for sprite in variants):
                raise ValueError("Original lock owners need both default elevation sources")
            for elevation in range(2):
                for climate in range(4):
                    name = f"missing/lock/elevation{elevation}/part{lock['part']}/direction{lock['direction']}/face{face}/climate{climate}"
                    row(name,{"layout":lock,"owner":owner,"elevation":elevation},climate,"original-source-layer",1,
                        f"Original {owner['face']} wall, default sprite{variants[elevation]}, at its own sequence anchor. Actual custom IDs/bytes require live provenance; sorting extents are not dimensions. No runtime structural replacement or visual approval is established.")
        for elevation in range(2):
            for climate in range(4):
                name = f"original/lock/elevation{elevation}/part{lock['part']}/direction{lock['direction']}/water/climate{climate}"
                row(name,{"layout":lock,"ground":lock["ground"],"elevation":elevation},climate,"native-water-layer",4,
                    "Original independently owned animated water surface, with original source-height/custom-flat/slope selection. A surface is intentional, not a wall billboard or missing body. Live palette phases, terrain registration, continuity and ships still require individual review.",renderer=True)
    slopes = water.get("default_water_slopes")
    if (not isinstance(slopes,list) or len(slopes) != 4 or
            any(not isinstance(slope,dict) or type(slope.get("slot")) is not int for slope in slopes) or
            {slope["slot"] for slope in slopes} != set(range(4))):
        raise ValueError("Original water inventory needs all four default water slopes")
    for slope in sorted(slopes,key=lambda slope:slope["slot"]):
        for climate in range(4):
            row(f"original/water-slope/{slope['slot']}/climate{climate}",slope,climate,"native-water-layer",4,
                "Original water-slope surface retains separate water ownership. Static default source IDs do not prove live Classic/NewGRF source selection, all animated phases, shore/bank continuity or ship clearance.",renderer=True)
    edges = water.get("river_edge_source_offsets")
    groups = ("SLOPE_FLAT","SLOPE_SE","SLOPE_NE","SLOPE_SW","SLOPE_NW")
    if (not isinstance(edges,list) or len(edges) != 60 or
            any(not isinstance(edge,dict) or type(edge.get("edge")) is not int or type(edge.get("offset")) is not int for edge in edges) or
            {(edge.get("slope"),edge["edge"],edge["offset"]) for edge in edges} !=
            {(slope,edge,group*12+edge) for group,slope in enumerate(groups) for edge in range(12)}):
        raise ValueError("Original river inventory needs all sixty conditional bank offsets")
    for edge in sorted(edges,key=lambda edge:edge["offset"]):
        for climate in range(4):
            row(f"unresolved/river-bank/{edge['slope']}/edge{edge['edge']}/climate{climate}",edge,climate,"original-source-layer",1,
                "Conditional original CF_RIVER_EDGE owner: live base/callback/connectivity/source bytes must be observed before geometry is bound. When the original feature supplies no bank it is intentionally absent, not a license to invent one. Static offsets or unrelated dike models do not establish river-bank coverage.")
    return rows


def apply_review(row, entry, root, evidence_sha256=None):
    if entry is None:
        return
    name, rating, notes = row["model"], entry.get("score"), entry.get("notes")
    if type(rating) is not int or not 1 <= rating <= 10 or not isinstance(notes,list) or not notes or any(not isinstance(note,str) or not note.strip() for note in notes):
        raise ValueError(f"Invalid individual score/notes: {name}")
    if rating >= 8 and row["representation"] == "original-source-layer":
        raise ValueError(f"Missing structural coverage cannot be promoted by a source-layer review: {name}")
    if entry.get("fingerprint") != row["fingerprint"]:
        row["status"] = "stale-review"
        row["notes"].append("Prior review fingerprint differs; do not carry its rating to changed artwork.")
        return
    checks, evidence = entry.get("checks", {}), entry.get("evidence", [])
    defects = entry.get("defects", [])
    if not isinstance(defects,list) or any(not isinstance(defect,str) or not defect.strip() for defect in defects):
        raise ValueError(f"Defects must be an explicit list of unresolved observations: {name}")
    if not isinstance(checks,dict) or any(type(value) is not bool for value in checks.values()):
        raise ValueError(f"Checks must be explicit booleans: {name}")
    if not isinstance(evidence,list) or not evidence or any(not isinstance(path,str) or not (root/path).is_file() for path in evidence):
        raise ValueError(f"Missing individual review evidence: {name}")
    hashes = entry.get("evidence_sha256", {path:evidence_sha256[path] for path in evidence if path in (evidence_sha256 or {})})
    if not isinstance(hashes,dict) or (rating >= 8 and set(hashes) != set(evidence)):
        raise ValueError(f"8/10 needs immutable hashes for every evidence file: {name}")
    if any(path not in evidence or not isinstance(digest,str) or len(digest) != 64 for path,digest in hashes.items()):
        raise ValueError(f"Invalid evidence hash: {name}")
    if any(hashlib.sha256((root/path).read_bytes()).hexdigest() != digest for path,digest in hashes.items()):
        row["status"] = "stale-evidence"
        row["notes"].append("Retained evidence bytes changed; its prior rating cannot be accepted.")
        return
    if rating >= 8 and ("defects" not in entry or not all(checks.get(key) is True for key in REVIEW_CHECKS) or defects):
        raise ValueError(f"8/10 needs all six review checks and no unresolved defects: {name}")
    row.update(score=rating,status="individually-reviewed",notes=notes,checks=checks,evidence=evidence,
               evidence_sha256=hashes,defects=defects)


def audit(catalogue, reviews, root=ROOT, scope=None):
    if catalogue.get("format") != 1 or reviews.get("format") != 1 or not isinstance(reviews.get("models"),dict):
        raise ValueError("Unsupported catalogue/review format")
    evidence_sha256 = reviews.get("evidence_sha256", {})
    if not isinstance(evidence_sha256,dict):
        raise ValueError("Shared review evidence hashes must be a dictionary")
    owners = defaultdict(list)
    for category, identifiers in catalogue["bindings"].items():
        for identifier, states in identifiers.items():
            for state, name in states.items():
                owners[name].append(f"{category}/{identifier}/{state}")
    rows = []
    for name, model in sorted(catalogue["models"].items()):
        digest = fingerprint(model, catalogue["materials"])
        score, status = (5, "structural-screen-only") if owners[name] else (3, "unbound-diagnostic")
        reasons = ["Authored occupied 3D cells; individual visual/detail/world consistency review is not yet established."]
        rows.append({"model":name, "representation":"authored-voxel", "score":score, "status":status,
                     "fingerprint":digest, "owners":owners[name], "checks":{}, "evidence":[], "notes":reasons,
                     "required_runtime_review":bool(owners[name])})
    # These assemblies are still compiled and retained even when superseded by
    # the voxel runtime. List them explicitly; do not confuse them with approvals.
    legacy = json.loads((root/"assets/3d/models.json").read_text())
    for model in legacy["models"]:
        rows.append({"model":"legacy/"+model["name"], "representation":"legacy-assembly", "score":3,
                     "status":"retained-reference-not-reviewed", "owners":[], "checks":{}, "evidence":[], "required_runtime_review":False,
                     "fingerprint":definition_fingerprint({"model":model,"materials":legacy["materials"]}),
                     "notes":["Retained non-voxel reference assembly; not an approved replacement for the current voxel catalogue."]})
    for pack in ("houses", "trees", "industries", "vehicles"):
        source = json.loads((root/f"assets/3d/{pack}.json").read_text())
        key = "assemblies" if pack == "vehicles" else "models"
        for identifier in sorted(source[key]):
            tree = pack == "trees"
            rows.append({"model":f"profile/{pack}/{identifier}", "representation":"projected-material-3d-tree" if tree else "retained-profile",
                         "score":4 if tree else 3, "status":"individual-visual-review-pending" if tree else "retained-reference-not-reviewed",
                         "required_runtime_review":tree, "owners":[], "checks":{}, "evidence":[],
                         "fingerprint":definition_fingerprint({"pack":source,"identifier":identifier}),
                         "notes":["Active permitted 3D tree branch/crown representation; seven original lifecycle states and palettes require review." if tree else
                                  "Retained legacy profile; current voxel bindings are rated separately. Custom/unbound fallback coverage is not inferred."]})
    gaps = [
        {"family":"original objects/HQ", "score":1, "status":"missing-voxel-coverage",
         "notes":"24 layouts/37 layers, including five four-tile HQ sizes; source exports do not provide 3D coverage."},
        {"family":"canal locks", "score":1, "status":"original-sprite-fallback",
         "notes":"All three lock parts/four directions and elevated variants still need true structural voxel coverage."},
        {"family":"river banks and water slopes", "score":1, "status":"incomplete-coverage",
         "notes":"Original NewGRF river edges and lock water slopes require separate review; flat animated water is intentionally a surface."},
        {"family":"disasters and uncatalogued world sprites", "score":1, "status":"coverage-not-established",
         "notes":"Complete runtime missing-geometry/parameter inventory remains required; the authored list alone is not the world catalogue."},
    ]
    # Runtime procedural geometry must also be reviewed, not hidden by JSON counts.
    procedural = []
    for truck in range(2):
        for layout in range(6):
            for tram in range(2 if layout >= 4 else 1):
                for detail in range(2):
                    procedural.append(f"road-stop/{truck}/{layout}/tram{tram}/detail{detail}")
    for kind, count in (("bridge",13), ("tunnel",4), ("running-rail",4), ("rail-station",3),
                        ("rail-signal",6), ("catenary",1), ("crossing",4), ("fence",7),
                        ("foundation",13), ("ground-detail",5)):
        procedural.extend(f"{kind}/{identifier}" for identifier in range(count))
    renderer_sources = {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted((root/"src/renderer3d").rglob("*")) if path.is_file() and path.suffix in (".cpp",".h",".hpp",".vert",".frag",".glsl")}
    for name in procedural:
        rows.append({"model":"procedural/"+name, "representation":"procedural-runtime", "score":4,
                     "status":"individual-visual-review-pending", "owners":[], "checks":{}, "evidence":[], "required_runtime_review":True,
                     "fingerprint":definition_fingerprint({"sources":renderer_sources,"variant":name}),
                     "notes":["Existing 3D implementation; all original layout/slope/state/LOD variants still need individual consistency ratings."]})
    runtime_scope = None
    intentional_absences = []
    if scope is not None:
        if scope.get("voxel_bindings") != catalogue["bindings"]:
            raise ValueError("Original-state inventory must use the exact reviewed catalogue bindings")
        runtime_scope = {key:scope[key] for key in ("vehicles","houses","trees","industry_tiles","airport_tiles","depots","ship_depots","docks","effect_types","effect_source_frames","original_objects")}
        climate_names = ("temperate","arctic","tropic","toyland")
        object_climates = {typ["id"]:typ["climates"] for typ in scope["original_objects"]["types"]}
        for tile in scope["original_objects"]["tiles"]:
            layers = [("ground",0,tile["ground"])]+[("body",index,layer) for index,layer in enumerate(tile["body"])]
            for climate in range(4):
                if climate_names[climate] not in object_climates[tile["object_id"]]:
                    intentional_absences.append({"object":tile["object_id"],"part":tile["part"],"stage":tile["size_stage"],
                                                 "climate":climate_names[climate],"reason":"Original object climate restriction; no model is required for an unavailable object."})
                    continue
                if not tile["body"]:
                    intentional_absences.append({"object":tile["object_id"],"part":tile["part"],"stage":tile["size_stage"],
                                                 "climate":climate_names[climate],"reason":"Original separate body is absent; raised ground artwork remains independently required."})
                for role,index,layer in layers:
                    stage = tile["size_stage"] if tile["size_stage"] is not None else 0
                    name = f"missing/object/{tile['object_id']}/{stage}/{tile['part']}/{role}{index}/climate{climate}"
                    bound_model = original_object_layer_model(catalogue,scope["original_objects"],tile,role,index,climate)
                    if bound_model:
                        layout = tile["object_id"] if tile["object_id"] < 4 else 4+stage*4+tile["part"]
                        category = "objects" if role == "body" else "object_ground"
                        rows.append({"model":name.replace("missing/","original/",1),"score":5,"status":"structural-screen-only",
                                     "representation":"authored-voxel-instance","required_runtime_review":True,
                                     "owners":[f"{category}/{layout}/{climate}"],"checks":{},"evidence":[],
                                     "fingerprint":definition_fingerprint({"source":layer,"layout":tile,"climate":climate,
                                         "model":bound_model,"voxel":fingerprint(catalogue["models"][bound_model],catalogue["materials"])}),
                                     "notes":[f"Original {tile['kind']} {role} layer sprite{layer['sprite']} selects {bound_model} in its complete original family. Binding availability is not individual source/world/state acceptance; its instance does not inherit a model's visual score."]})
                        continue
                    if tile["object_id"] < 4 and role == "ground":
                        rows.append({"model":name.replace("missing/","original/",1),"score":4,"status":"individual-visual-review-pending",
                                     "representation":"native-terrain-layer","required_runtime_review":True,"owners":[],"checks":{},"evidence":[],
                                     "fingerprint":definition_fingerprint({"source":layer,"layout":tile,"climate":climate,"renderer":renderer_sources}),
                                     "notes":[f"Original {tile['kind']} flat ground sprite{layer['sprite']} remains an independently projected terrain surface, not an invented solid. Original climate/slope/registration/palette/ownership reviews remain required; no raised HQ artwork is covered by this path."]})
                        continue
                    rows.append({"model":name,"score":1,"status":"missing-voxel-coverage","representation":"original-source-layer",
                                 "fingerprint":definition_fingerprint({"source":layer,"layout":tile,"climate":climate}),
                                 "required_runtime_review":True,"owners":[],"checks":{},"evidence":[],
                                  "notes":[f"Original {tile['kind']} {role} layer, sprite{layer['sprite']}. Raised ground artwork still needs its own volume; source exports are not coverage."]})
        missing_objects = sum(row["model"].startswith("missing/object/") for row in rows)
        gaps[0]["notes"] = f"24 original layouts/37 layers retain every climate/owner/absence. {missing_objects} available source-layer instances still lack complete-family volumes; ordinary flat terrain remains native and independently review-pending. Binding availability never establishes visual approval."
        if "water_structures" in scope:
            runtime_scope["water_structures"] = scope["water_structures"]
            rows.extend(original_water_rows(scope["water_structures"],renderer_sources))
            gaps[1]["notes"] = "192 original climate/elevation/part/direction/rear/front wall instances remain separately required. Live source verification alone is not structural coverage or visual acceptance."
            gaps[2]["notes"] = "96 independent lock water owners, sixteen default slope/climate surfaces and240 unresolved conditional river-bank selectors remain individually review-pending. Absent CF_RIVER_EDGE supplies no invented bank; no custom source or animation approval is inferred."
        else:
            gaps.append({"family":"original water-state inventory","score":1,"status":"scope-incomplete",
                         "notes":"Regenerate the exact-catalogue inventory with water_structures; do not silently drop original wall/water owners or conditional river-bank absence."})
    else:
        gaps.append({"family":"original-state inventory","score":1,"status":"scope-incomplete",
                     "notes":"Use --inventory from the exact reviewed catalogue; model counts do not enumerate original states, body absences, palettes or climate restrictions."})
    unknown = reviews["models"].keys()-{row["model"] for row in rows}
    if unknown:
        raise ValueError(f"Reviews refer to missing models: {sorted(unknown)}")
    for row in rows:
        apply_review(row,reviews["models"].get(row["model"]),root,evidence_sha256)
    counts = Counter(row["score"] for row in rows)
    return {"format":1, "objective":"Every world asset genuinely 3D, detailed and consistent; every model at least8/10.",
            "rubric":{"1":"Missing/fallback or no 3D evidence", "3":"Retained reference or unbound diagnostic", "4":"Procedural 3D, review pending",
                      "5":"Authored and bound 3D cells, visual review pending", "6":"Individually inspected; significant defects remain",
                      "7":"Mostly coherent; known defect or evidence gap remains", "8":"All quick-pass source/orbit/street/world/state/consistency checks pass",
                      "9":"High-fidelity individually verified", "10":"Exceptional fidelity/detail and all acceptance evidence"},
            "models":rows, "coverage_gaps":gaps, "runtime_scope":runtime_scope, "intentional_absences":intentional_absences, "score_counts":dict(sorted(counts.items())),
            "meets_objective":not gaps and bool(rows) and all(row["score"] >= 8 and row["status"] == "individually-reviewed" for row in rows if row["required_runtime_review"]),
            "note":"Screening scores are deliberately conservative, not claimed aesthetic judgements or final upstream-art approvals. Unknown and stale reviews cannot satisfy8/10."}


def write_ratings_csv(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="") as stream:
        writer = csv.writer(stream,lineterminator="\n")
        writer.writerow(("model","score/10","representation","review_status","notes"))
        for row in rows:
            writer.writerow((row["model"],row["score"],row["representation"],row["status"]," ".join(row["notes"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue",type=Path,required=True)
    parser.add_argument("--reviews",type=Path,default=ROOT/"assets/3d/quality_reviews.json")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--csv",type=Path)
    parser.add_argument("--inventory",type=Path,help="Original family/state/absence inventory generated from the exact reviewed compiled catalogue")
    parser.add_argument("--require-eight",action="store_true")
    args = parser.parse_args()
    report = audit(json.loads(args.catalogue.read_text()),json.loads(args.reviews.read_text()),scope=json.loads(args.inventory.read_text()) if args.inventory else None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    if args.csv:
        write_ratings_csv(args.csv,report["models"])
    print(json.dumps({"models":len(report["models"]),"scores":report["score_counts"],"coverage_gaps":len(report["coverage_gaps"]),"meets_objective":report["meets_objective"]}))
    if args.require_eight and not report["meets_objective"]:
        raise SystemExit("Quality pass incomplete: models below8/10 and/or missing world-asset coverage")


if __name__ == "__main__":
    main()

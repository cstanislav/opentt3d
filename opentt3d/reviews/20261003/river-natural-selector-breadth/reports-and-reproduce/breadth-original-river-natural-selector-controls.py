"""Actual higher-terrain river callbacks, independently checked against public NoAI saved-tile surveys."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys

sys.path.insert(0,"tools/assets")
sys.path.insert(0,"tools/opentt3d")
from live_river_selectors import selected_river_selectors
from fixture_rivers import validate_survey

root = Path("build-macos").resolve()
prefix = "breadth-original-river-natural-selector"
runs = root / (prefix+"-runs.json")
assert not runs.exists()
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
fixtures = [(climate,root / ("breadth-original-river-natural-survey-"+climate)) for climate in ("temperate","arctic","tropic","toyland")]
fixtures.append(("tropic",root / "breadth-original-river-natural-survey-tropic-seed161803"))
rows,selected,worlds,proofs = [],{},{},{}
for family,build in (("classic",root / "breadth-original-river-selector1831-frozen-build"),
                     ("opengfx",root / "breadth-original-river-selector-opengfx1831-frozen-build")):
    manifest = json.loads((build / "manifest.json").read_text())
    assert digest(build / "opentt3d") == manifest["binary_sha256"]
    assert digest(build / "baseset/opentt3d-voxels.json") == "6e5be58e30a55d36be9d1e40a118739fc687d3a84afa22ebf3217469350ca56d"
    selected[family],worlds[family] = {},[]
    for climate,fixture in fixtures:
        original = json.loads((fixture / "fixture.json").read_text())
        validate_survey(original,original["tiles"])
        save = fixture / original["save"]
        assert digest(save) == original["save_sha256"]
        label = climate+"-seed"+str(original["seed"])
        owners = {row["tile"]:row for row in original["tiles"]}
        outputs,pairs = {},{}
        for backend in ("vulkan","opengl"):
            for tracing in (False,True):
                output = root / (prefix+"-"+family+"-"+label+"-"+backend+("-on" if tracing else "-off"))
                assert not output.exists()
                command = ["python3","tools/opentt3d/smoke.py","--build-dir",str(build),"--output",str(output),"--background","--backend",backend,
                    "--savegame",str(save),"--ai-dir",str(fixture / "ai"),"--center","64","64","--zoom","5",
                    "--verify-world-atlas","--verify-tile-picking","--synchronous-save","--resolution","640","480","--timeout","600","--brief"]
                if family == "opengfx":
                    command.extend(["--graphics","OpenGFX"])
                result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="1" if tracing else "0",OPENTT3D_GL_RASTER_Y_DOWN="0"))
                row = {"family":family,"climate":climate,"seed":original["seed"],"backend":backend,"tracing":tracing,"output":str(output),
                    "exit_code":result.returncode,"command":command,"original_survey_save_sha256":original["save_sha256"],
                    "frozen_manifest_sha256":digest(build / "manifest.json"),"geometry_or_quality_approved":False}
                rows.append(row)
                runs.write_text(json.dumps(rows,indent=2)+"\n")
                assert result.returncode == 0,row
                assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
                subprocess.run([python,"tools/assets/compact_reviews.py",str(root),"--validation-manifest",str(runs),"--apply"],check=True)
                outputs[backend,tracing] = output
                directory = output / "renderer3d-reference"
                observed = directory / "river-selectors.json"
                assert observed.exists() == tracing
                if not tracing:
                    continue
                observations = json.loads(observed.read_text())["observations"]
                proofs[str(observed)] = digest(observed)
                for source in observations:
                    tile = owners[source["tile"]]
                    assert source["slope"] == tile["slope"] and source["source_height"] == tile["min_height_levels"]*8
                    assert source["tile_xy"] == [tile["x"],tile["y"]]
                    if not source["absent"]:
                        image = directory / source["source_image"]
                        source["source_image_sha256"] = digest(image)
                        proofs[str(image)] = source["source_image_sha256"]
                pairs[backend] = selected_river_selectors(observations,original,("temperate","arctic","tropic","toyland").index(climate))
                assert pairs[backend]["observed_tiles"] == original["river_tiles"],(family,label,backend,"Survey/rendered river tile sets differ")
            report = root / (prefix+"-world-"+family+"-"+label+"-"+backend+".json")
            subprocess.run([python,"tools/assets/compare_galleries.py",str(outputs[backend,False] / "screenshot/smoke.png"),
                str(outputs[backend,True] / "screenshot/smoke.png"),"--pixel-details","20","--output",str(report)],check=True)
            compared = json.loads(report.read_text())
            assert compared["images"] == 1 and not compared["differences"]
            worlds[family].append({"climate":climate,"seed":original["seed"],"backend":backend,"report":str(report),
                "report_sha256":digest(report),"changed_pixels":0,"masks":False,"tolerance":0})
        assert pairs["vulkan"] == pairs["opengl"],(family,label)
        selected[family][label] = pairs["vulkan"]
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"quiet_native_controls":len(rows),
    "public_read_only_surveys":len(fixtures),"selected_sources":selected,"strict_world_comparisons":worlds,"source_evidence_sha256":proofs,
    "ground_owner_states_exact_per_base_set":sum(len(row["ground_sources"]) for row in selected["classic"].values()),
    "bank_owner_states_exact_per_base_set":sum(len(row["edge_sources"]) for row in selected["classic"].values()),
    "strict_world_images":sum(len(row) for row in worlds.values()),"strict_world_changed_pixels":0,"approved_models":0,
    "scope":"Normally generated hill/many-river worlds retain five public read-only NoAI surveys, every surveyed tile rendered by original callbacks, exact original slope/anchor/height (eight source units per map level), selected source bytes and independent feature/input/output provenance across both backends and Classic/OpenGFX8.0. Only tracing-on/off world comparisons are exact; no cross-backend world equality is inferred. No authored object inflation, forced terrain/feature/selector/absence/RNG, duplicate callback, new geometry/binding or complete custom-family/relief/water ownership/animation/ships/performance/8+ approval. Entire catalogue goal remains open."}
(root / (prefix+"-verification.json")).write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({key:value for key,value in summary.items() if key not in ("selected_sources","strict_world_comparisons","source_evidence_sha256")}))

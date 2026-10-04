"""Freeze and test provisional locks in public saved worlds; never change releases."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from compile_voxels import compile_catalogue
from live_water import selected_lock_sources
from quality_audit import fingerprint

CLIMATES = ("temperate", "arctic", "tropic", "toyland")
ART = ROOT / "opentt3d/reviews/20261003/water-foam-palette-study/authored-source.json"
RESOURCES = ROOT / "build-macos/playable-release42-independent-extracted/OpenTT3D.app/Contents/Resources"
WALL = re.compile(r"live voxel lock wall (\d+) part (\d+) direction (\d+) face (\d+) climate (\d+) base (\d+) family (\d+) source (\d+) captured at (\d+),(\d+) origin ([^, ]+),([^, ]+),([^ ]+) opacity ([^ ]+) with independent original water ground")


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def fixture(climate):
    name = "temperate-natural-resources" if climate == "temperate" else climate + "-natural"
    path = ROOT / "build-macos" / ("breadth-original-lock-" + name + "-fixture")
    record = json.loads((path / "fixture.json").read_text())
    assert digest(path / "save/lock-fixture.sav") == record["save_sha256"]
    return path, record


def freeze(prefix):
    build = ROOT / "build-macos"
    original_path = RESOURCES / "baseset/opentt3d-voxels.json"
    original = json.loads(original_path.read_text())
    study = compile_catalogue(json.loads(ART.read_text()))
    assert len(original["models"]) == 1831 and len(study["models"]) == 48 and study["bindings"] == {}
    merged = json.loads(original_path.read_text())
    offset = len(merged["materials"])
    merged["materials"].extend(study["materials"])
    for name, model in study["models"].items():
        assert name not in merged["models"]
        merged["models"][name] = {**model, "runs": [run[:4] + [run[4]+offset] for run in model["runs"]]}
    assert all(fingerprint(model, original["materials"]) == fingerprint(merged["models"][name], merged["materials"])
               for name, model in original["models"].items())
    bindings = {}
    for elevation, suffix in enumerate(("sea", "elevated")):
        for part, label in enumerate(("middle", "lower", "upper")):
            for direction, label_direction in enumerate(("se", "ne", "sw", "nw")):
                for face, label_face in enumerate(("rear", "front")):
                    owner = elevation*24 + part*8 + face*4 + direction
                    name = f"lock_study_{label}_{label_direction}_{label_face}_{suffix}"
                    assert name in study["models"]
                    bindings[str(owner)] = {str(climate): name for climate in range(4)}
    merged["bindings"]["lock_walls"] = bindings
    for scope in ("canonical", "complete", "missing-owner"):
        target = build / f"{prefix}-{scope}-frozen-build"
        if target.exists():
            raise ValueError("Retain existing freeze and use a new prefix: " + str(target))
        (target / "baseset").mkdir(parents=True)
        if scope == "canonical":
            shutil.copy2(original_path, target / "baseset/opentt3d-voxels.json")
        else:
            payload = json.loads(json.dumps(merged))
            if scope == "missing-owner":
                payload["bindings"]["lock_walls"].pop("47")
            (target / "baseset/opentt3d-voxels.json").write_text(json.dumps(payload, separators=(",", ":")) + "\n")
        for path in (RESOURCES / "baseset").iterdir():
            if path.name != "opentt3d-voxels.json":
                (target / "baseset" / path.name).symlink_to(path, target_is_directory=path.is_dir())
        for name in ("ai", "game", "lang"):
            (target / name).symlink_to(RESOURCES / name, target_is_directory=True)
        alternate = build / "baseset/opengfx-8.0.tar"
        assert digest(alternate) == "9389bcb0807058c80bd95121e978f05d9ef86b4b1bc3ac2da8da8bb02456043c"
        (target / "baseset/opengfx-8.0.tar").symlink_to(alternate)
        shutil.copy2(build / "opentt3d", target / "opentt3d")
        shutil.copy2(ART, target / "authored-source.json")
        shutil.copy2(ROOT / "tools/assets/compile_voxels.py", target / "compiler-snapshot.py")
        manifest = {"frozen_utc": datetime.now(timezone.utc).isoformat(), "scope": scope,
                    "models": 1831 if scope == "canonical" else 1879,
                    "diagnostic_bound_owners": 48 if scope == "complete" else 47 if scope == "missing-owner" else 0,
                    "sha256": {name: digest(target / name) for name in ("opentt3d", "baseset/opentt3d-voxels.json", "authored-source.json", "compiler-snapshot.py")},
                    "runtime_sources": {str(path.relative_to(ROOT)): digest(path) for path in sorted((ROOT / "src/renderer3d").rglob("*")) if path.is_file()},
                    "study_fingerprints": {name: fingerprint(model, study["materials"]) for name, model in study["models"].items()},
                    "prior_1831_models_and_bindings_exact": True, "exact_tag_binary": False,
                    "released_catalogue_sha256": digest(original_path), "geometry_approvals": 0}
        manifest["runtime_sources"]["src/water_cmd.cpp"] = digest(ROOT / "src/water_cmd.cpp")
        manifest["alternate_archive_sha256"] = digest(alternate)
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def verify_frozen(path):
    manifest = json.loads((path / "manifest.json").read_text())
    assert all(digest(path / name) == expected for name, expected in manifest["sha256"].items())
    assert digest(path / "baseset/opengfx-8.0.tar") == manifest["alternate_archive_sha256"]
    return manifest


def run(prefix, phase):
    build = ROOT / "build-macos"
    complete = build / f"{prefix}-complete-frozen-build"
    canonical = build / f"{prefix}-canonical-frozen-build"
    missing = build / f"{prefix}-missing-owner-frozen-build"
    frozen = {path: verify_frozen(path) for path in (complete, canonical, missing)}
    old = build / "breadth-original-river-selector1831-frozen-build"
    old_alternate = build / "breadth-original-river-selector-opengfx1831-frozen-build"
    rows = []
    plan = []
    if phase == "pilot":
        path, sites = fixture("temperate")
        site = sites["locks"][0]
        for backend in ("vulkan", "opengl"):
            for scope, executable, graphics in (("complete", complete, None), ("canonical", canonical, None),
                                                ("missing-owner", missing, None), ("prior-canonical", old, None),
                                                ("alternate", complete, "OpenGFX"), ("prior-alternate", old_alternate, "OpenGFX")):
                plan.append(("temperate", path, sites, site, backend, scope, executable, graphics))
    else:
        for climate in CLIMATES:
            path, sites = fixture(climate)
            for backend in ("vulkan", "opengl"):
                for site in sites["locks"]:
                    plan.append((climate, path, sites, site, backend, "complete", complete, None))
    run_manifest = build / f"{prefix}-{phase}-runs.json"
    if run_manifest.exists():
        raise ValueError("Retain existing runs and use a new prefix or phase")
    for climate, path, sites, site, backend, scope, executable, graphics in plan:
        output = build / f"{prefix}-{phase}-{scope}-{climate}-{site['elevation']}-{site['direction']}-{backend}"
        command = [sys.executable, "tools/opentt3d/smoke.py", "--build-dir", str(executable), "--output", str(output),
                   "--background", "--backend", backend, "--savegame", str(path / "save/lock-fixture.sav"),
                   "--ai-dir", str(path / "ai"), "--center", str(site["x"]), str(site["y"]), "--verify-world-atlas",
                   "--verify-tile-picking", "--synchronous-save", "--zoom", "0", "--resolution", "640", "480", "--timeout", "300", "--brief"]
        if graphics:
            command += ["--graphics", graphics]
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, OPENTT3D_EXPORT_WATER_SOURCES="1"))
        record = {"output": str(output), "exit_code": result.returncode, "command": command, "scope": scope,
                  "climate": climate, "backend": backend, "elevation": site["elevation"], "direction": site["direction"],
                  "binary_sha256": digest(executable / "opentt3d"), "catalogue_sha256": digest(executable / "baseset/opentt3d-voxels.json")}
        rows.append(record)
        run_manifest.write_text(json.dumps(rows, indent=2) + "\n")
        if result.returncode:
            raise SystemExit(result.returncode)
        assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
        observed = []
        for match in WALL.finditer((output / "run.log").read_text()):
            values = match.groups()
            observed.append({"owner": int(values[0]), "part": int(values[1]), "direction": int(values[2]),
                             "face": int(values[3]), "climate": int(values[4]), "base": int(values[5]), "family_base": int(values[6]), "source": int(values[7]),
                             "tile_xy": [int(values[8]), int(values[9])], "origin": list(map(float, values[10:13])), "opacity": float(values[13])})
        record["emitted_walls"] = observed
        source = json.loads((output / "renderer3d-reference/water-live.json").read_text())
        assert {row["base_set"] for row in source["observations"]} == {graphics or "OpenGFX2 Classic"}, "The requested archive must actually be selected, not silently fall back"
        if scope == "complete":
            positions = [[site["x"], site["y"]], [site["lower"] % sites["map_width"], site["lower"] // sites["map_width"]],
                         [site["upper"] % sites["map_width"], site["upper"] // sites["map_width"]]]
            actual = [wall for wall in observed if wall["tile_xy"] in positions]
            assert len(actual) == 6, "Both actual original walls must be emitted on all three focused lock tiles"
            saved_parts = {}
            for saved in sites["locks"]:
                for part, tile in enumerate((saved["tile"], saved["lower"], saved["upper"])):
                    saved_parts[tile] = (part, saved)
            for wall in observed:
                part, saved = saved_parts[wall["tile_xy"][0] + wall["tile_xy"][1]*sites["map_width"]]
                assert wall["part"] == part and wall["direction"] == saved["direction"]
                ordinal = saved["elevation"]*24 + part*8 + wall["face"]*4 + (1, 0, 2, 3)[saved["direction"]]
                assert wall["owner"] == ordinal and wall["climate"] == CLIMATES.index(climate)
                assert wall["opacity"] == 1
                along_x = saved["direction"] in (0, 2)
                source_height = saved["height"]*8 + (8 if part == 2 else 0)
                assert wall["origin"] == [wall["tile_xy"][0]*16 + (0 if along_x else wall["face"]*15),
                                          wall["tile_xy"][1]*16 + (wall["face"]*15 if along_x else 0), source_height*2]
        else:
            assert not observed, "An incomplete/alternate/canonical family must not hide any original wall"
        run_manifest.write_text(json.dumps(rows, indent=2) + "\n")
    for path in frozen:
        assert verify_frozen(path) == frozen[path]
    summary = {"audited_utc": datetime.now(timezone.utc).isoformat(), "phase": phase, "quiet_native_controls": len(rows),
               "observed_owner_climates": sorted({(wall["owner"], wall["climate"]) for row in rows for wall in row["emitted_walls"]}),
               "geometry_approvals": 0, "release_bindings_changed": False, "run_manifest": str(run_manifest)}
    if phase == "matrix":
        sources = {}
        for climate in CLIMATES:
            path, sites = fixture(climate)
            for backend in ("vulkan", "opengl"):
                observations = []
                for row in rows:
                    if row["climate"] != climate or row["backend"] != backend:
                        continue
                    output = Path(row["output"])
                    source = json.loads((output / "renderer3d-reference/water-live.json").read_text())
                    for observation in source["observations"]:
                        observation["source_image_sha256"] = digest(output / "renderer3d-reference" / observation["source_image"])
                    observations.extend(source["observations"])
                sources[climate, backend] = selected_lock_sources(observations, sites, CLIMATES.index(climate))
            assert sources[climate, "vulkan"] == sources[climate, "opengl"]
        prior = json.loads((ROOT / "opentt3d/reviews/20261003/water-live-selectors/breadth-original-lock-live-source-verification.json").read_text())["selected_sources"]
        assert {climate: sources[climate, "vulkan"] for climate in CLIMATES} == prior
        assert len(summary["observed_owner_climates"]) == 192
        summary["all192_original_wall_and96_independent_water_source_states_exact"] = True
    (build / f"{prefix}-{phase}-verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--phase", choices=("freeze", "pilot", "matrix"), required=True)
    args = parser.parse_args()
    if not args.prefix.startswith("breadth-original-lock-") or not all(char.isalnum() or char == "-" for char in args.prefix):
        parser.error("Use a fresh breadth-original-lock-* diagnostic prefix")
    if args.phase == "freeze":
        freeze(args.prefix)
    else:
        run(args.prefix, args.phase)


if __name__ == "__main__":
    main()

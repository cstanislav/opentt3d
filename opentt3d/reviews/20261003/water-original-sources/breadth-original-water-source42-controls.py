"""Export original static lock/water sources from the exact downloaded .42 runtime."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, sys

root = Path("build-macos").resolve()
prefix = "breadth-original-water-source42"
app = root / "playable-release42-independent-extracted/OpenTT3D.app"
resources = app / "Contents/Resources"
executable = app / "Contents/MacOS/opentt3d"
audit = json.loads((root / "playable-release42-independent-runtime-audit.json").read_text())
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
assert digest(executable) == audit["binary_sha256"]
assert digest(resources / "baseset/opentt3d-voxels.json") == audit["catalogue_sha256"]
sys.path.insert(0, "tools/assets")
from original_water import catalogue, validate_default_export
inventory = catalogue()
runs = []
comparisons = []
for climate in ("temperate", "arctic", "tropic", "toyland"):
    fixture = root / f"breadth-original-object-command-{climate}-owned-land-fixture"
    site = json.loads((fixture / "fixture.json").read_text())
    sources = {}
    for backend in ("vulkan", "opengl"):
        output = root / f"{prefix}-{climate}-{backend}"
        command = ["python3", str(root / "playable-release42-smoke-cow.py"), "--build-dir", str(resources), "--executable", str(executable),
            "--output", str(output), "--background", "--backend", backend, "--savegame", str(fixture / "save/object-fixture.sav"),
            "--ai-dir", str(fixture / "ai"), "--reference-object", "4", "--reference-object-tile", str(site["hq_x"]), str(site["hq_y"]),
            "--export-terrain", "--verify-world-atlas", "--verify-tile-picking", "--synchronous-save", "--zoom", "0",
            "--resolution", "640", "480", "--timeout", "300", "--brief"]
        result = subprocess.run(command)
        runs.append({"climate": climate, "backend": backend, "output": str(output), "command": command, "exit_code": result.returncode})
        (root / (prefix + "-runs.json")).write_text(json.dumps(runs, indent=2) + "\n")
        if result.returncode:
            raise SystemExit(result.returncode)
        assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
        references = output / "renderer3d-reference"
        exported = json.loads((references / "terrain-details.json").read_text())
        assert validate_default_export(exported, inventory)["source_entries_verified"] == 52
        sources[backend] = {row["image"]: {"metadata": row, "sha256": digest(references / row["image"])}
                            for row in exported if row["category"] in ("canal-lock", "water-slope")}
    assert len(sources["vulkan"]) == 52 and sources["vulkan"] == sources["opengl"], climate
    comparisons.append({"climate": climate, "source_images_exact": 52, "metadata_and_pam_bytes_exact": True,
                        "source_sha256": sources["vulkan"]})
assert digest(executable) == audit["binary_sha256"] and digest(resources / "baseset/opentt3d-voxels.json") == audit["catalogue_sha256"]
summary = {"audited_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "tag": audit["tag"], "commit": audit["commit"],
    "binary_sha256": audit["binary_sha256"], "catalogue_sha256": audit["catalogue_sha256"], "runs": runs,
    "source_inventory": inventory, "comparisons": comparisons, "source_equalities": 208, "geometry_approvals": 0,
    "scope": "Eight quiet native export/atlas/picking/synchronous-save controls use the unchanged exact-tag downloaded app/resources. All48 default lock wall sources and four default water slopes retain original metadata and exact backend bytes per climate. Static exports do not resolve active Classic/NewGRF lock/river features or prove any lock model/world/ship clearance, river bank geometry, performance or quality. No game selector, commands, terrain, time, ratings, RNG, renderer or artwork changed."}
output = root / (prefix + "-verification.json")
assert not output.exists()
output.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"runs": len(runs), "source_equalities": 208, "geometry_approvals": 0}))

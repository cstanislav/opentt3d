"""Exercise original company-building visibility without modifying ground/simulation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def observations(path, role):
    data = json.loads((path / "renderer3d-reference/water-live.json").read_text())
    rows = []
    for entry in data["observations"]:
        if entry["kind"] != "lock" or entry["role"] != role:
            continue
        row = dict(entry)
        row["source_image_sha256"] = digest(path / "renderer3d-reference" / row["source_image"])
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--freeze-prefix", default="breadth-original-lock-world-support-corrected")
    args = parser.parse_args()
    if not args.prefix.startswith("breadth-original-lock-") or not all(c.isalnum() or c == "-" for c in args.prefix):
        parser.error("Use a fresh diagnostic prefix")
    build = ROOT / "build-macos"
    freezes = {scope: build / f"{args.freeze_prefix}-{scope}-frozen-build" for scope in ("complete", "canonical", "missing-owner")}
    freezes.update({"prior-canonical": build / "breadth-original-river-selector1831-frozen-build",
                    "alternate": freezes["complete"], "prior-alternate": build / "breadth-original-river-selector-opengfx1831-frozen-build"})
    fixture = build / "breadth-original-lock-temperate-natural-resources-fixture"
    sites = json.loads((fixture / "fixture.json").read_text())
    assert digest(fixture / "save/lock-fixture.sav") == sites["save_sha256"]
    site = sites["locks"][0]
    manifest_path = build / f"{args.prefix}-runs.json"
    if manifest_path.exists():
        raise ValueError("Retain existing controls and choose a fresh prefix")
    records = []
    for backend in ("vulkan", "opengl"):
        for scope in ("complete", "canonical", "missing-owner", "prior-canonical", "alternate", "prior-alternate"):
            for visibility in (("transparent", "invisible") if scope in ("complete", "canonical", "prior-canonical") else ("transparent",)):
                frozen = freezes[scope]
                output = build / f"{args.prefix}-{scope}-{visibility}-{backend}"
                graphics = "OpenGFX" if "alternate" in scope else "OpenGFX2 Classic"
                command = [sys.executable, "tools/opentt3d/smoke.py", "--build-dir", str(frozen), "--output", str(output), "--background",
                           "--backend", backend, "--savegame", str(fixture / "save/lock-fixture.sav"), "--ai-dir", str(fixture / "ai"),
                           "--center", str(site["x"]), str(site["y"]), "--building-visibility", visibility,
                           "--graphics", graphics, "--verify-world-atlas", "--verify-tile-picking", "--synchronous-save", "--zoom", "0",
                           "--resolution", "640", "480", "--timeout", "300", "--brief"]
                result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, OPENTT3D_EXPORT_WATER_SOURCES="1"))
                record = {"output": str(output), "scope": scope, "backend": backend, "visibility": visibility,
                          "command": command, "exit_code": result.returncode, "binary_sha256": digest(frozen / "opentt3d"),
                          "catalogue_sha256": digest(frozen / "baseset/opentt3d-voxels.json")}
                records.append(record)
                manifest_path.write_text(json.dumps(records, indent=2) + "\n")
                if result.returncode:
                    raise SystemExit(result.returncode)
                data = json.loads((output / "renderer3d-reference/water-live.json").read_text())
                assert {entry["base_set"] for entry in data["observations"]} == {graphics}
                assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
                baseline_scope = "alternate" if "alternate" in scope else "canonical"
                baseline = build / f"{args.freeze_prefix}-pilot-{baseline_scope}-temperate-0-0-{backend}"
                assert observations(output, "ground") == observations(baseline, "ground"), "Walls must not hide, recolour or replace independent original water"
                walls = observations(output, "body")
                emitted = [line for line in (output / "run.log").read_text().splitlines() if "live voxel lock wall " in line]
                if visibility == "invisible":
                    assert not walls and not emitted, "Original hidden building walls must stay absent"
                else:
                    assert walls and all(wall["transparent"] for wall in walls)
                    originals = observations(baseline, "body")
                    for wall in walls:
                        wall["transparent"] = False
                    assert walls == originals, "Transparent wall callbacks, ordering, source bytes and registration must stay original"
                    if scope == "complete":
                        assert emitted and all("opacity 0.379999995 " in line for line in emitted), "Both voxel walls need original transparency"
                    else:
                        assert not emitted, "Incomplete/alternate families must retain original transparent walls"
                record["independent_water_exact"] = True
                record["original_wall_visibility_exact"] = True
                manifest_path.write_text(json.dumps(records, indent=2) + "\n")
    directory = HERE / "visibility-strict-comparisons"
    directory.mkdir()
    groups = {(row["scope"], row["visibility"], row["backend"]): row for row in records}
    comparisons = []
    for backend in ("vulkan", "opengl"):
        for left, right, mode in (("prior-canonical", "canonical", "transparent"), ("prior-canonical", "canonical", "invisible"),
                                  ("canonical", "missing-owner", "transparent"), ("canonical", "complete", "invisible"),
                                  ("prior-alternate", "alternate", "transparent")):
            label = f"{left}-to-{right}-{mode}-{backend}"
            report = directory / f"{label}.json"
            with (directory / f"{label}.log").open("x") as log:
                result = subprocess.run([sys.executable, "tools/assets/compare_galleries.py",
                                         str(Path(groups[left, mode, backend]["output"]) / "screenshot/smoke.png"),
                                         str(Path(groups[right, mode, backend]["output"]) / "screenshot/smoke.png"),
                                         "--output", str(report), "--pixel-details", "32"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            assert result.returncode in (0, 1)
            comparisons.append({"label": label, "exit_code": result.returncode, "report": str(report.relative_to(ROOT))})
    summary = {"audited_utc": datetime.now(timezone.utc).isoformat(), "quiet_native_controls": len(records),
               "independent_water_and_original_visibility_exact": True, "preservation_comparisons": comparisons,
               "strict_preservation_passed": all(row["exit_code"] == 0 for row in comparisons), "geometry_approvals": 0,
               "does_not_establish": ["all-climate visibility", "independent animated phases", "ship clearance", "lock-specific GPU pick samples", "strict paired-renderer acceptance"]}
    (build / f"{args.prefix}-verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

"""Compare complete native worlds exactly; retain failures without masks/tolerance."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--phase", choices=("pilot", "matrix"), required=True)
    args = parser.parse_args()
    rows = json.loads((ROOT / "build-macos" / f"{args.prefix}-{args.phase}-runs.json").read_text())
    assert all(row["exit_code"] == 0 for row in rows)
    directory = HERE / "strict-comparisons"
    directory.mkdir(exist_ok=True)
    pairs = []
    def shot(row):
        return Path(row["output"]) / "screenshot/smoke.png"
    if args.phase == "pilot":
        assert len(rows) == 12
        scopes = {(row["scope"], row["backend"]): row for row in rows}
        for backend in ("vulkan", "opengl"):
            for old, new in (("prior-canonical", "canonical"), ("canonical", "missing-owner"), ("prior-alternate", "alternate")):
                pairs.append((f"preservation-{new}-{backend}", shot(scopes[old, backend]), shot(scopes[new, backend]), "preservation"))
        for scope in ("complete", "canonical", "alternate"):
            pairs.append((f"paired-{scope}", shot(scopes[scope, "vulkan"]), shot(scopes[scope, "opengl"]), "paired-world"))
    else:
        assert len(rows) == 64
        grouped = {(row["climate"], row["elevation"], row["direction"], row["backend"]): row for row in rows}
        for climate in ("temperate", "arctic", "tropic", "toyland"):
            for elevation in range(2):
                for direction in range(4):
                    pairs.append((f"{climate}-{elevation}-{direction}", shot(grouped[climate, elevation, direction, "vulkan"]),
                                  shot(grouped[climate, elevation, direction, "opengl"]), "paired-world"))
    reports = []
    for label, left, right, scope in pairs:
        report = directory / f"{args.phase}-{label}.json"
        with (directory / f"{args.phase}-{label}.log").open("x") as log:
            result = subprocess.run([sys.executable, "tools/assets/compare_galleries.py", str(left), str(right),
                                     "--output", str(report), "--pixel-details", "32"], cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode in (0, 1) and report.is_file()
        data = json.loads(report.read_text())
        assert data["images"] == 1
        reports.append({"label": label, "scope": scope, "exit_code": result.returncode, "report": str(report.relative_to(ROOT)),
                        "different_images": len(data["differences"]),
                        "different_pixels": sum(row.get("changed_pixels", 0) for row in data["differences"])})
    summary = {"audited_utc": datetime.now(timezone.utc).isoformat(), "phase": args.phase, "comparisons": reports,
               "geometry_approvals": 0, "masks_or_tolerance": False,
               "exact_preservation_controls": sum(row["scope"] == "preservation" and row["exit_code"] == 0 for row in reports),
               "different_images": sum(row["different_images"] for row in reports),
               "different_pixels": sum(row["different_pixels"] for row in reports)}
    (HERE / f"{args.phase}-strict-verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

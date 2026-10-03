"""Compare observer-default-off against the exact downloaded app using identical capture paths."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess

root = Path("build-macos").resolve()
prefix = "breadth-original-water-observer-preservation"
app = root / "playable-release42-independent-extracted/OpenTT3D.app"
frozen = root / "breadth-original-water-observer1831-frozen-build"
manifest = json.loads((frozen / "manifest.json").read_text())
digest = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
wrapper = frozen / "external-runner-data-layout"
assert not wrapper.exists()
(wrapper / "Contents/MacOS").mkdir(parents=True)
(wrapper / "Contents/MacOS/opentt3d").symlink_to(frozen / "opentt3d")
(wrapper / "Contents/Resources").symlink_to(app / "Contents/Resources", target_is_directory=True)
executables = {"exact-tag":app / "Contents/MacOS/opentt3d", "observer-off":wrapper / "Contents/MacOS/opentt3d"}
assert digest(executables["exact-tag"]) == "9947915f13e84c7308f86a5af41bf2da71fea1fda96e9421a48036074111be22"
assert digest(executables["observer-off"]) == manifest["binary_sha256"]
rows, comparisons = [], []
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
for climate in ("temperate","arctic","tropic","toyland"):
    fixture = root / ("breadth-original-lock-temperate-natural-resources-fixture" if climate == "temperate" else f"breadth-original-lock-{climate}-natural-fixture")
    site = json.loads((fixture / "fixture.json").read_text())["locks"][0]
    for backend in ("vulkan","opengl"):
        outputs = {}
        for mode, executable in executables.items():
            output = root / f"{prefix}-{climate}-{backend}-{mode}"
            command = ["python3",str(root / "playable-release42-smoke-cow.py"),"--build-dir",str(app / "Contents/Resources"),
                "--executable",str(executable),"--output",str(output),"--background","--backend",backend,
                "--savegame",str(fixture / "save/lock-fixture.sav"),"--ai-dir",str(fixture / "ai"),"--center",str(site["x"]),str(site["y"]),
                "--verify-world-atlas","--verify-tile-picking","--synchronous-save","--zoom","0","--resolution","640","480","--timeout","300","--brief"]
            result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
            rows.append({"climate":climate,"backend":backend,"mode":mode,"output":str(output),"exit_code":result.returncode,
                         "command":command,"binary_sha256":digest(executable)})
            (root / (prefix+"-runs.json")).write_text(json.dumps(rows,indent=2)+"\n")
            if result.returncode:
                raise SystemExit(result.returncode)
            assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
            assert not (output / "renderer3d-reference/water-live.json").exists(), "Default-off must not export/resolve/retain observations"
            outputs[mode] = output
        report = root / f"{prefix}-{climate}-{backend}-strict.json"
        result = subprocess.run([python,"tools/assets/compare_galleries.py",str(outputs["exact-tag"] / "screenshot/smoke.png"),
            str(outputs["observer-off"] / "screenshot/smoke.png"),"--output",str(report)],stdout=subprocess.DEVNULL)
        assert result.returncode in (0,1) and report.is_file()
        comparison = json.loads(report.read_text())
        comparisons.append({"climate":climate,"backend":backend,"exit_code":result.returncode,"different_images":len(comparison["differences"]),
            "different_pixels":sum(row.get("changed_pixels",0) for row in comparison["differences"]),"report":str(report),"report_sha256":digest(report)})
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"runs":rows,"comparisons":comparisons,
    "exact_tag_binary_sha256":digest(executables["exact-tag"]),"observer_binary_sha256":manifest["binary_sha256"],
    "catalogue_sha256":manifest["loaded_catalogue_sha256"],"models":1831,"all_worlds_strict_exact":all(row["exit_code"] == 0 for row in comparisons),
    "scope":"Sixteen quiet native atlas/picking/synchronous-save controls compare the unchanged downloaded exact-tag app against the local observer with diagnostics disabled, using identical external-executable/resource/capture paths. Failure remains failure; no tolerance or UI mask. This only validates observational default-off world preservation in four public natural-lock saves, not new geometry, palette phases, performance, source provenance of the mixed local build or release approval."}
output = root / (prefix+"-verification.json")
assert not output.exists()
output.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"native_controls":len(rows),"worlds":len(comparisons),"all_worlds_strict_exact":summary["all_worlds_strict_exact"]}))
if not summary["all_worlds_strict_exact"]:
    raise SystemExit(1)

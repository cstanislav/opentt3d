"""Four legal normally generated maps, with read-only NoAI tile surveys and acknowledged saves."""
from pathlib import Path
import hashlib, json, subprocess

root = Path("build-macos").resolve()
build = root / "breadth-original-river-selector1831-frozen-build"
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
manifest = json.loads((build / "manifest.json").read_text())
assert digest(build / "opentt3d") == manifest["binary_sha256"]
runs = root / "breadth-original-river-natural-survey-runs.json"
assert not runs.exists()
rows = []
for climate in ("temperate","arctic","tropic","toyland"):
    output = root / ("breadth-original-river-natural-survey-"+climate)
    assert not output.exists()
    command = ["python3","tools/opentt3d/fixture_rivers.py","--build-dir",str(build),"--output",str(output),
        "--climate",climate,"--seed","271828","--timeout","300"]
    result = subprocess.run(command)
    rows.append({"climate":climate,"output":str(output),"command":command,"exit_code":result.returncode})
    runs.write_text(json.dumps(rows,indent=2)+"\n")
    assert result.returncode == 0,rows[-1]
    survey = json.loads((output / "fixture.json").read_text())
    assert digest(output / survey["save"]) == survey["save_sha256"]
    assert survey["read_only_tile_queries"] and not survey["geometry_or_quality_approved"]
print(json.dumps({"surveys":len(rows),"approved_models":0,"scope":"Original normal terrain_type2/many-rivers map generation using one unchanged seed per climate; public read-only NoAI queries plus acknowledged ordinary saves. No constructed/forced river, selector, feature, height, bank absence or simulation RNG."}))

"""Compile unbound wall studies and inspect them without changing any runtime bindings."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys

sys.path.insert(0,"tools/assets")
from compile_voxels import compile_catalogue
from quality_audit import fingerprint

root = Path("build-macos").resolve()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--prefix",default="breadth-original-lock-authored-study")
parser.add_argument("--source",type=Path,default=root / "breadth-original-lock-authored-study.json")
parser.add_argument("--require-open-lamp",action="store_true")
parser.add_argument("--require-front-profile",action="store_true")
args = parser.parse_args()
prefix = args.prefix
assert re.fullmatch(r"breadth-original-lock-[a-z0-9-]+",prefix)
out = root / (prefix+"-frozen-build")
assert not out.exists()
out.mkdir()
source_path = args.source.resolve()
source = json.loads(source_path.read_text())
study = compile_catalogue(source)
assert len(study["models"]) == 48 and study["bindings"] == {}
parts, directions, faces, elevations = ("middle","lower","upper"),("ne","se","sw","nw"),("rear","front"),("sea","elevated")
expected = {f"lock_study_{part}_{direction}_{face}_{elevation}" for part in parts for direction in directions for face in faces for elevation in elevations}
assert study["models"].keys() == expected
cells = lambda name: {(x+i,y,z):study["materials"][material-1] for x,y,z,length,material in study["models"][name]["runs"] for i in range(length)}
structures = []
for name, model in study["models"].items():
    occupied = cells(name)
    axis = 0 if "_ne_" in name or "_sw_" in name else 1
    assert model["size"] == ([72,12,96] if axis == 0 else [12,72,96]) and model["cell_size"] == [0.25]*3
    source_colours = {value for colours in occupied.values() for value in colours}
    lower_sea = "_lower_" in name and name.endswith("_sea")
    assert bool(source_colours & {65,66,67}) == lower_sea
    assert (252 in source_colours) == lower_sea
    if lower_sea and args.require_open_lamp:
        longitudinal = 68 if "_ne_" in name or "_nw_" in name else 4
        glass, opening = [longitudinal,2,78],[longitudinal,1,78]
        if axis == 1:
            glass[0],glass[1] = glass[1],glass[0]
            opening[0],opening[1] = opening[1],opening[0]
        assert tuple(opening) not in occupied and set(occupied[tuple(glass)]) <= {65,66,67}
    high = max(z for x,y,z in occupied)*0.25+model["origin"][2]+0.25
    assert high == (21 if lower_sea else 5 if "_upper_" in name else 13)
    assert 1 <= min(cell[axis] for cell in occupied) <= 4 and max(cell[axis] for cell in occupied) <= 70
    # A physical retaining wall, recessed buttresses, platform and open rail;
    # source sorting boxes are not substituted for the inspected artwork size.
    assert len({cell[1-axis] for cell in occupied}) >= 10
    rail_base = 9 if "_upper_" in name else 41
    front = "_front_" in name and args.require_front_profile
    rail_y = 6 if front else 2
    open_cell = [7,rail_y,rail_base+8]
    if axis == 1:
        open_cell[0],open_cell[1] = open_cell[1],open_cell[0]
    assert tuple(open_cell) not in occupied
    if front:
        samples = [[7,2,rail_base-1],[7,6,rail_base-1],[4,rail_y,rail_base+8],[7,rail_y,rail_base+10]]
        if axis == 1:
            samples = [[y,x,z] for x,y,z in samples]
        assert tuple(samples[0]) not in occupied
        assert all(tuple(sample) in occupied for sample in samples[1:])
        outward = 1 if axis == 1 else 3
        assert max(paint[outward] for cell,paint in occupied.items() if cell[1-axis] == 11 and cell[2] < rail_base-4) <= 5
    if "_middle_" in name:
        for cell in occupied:
            longitudinal = (cell[axis]-4)*0.25
            floor = 8-longitudinal/2 if "_ne_" in name or "_nw_" in name else longitudinal/2
            assert cell[2]*0.25+model["origin"][2] >= floor-0.25
    structures.append({"model":name,"fingerprint":fingerprint(model,study["materials"]),"occupied":len(occupied),
        "height":high,"lamp_and_foam":lower_sea,"structural_screen_passed":True,"approved":False})

if args.require_front_profile:
    lamp_prior = json.loads((root / "breadth-original-lock-open-lamp-frozen-build/baseset/opentt3d-voxels.json").read_text())
    for name,model in study["models"].items():
        prior_model = lamp_prior["models"][name]
        assert all(model[key] == prior_model[key] for key in ("origin","size","cell_size"))
        same = fingerprint(model,study["materials"]) == fingerprint(prior_model,lamp_prior["materials"])
        assert same == ("_rear_" in name), name

resources = root / "playable-release42-independent-extracted/OpenTT3D.app/Contents/Resources"
prior = json.loads((resources / "baseset/opentt3d-voxels.json").read_text())
merged = json.loads((resources / "baseset/opentt3d-voxels.json").read_text())
assert len(prior["models"]) == 1831 and not (prior["models"].keys() & study["models"].keys())
offset = len(merged["materials"])
merged["materials"].extend(study["materials"])
assert len(merged["materials"]) <= 65535
for name, model in study["models"].items():
    for run in model["runs"]:
        run[4] += offset
    merged["models"][name] = model
assert len(merged["models"]) == 1879 and prior["bindings"] == merged["bindings"]
assert all(fingerprint(model,prior["materials"]) == fingerprint(merged["models"][name],merged["materials"])
           for name, model in prior["models"].items())
assert all(fingerprint(merged["models"][row["model"]],merged["materials"]) == row["fingerprint"] for row in structures)
(out / "baseset").mkdir()
for path in (resources / "baseset").iterdir():
    if path.name != "opentt3d-voxels.json":
        (out / "baseset" / path.name).symlink_to(path,target_is_directory=path.is_dir())
(out / "baseset/opentt3d-voxels.json").write_text(json.dumps(merged,separators=(",",":"))+"\n")
for name in ("lang","ai","game"):
    (out / name).symlink_to(resources / name,target_is_directory=True)
shutil.copy2(root / "breadth-original-water-observer1831-frozen-build/opentt3d",out / "opentt3d")
shutil.copy2(source_path,out / "authored-source.json")
shutil.copy2("tools/assets/compile_voxels.py",out / "compiler-snapshot.py")
digest = lambda path: hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
manifest = {"frozen_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"models":1879,"unbound_lock_studies":48,
    "prior_1831_models_and_bindings_exact":True,"no_experimental_hq_models":True,
    "binary_sha256":digest(out / "opentt3d"),"catalogue_sha256":digest(out / "baseset/opentt3d-voxels.json"),
    "source_sha256":digest(out / "authored-source.json"),"compiler_sha256":digest(out / "compiler-snapshot.py"),
    "structural_models":structures,"geometry_approvals":0,"exact_tag_binary":False,
    "scope":"Hand-authored unbound48-model lock studies, with no runtime binding/capture/geometry/simulation changes, added to the unchanged released1831 models. Local diagnostic observer binary and experimental compiler are explicitly not an exact-tag app or accepted runtime asset increment. Original wall sources inform manual dimensions/details; no geometry is inferred from image pixels or sorting extents. World terrain grade, ships, original ownership/fidelity and every acceptance check remain unproved."}
(out / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
rows = []
fixture = root / "breadth-original-lock-temperate-natural-resources-fixture"
for backend in ("vulkan","opengl"):
    output = root / f"{prefix}-{backend}"
    command = ["python3","tools/opentt3d/smoke.py","--build-dir",str(out),"--output",str(output),"--background","--backend",backend,
        "--savegame",str(fixture / "save/lock-fixture.sav"),"--ai-dir",str(fixture / "ai"),"--center","101","4",
        "--gallery-voxel-prefix","lock_study_","--gallery-voxel-overview","--verify-world-atlas","--verify-tile-picking",
        "--synchronous-save","--resolution","640","480","--timeout","600","--brief"]
    result = subprocess.run(command,env=dict(os.environ,OPENTT3D_EXPORT_WATER_SOURCES="0"))
    rows.append({"backend":backend,"output":str(output),"exit_code":result.returncode,"command":command})
    (root / (prefix+"-runs.json")).write_text(json.dumps(rows,indent=2)+"\n")
    if result.returncode:
        raise SystemExit(result.returncode)
    assert json.loads((output / "result.json").read_text())["synchronous_original_save_verified"]
    assert len(list((output / "renderer3d-reference").glob("model-voxel-lock_study_*.pam"))) == 48*9
python = "/private/var/folders/2h/jfs4f82d6dv54t_m4v49cd_80000gn/T/opencode/voxel-art-20261002-venv/bin/python"
result = subprocess.run([python,"tools/assets/compare_galleries.py",str(root / f"{prefix}-vulkan/renderer3d-reference"),
    str(root / f"{prefix}-opengl/renderer3d-reference"),"--pattern","model-voxel-lock_study_*","--output",str(root / (prefix+"-strict.json"))])
assert result.returncode in (0,1)
comparison = json.loads((root / (prefix+"-strict.json")).read_text())
summary = {"reviewed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"unbound_genuine_3d_studies":48,
    "native_and_orbit_street_images_compared":comparison["images"],"different_images":len(comparison["differences"]),
    "different_pixels":sum(row.get("changed_pixels",0) for row in comparison["differences"]),
    "prior_models_and_bindings_exact":1831,"open_original_sea_level_lamp_verified":args.require_open_lamp,
    "front_profile_structural_screen":args.require_front_profile,
    "all_backends_strict_exact":result.returncode == 0,"strict_exit_code":result.returncode,"approved":False,
    "scope":manifest["scope"]}
(root / (prefix+"-verification.json")).write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary))
if result.returncode:
    raise SystemExit(result.returncode)

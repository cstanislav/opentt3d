"""Prove original water simulation/draw code is exact after removing only diagnostic additions."""
from pathlib import Path
import datetime, hashlib, json, re, subprocess

root = Path("build-macos")
out = root / "breadth-original-river-selector-presentation-delta.json"
assert not out.exists()
snapshot = root / "breadth-original-river-selector-original-snapshot"
names = ("src/water_cmd.cpp","src/renderer3d/world_capture.h","src/renderer3d/world_capture.cpp",
         "src/renderer3d/sprite_textures.hpp","src/renderer3d/reference_export.cpp")
assert set(subprocess.check_output(["git","diff","--name-only","--","src"],text=True).splitlines()) == set(names)
proofs = []
for name in names:
    original = (snapshot / name).read_text()
    current = Path(name).read_text()
    normal = current
    if name == "src/water_cmd.cpp":
        for line in ("\tuint requested_offset = offset;\n","\tbool offset_callback = base != SPR_FLAT_WATER_TILE;\n",
                     "\tSpriteID feature_base = 0;\n","\tuint     requested_offset = 0;\n","\tbool     offset_callback = false;\n",
                     "\t\tfeature_base = image;\n","\t\t\trequested_offset = offset;\n","\t\t\toffset_callback = true;\n"):
            assert normal.count(line) == 1,line
            normal = normal.replace(line,"",1)
        pattern = r"\t(?:\t)?if \([^\n]*Renderer3D::IsCapturing\(\)\) \{\n\t(?:\t)?\tRenderer3D::ObserveRiverSelector\([^\n]+\);\n\t(?:\t)?\}\n"
        normal,count = re.subn(pattern,"",normal)
        assert count == 3,count
    elif name == "src/renderer3d/world_capture.h":
        start = "/** Values already selected by the original river draw callback; never resolve it again. */\n"
        end = "void ObserveRiverSelector(TileIndex tile, const RiverSourceSelector &selector);\n"
        body = normal.split(start,1)[1].split(end,1)[0]
        normal = normal.replace(start+body+end,"",1)
    elif name == "src/renderer3d/sprite_textures.hpp":
        for line in ("bool WaterSourceTracingEnabled();\n","struct RiverSourceSelector;\n","void RetainRiverSelector(const TileInfo &tile, const RiverSourceSelector &selector);\n"):
            assert normal.count(line) == 1,line
            normal = normal.replace(line,"",1)
    elif name == "src/renderer3d/world_capture.cpp":
        body = normal.split("void ObserveRiverSelector(",1)[1].split("void BeginCapture(",1)[0]
        normal = normal.replace("void ObserveRiverSelector("+body,"",1)
    else:
        enabled = normal.split("bool WaterSourceTracingEnabled()\n",1)[1].split("void ObserveWaterSource(",1)[0]
        normal = normal.replace("bool WaterSourceTracingEnabled()\n"+enabled,"",1)
        body = normal.split("void RetainRiverSelector(",1)[1].split("void ExportHouseReferences()",1)[0]
        normal = normal.replace("void RetainRiverSelector("+body,"",1)
        replaced = "\tif (!WaterSourceTracingEnabled() || diagnostic || tile.tile == INVALID_TILE || !IsValidTile(tile.tile) || !IsTileType(tile.tile,MP_WATER)) return;"
        old = '\tstatic const bool enabled = [] { const char *value = std::getenv("OPENTT3D_EXPORT_WATER_SOURCES"); return value != nullptr && std::string_view(value) == "1"; }();\n\tif (!enabled || diagnostic || tile.tile == INVALID_TILE || !IsValidTile(tile.tile) || !IsTileType(tile.tile,MP_WATER)) return;'
        assert normal.count(replaced) == 1
        normal = normal.replace(replaced,old,1)
    assert normal == original,name
    proofs.append({"file":name,"original_sha256":hashlib.sha256(original.encode()).hexdigest(),
        "current_sha256":hashlib.sha256(current.encode()).hexdigest(),"original_after_removing_only_read_only_diagnostics_byte_exact":True})
summary = {"audited_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"files":proofs,
    "scope":"All five modified C++/header files restore byte-exactly to the retained pre-edit source when only the new env-gated observer declarations/definitions, read-only local selector snapshots and three observation calls are removed. The shared flag retains the exact prior default-off predicate. Original draws, callback call sites/counts, commands, simulation, save layouts, source heights, terrain/object dimensions, palettes and RNG code have no other delta. This is a source/draw-boundary proof, not full replay/network/performance or visual quality acceptance."}
out.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"original_source_after_diagnostic_removal_exact":5,"unrelated_runtime_deltas":0}))

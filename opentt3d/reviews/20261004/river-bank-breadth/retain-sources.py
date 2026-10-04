"""Retain actual flat-bank owners and pinned authoring layers without decoding geometry."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import pypdn
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PIN = "013cbc9e700c796af001a381a2d93592d49146ac"
UPSTREAM = ROOT / "build-opengfx2"


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / "sources-complete-survey"
    if target.exists(): raise ValueError("Retain previous source studies")
    target.mkdir()
    retained = []
    prior = ROOT / "opentt3d/reviews/20261003/river-natural-selector-breadth/source-file-map.json"
    matrix = json.loads(prior.read_text())
    for climate in ("temperate","arctic","tropic","toyland"):
        for edge in range(12):
            entry = next(row for row in matrix if row["base_set_family"] == "classic" and row["climate"] == climate and row["backend"] == "vulkan" and
                row["feature"] == "CF_RIVER_EDGE" and row["requested_offset"] == edge and row["resolved_offset"] == edge and row["source_height"] > 0)
            observed = json.loads((Path(entry["original_image"]).parent / "river-selectors.json").read_text())["observations"]
            row = next(row for row in observed if row["feature"] == entry["feature"] and row["tile"] == entry["tile"] and row["requested_offset"] == edge)
            assert row["slope"] == 0 and row["source_height"] > 0 and row["base_set"] == "OpenGFX2 Classic"
            original = ROOT / entry["portable_image"]
            assert digest(original) == entry["sha256"]
            destination = target / f"{climate}-flat-{edge}.pam"
            shutil.copy2(original,destination)
            retained.append({**row,"source_pam":str(destination.relative_to(ROOT)),"source_pam_sha256":digest(destination),
                "actual_selection_provenance":entry,"prior_source_matrix_sha256":digest(prior),
                "native_offset":[value//4 for value in row["source_offset"]],
                "native_size":[value//4 for value in row["source_size"]],"geometry_approved":False,
                "scope":"One actual elevated flat-bank source selection; not sea-level, snow/desert, grid parameter, sloped group, theoretical input or absence coverage."})
    (HERE / "actual-source-index.json").write_text(json.dumps(retained,indent=2)+"\n")
    author = HERE / "upstream"; author.mkdir()
    provenance,layers = [],[]
    for kind in ("overlaynormal","overlayalpha","overlayshading"):
        for suffix in ("png","pdn"):
            name = "river_"+kind+"."+suffix
            relative = "graphics/infrastructure/64/"+name
            pointer = subprocess.check_output(["git","show",PIN+":"+relative],cwd=UPSTREAM)
            match = re.fullmatch(rb"version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize (\d+)\n",pointer)
            assert match
            sha,size = match[1].decode(),int(match[2])
            url = f"https://media.githubusercontent.com/media/OpenTTD/OpenGFX2/{PIN}/{relative}"
            with urllib.request.urlopen(url,timeout=60) as response: payload = response.read(size+1)
            assert len(payload) == size and hashlib.sha256(payload).hexdigest() == sha
            path = author / name; path.write_bytes(payload)
            (author / (name+".lfs-pointer")).write_bytes(pointer)
            provenance.append({"path":relative,"upstream_commit":PIN,"url":url,"sha256":sha,"bytes":size,
                "portable":str(path.relative_to(ROOT))})
            if suffix != "pdn": continue
            document = pypdn.read(str(path)); directory = HERE / "original-layers" / path.stem; directory.mkdir(parents=True)
            for index,layer in enumerate(document.layers):
                destination = directory / (f"{index:02d}-"+re.sub(r"[^a-z0-9]+","-",layer.name.lower()).strip("-")+".png")
                Image.fromarray(layer.image).save(destination)
                layers.append({"document":str(path.relative_to(ROOT)),"document_sha256":sha,"index":index,"name":layer.name,
                    "visible":layer.visible,"opacity":layer.opacity,"blend_mode":int(layer.blendMode),
                    "image":str(destination.relative_to(ROOT)),"sha256":digest(destination),"size":[document.width,document.height]})
    for name in ("templates/zoom-sensitive.pnml","graphics/infrastructure/canalriver_terrainoverlay.py",
        "baseset/nml/extra/extra-plus-rivers.pnml","graphics/tools.py","LICENSE"):
        (author / Path(name).name).write_bytes(subprocess.check_output(["git","show",PIN+":"+name],cwd=UPSTREAM))
    (HERE / "pinned-source-index.json").write_text(json.dumps({"retained_utc":datetime.now(timezone.utc).isoformat(),
        "files":provenance,"original_layers":layers,"local_lfs_pointers_unchanged":True,"geometry_approvals":0},indent=2)+"\n")
    print(json.dumps({"actual_elevated_flat_sources":len(retained),"pinned_authoring_files":len(provenance),"original_layers":len(layers),"quality_approvals":0}))


if __name__ == "__main__": main()

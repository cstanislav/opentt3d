"""Retain exact pinned upstream river layers, without replacing LFS pointer files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
UPSTREAM = ROOT / "build-opengfx2"
COMMIT = "013cbc9e700c796af001a381a2d93592d49146ac"
NAMES = (
    "universal_rivertiles_cbt32bpp.png", "universal_rivertiles_cbt32bpp.pdn",
    "universal_rivertiles_palmask.png", "universal_rivertiles_32bpp.pdn",
    "toyland_rivertiles_cbt32bpp.png", "toyland_rivertiles_cbt32bpp.pdn",
    "toyland_rivertiles_palmask.png", "toyland_rivertiles_palmask.pdn",
    "toyland_rivertiles_32bpp.pdn",
)


def main():
    target = HERE / "upstream"
    if target.exists(): raise ValueError("Retain existing upstream files; choose a fresh study")
    target.mkdir()
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True).strip() == COMMIT
    rows = []
    for name in NAMES:
        relative = "graphics/terrain/64/" + name
        pointer = subprocess.check_output(["git", "show", COMMIT+":"+relative], cwd=UPSTREAM)
        match = re.fullmatch(rb"version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize (\d+)\n", pointer)
        assert match, "Missing pinned LFS provenance"
        sha, size = match[1].decode(), int(match[2])
        url = f"https://media.githubusercontent.com/media/OpenTTD/OpenGFX2/{COMMIT}/{relative}"
        with urllib.request.urlopen(url, timeout=60) as response: payload = response.read(size+1)
        assert len(payload) == size and hashlib.sha256(payload).hexdigest() == sha
        (target / name).write_bytes(payload)
        (target / (name+".lfs-pointer")).write_bytes(pointer)
        rows.append({"upstream_path":relative,"upstream_commit":COMMIT,"url":url,"sha256":sha,"bytes":size,
                     "portable":str((target / name).relative_to(ROOT))})
    for name in ("baseset/nml/extra/extra-plus-rivers.pnml", "templates/zoom-sensitive.pnml", "LICENSE"):
        payload = subprocess.check_output(["git", "show", COMMIT+":"+name], cwd=UPSTREAM)
        (target / Path(name).name).write_bytes(payload)
    value = {"retained_utc":datetime.now(timezone.utc).isoformat(),"files":rows,"geometry_approved":False,
             "scope":"Pinned original authoring files only; local LFS pointers remain unchanged. Runtime source equivalence and palette/ownership must be proved independently."}
    (HERE / "upstream-index.json").write_text(json.dumps(value, indent=2)+"\n")
    print(json.dumps({"upstream_files":len(rows),"verified_bytes":sum(row["bytes"] for row in rows),"approvals":0}))


if __name__ == "__main__": main()

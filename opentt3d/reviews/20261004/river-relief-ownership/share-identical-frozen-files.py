"""Preserve exact owned freezes while sharing byte-identical generated files.

Only this increment's two named frozen matrices are eligible. Source artwork,
captures, failures, user work and primary developer binaries are never touched.
Each replacement retains the same complete bytes, mode and SHA-256, and uses a
temporary hard link before atomic replacement. No unique evidence is removed.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    report = HERE / "identical-frozen-file-sharing.json"
    if report.exists(): raise ValueError("Retain the previous sharing receipt")
    groups,records = {},[]
    for prefix in ("initial","complete-water"):
        for scope in ("canonical","complete","missing-owner","missing-water","changed-source"):
            frozen = ROOT / "build-macos" / ("breadth-original-river-relief-world-"+prefix+"-"+scope+"-frozen-build")
            manifest = json.loads((frozen / "manifest.json").read_text())
            for name,sha in manifest["sha256"].items():
                path = frozen / name
                assert path.is_file() and not path.is_symlink() and digest(path) == sha
                mode = stat.S_IMODE(path.stat().st_mode)
                key = (sha,mode,path.stat().st_size)
                if key not in groups: groups[key] = path; continue
                original = groups[key]
                if path.stat().st_ino == original.stat().st_ino: continue
                temporary = path.with_name(path.name+".verified-identical-link")
                if temporary.exists(): raise ValueError("Retain an unexpected previous temporary file")
                os.link(original,temporary)
                assert digest(temporary) == sha and stat.S_IMODE(temporary.stat().st_mode) == mode
                temporary.replace(path)
                assert digest(path) == sha
                records.append({"path":str(path.relative_to(ROOT)),"shared_with":str(original.relative_to(ROOT)),
                    "sha256":sha,"bytes_retained":key[2],"mode_retained":mode,"byte_exact":True})
    value = {"utc":datetime.now(timezone.utc).isoformat(),"files":records,"unique_artwork_or_evidence_removed":False,
             "complete_file_bytes_retained":sum(row["bytes_retained"] for row in records)}
    report.write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value))


if __name__ == "__main__": main()

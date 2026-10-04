"""Losslessly compact only our copied successful generated atlas controls.

Every original build PAM, original sprite source and rejected initial run stays
untouched. Headers and RGBA reconstruct byte-exactly before a copied PAM retires.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

from PIL import Image, PngImagePlugin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools/assets"))
from compact_reviews import load_pam, verify_png


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    eligible = []
    maps = {}
    for name in ("source-file-map.json", "visibility-source-file-map.json"):
        path = HERE / name
        rows = json.loads(path.read_text())
        maps[path] = rows
        for row in rows:
            image = ROOT / row["portable_image"]
            if image.suffix != ".pam" or not image.name.startswith("model-world-atlas-") or "initial" in image.parts:
                continue
            assert not image.is_symlink() and image.resolve().is_relative_to(HERE / "native-controls")
            original = ROOT / row["original"]
            assert original.is_file() and digest(original) == digest(image) == row["sha256"]
            eligible.append((image, row))
    if not args.apply:
        print(json.dumps({"eligible_copied_atlas_controls": len(eligible), "raw_bytes": sum(image.stat().st_size for image, _ in eligible), "originals_modified": False}))
        return
    assert len(eligible) == 376
    snapshots = HERE / "before-portable-compaction"
    snapshots.mkdir()
    for path in maps:
        shutil.copy2(path, snapshots / path.name)
    records = []
    for image, row in eligible:
        header, size, pixels = load_pam(image)
        png = image.with_suffix(".png")
        assert not png.exists()
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("opentt3d_pam_header", header.decode("ascii"))
        Image.frombytes("RGBA", size, pixels).save(png, pnginfo=metadata, compress_level=6)
        verify_png(png, header, size, pixels)
        assert hashlib.sha256(header+pixels).hexdigest() == row["sha256"]
        record = {"copied_pam": str(image.relative_to(ROOT)), "png": str(png.relative_to(ROOT)),
                  "original_pam": row["original"], "pam_sha256": row["sha256"], "png_sha256": digest(png),
                  "raw_bytes": image.stat().st_size, "png_bytes": png.stat().st_size}
        records.append(record)
        row.update(portable_image=record["png"], encoding="lossless-rgba-png", portable_sha256=record["png_sha256"], raw_bytes=record["raw_bytes"])
    # Persist the reversible mappings before retiring any newly made copied PAM.
    for path, rows in maps.items():
        path.write_text(json.dumps(rows, indent=2) + "\n")
    receipt = {"compacted_utc": datetime.now(timezone.utc).isoformat(), "images": records,
               "original_build_pams_modified": False, "original_sprite_sources_modified": False, "rejected_initial_pams_modified": False,
               "raw_bytes": sum(row["raw_bytes"] for row in records), "png_bytes": sum(row["png_bytes"] for row in records)}
    receipt_path = HERE / "portable-atlas-compaction.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    for image, row in eligible:
        assert digest(image) == row["sha256"] and digest(ROOT / row["original"]) == row["sha256"]
        image.unlink()
    print(json.dumps({key: value for key, value in receipt.items() if key != "images"}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Losslessly compact generated model-gallery PAMs; run in the Pillow art container.

Only successful runs listed in explicit validation manifests are eligible, using
build-*/<run>/renderer3d-reference/model-*.pam files. Original
sprite references, screenshots, saves, model sources and logs are left in place.
PNG metadata retains the complete PAM header, and every RGBA byte is verified
before the uncompressed generated image is removed.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path


def load_pam(path):
    with path.open("rb") as source:
        header = bytearray(source.readline())
        if header != b"P7\n":
            raise ValueError("Not an exported PAM image")
        fields = {}
        while len(header) < 4096:
            line = source.readline()
            if not line:
                raise ValueError("Incomplete PAM header")
            header.extend(line)
            if line == b"ENDHDR\n":
                break
            key, value = line.decode("ascii").strip().split(" ", 1)
            fields[key] = value
        else:
            raise ValueError("Unexpectedly long PAM header")
        if fields.get("DEPTH") != "4" or fields.get("MAXVAL") != "255" or fields.get("TUPLTYPE") != "RGB_ALPHA":
            raise ValueError("Only the renderer's 8-bit RGBA export is supported")
        size = (int(fields["WIDTH"]), int(fields["HEIGHT"]))
        pixels = source.read()
    if min(size) <= 0 or len(pixels) != size[0] * size[1] * 4:
        raise ValueError("Incomplete or unexpected PAM pixel payload")
    return bytes(header), size, pixels


def verify_png(source, header, size, pixels):
    from PIL import Image

    with Image.open(source) as image:
        if image.mode != "RGBA" or image.size != size or image.tobytes() != pixels:
            raise ValueError("PNG does not preserve every original RGBA byte")
        if image.info.get("opentt3d_pam_header") != header.decode("ascii"):
            raise ValueError("PNG does not preserve the original PAM header")


def verified_runs(build, manifests):
    """Run paths are absolute or relative to the build's parent; failures win."""
    outcomes = {}
    for manifest in manifests:
        rows = json.loads(manifest.read_text())
        if not isinstance(rows, list):
            raise ValueError(f"Expected a list of completed run records: {manifest}")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("output"), str) or type(row.get("exit_code")) is not int:
                raise ValueError(f"Missing explicit output/exit_code in {manifest}")
            run = Path(row["output"])
            if not run.is_absolute():
                run = build.parent / run
            linked = run.is_symlink()
            run = run.resolve()
            if run.parent != build:
                continue
            outcomes[run] = outcomes.get(run, True) and row["exit_code"] == 0 and not linked
    return sorted(run for run, success in outcomes.items() if success)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_dirs", nargs="+", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--validation-manifest", type=Path, action="append", default=[],
                        help="Completed run records with output and exit_code; repeat as needed. Required to apply.")
    args = parser.parse_args()
    if args.apply and not args.validation_manifest:
        parser.error("--apply requires explicit successful-run --validation-manifest evidence")
    if args.apply:
        from PIL import Image, PngImagePlugin
    for requested in args.build_dirs:
        build = requested.resolve()
        if not build.name.startswith("build-") or not (build / "CMakeCache.txt").is_file():
            parser.error(f"Not a configured build directory: {build}")
        runs = verified_runs(build, args.validation_manifest)
        paths = sorted(path for run in runs for path in (run / "renderer3d-reference").glob("model-*.pam")
                       if not path.is_symlink() and path.resolve().parent == run / "renderer3d-reference")
        if not args.apply:
            print(json.dumps({"build": str(build), "verified_runs": len(runs), "eligible_images": len(paths), "raw_bytes": sum(path.stat().st_size for path in paths), "apply": False}))
            continue
        records, errors = [], []
        raw_bytes = png_bytes = 0
        for path in paths:
            png = path.with_suffix(".png")
            try:
                header, size, pixels = load_pam(path)
                if png.is_symlink():
                    raise ValueError("Existing PNG is a symbolic link")
                if png.exists():
                    # Never overwrite a different existing review artifact.
                    verify_png(png, header, size, pixels)
                else:
                    metadata = PngImagePlugin.PngInfo()
                    metadata.add_text("opentt3d_pam_header", header.decode("ascii"))
                    buffer = io.BytesIO()
                    Image.frombytes("RGBA", size, pixels).save(buffer, format="PNG", pnginfo=metadata, compress_level=6)
                    verify_png(io.BytesIO(buffer.getvalue()), header, size, pixels)
                    with png.open("xb") as destination:
                        destination.write(buffer.getvalue())
                        destination.flush()
                        os.fsync(destination.fileno())
                    verify_png(png, header, size, pixels)
                original_size, encoded_size = path.stat().st_size, png.stat().st_size
                record = {"original": str(path.relative_to(build)), "image": str(png.relative_to(build)),
                          "pam_sha256": hashlib.sha256(header + pixels).hexdigest(),
                          "raw_bytes": original_size, "png_bytes": encoded_size}
                path.unlink()
                records.append(record)
                raw_bytes += original_size
                png_bytes += encoded_size
            except (OSError, ValueError, KeyError, SyntaxError) as error:
                errors.append({"file": str(path.relative_to(build)), "error": str(error)})
        manifest = build / ("review-compaction-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        manifest.write_text(json.dumps({"validation_manifests": [str(path.resolve()) for path in args.validation_manifest],
                                        "images": records, "preserved_errors": errors}, indent=2) + "\n")
        print(json.dumps({"build": str(build), "converted": len(records), "raw_bytes": raw_bytes, "png_bytes": png_bytes,
                          "saved_bytes": raw_bytes - png_bytes, "preserved_errors": len(errors), "manifest": str(manifest)}))


if __name__ == "__main__":
    main()

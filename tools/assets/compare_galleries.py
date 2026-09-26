#!/usr/bin/env python3
"""Compare complete rendered galleries exactly, including compacted RGBA PNGs.

Run in the Pillow art container. This checks renderer changes against a previous
capture; it does not establish visual fidelity to the original sprite artwork.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
from contact_sheet import read_pam


def captures(directory, pattern):
    images = {}
    for path in directory.glob(pattern + ".png"):
        with Image.open(path) as image:
            if "opentt3d_pam_header" in image.info:
                images[path.stem] = path
    images.update({path.stem: path for path in directory.glob(pattern + ".pam")})
    return images


def image(path):
    if path.suffix == ".pam":
        return read_pam(path)
    with Image.open(path) as source:
        return source.convert("RGBA")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--pattern", default="model-voxel-*")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pixel-details", type=int, default=0, help="Include up to this many exact differing pixel coordinates per image")
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Use a new comparison report path")
    if args.pixel_details < 0:
        parser.error("--pixel-details must be nonnegative")
    if args.reference.is_file() and args.actual.is_file():
        reference,actual = {"image":args.reference},{"image":args.actual}
    else:
        reference, actual = captures(args.reference, args.pattern), captures(args.actual, args.pattern)
    if not reference or reference.keys() != actual.keys():
        parser.error(f"Gallery sets differ or are empty: missing={sorted(reference.keys()-actual.keys())}, added={sorted(actual.keys()-reference.keys())}")
    report = {"reference": str(args.reference), "actual": str(args.actual), "images": len(reference), "pixels": 0, "differences": []}
    for name in sorted(reference):
        a, b = image(reference[name]), image(actual[name])
        if a.size != b.size:
            report["differences"].append({"name": name, "reference_size": a.size, "actual_size": b.size})
            continue
        left, right = a.tobytes(), b.tobytes()
        report["pixels"] += a.width*a.height
        if left != right:
            changed = sum(left[i:i+4] != right[i:i+4] for i in range(0, len(left), 4))
            first = next(i for i in range(0, len(left), 4) if left[i:i+4] != right[i:i+4])
            report["differences"].append({"name": name, "changed_pixels": changed,
                                          "first_pixel": [first//4 % a.width, first//4 // a.width],
                                          "reference_rgba": list(left[first:first+4]), "actual_rgba": list(right[first:first+4])})
            if args.pixel_details:
                details = []
                for offset in range(0,len(left),4):
                    if left[offset:offset+4] == right[offset:offset+4]:
                        continue
                    details.append({"pixel":[offset//4 % a.width,offset//4 // a.width],"reference":list(left[offset:offset+4]),"actual":list(right[offset:offset+4])})
                    if len(details) == args.pixel_details:
                        break
                report["differences"][-1]["pixels"] = details
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if report["differences"]:
        raise SystemExit("Rendered gallery RGBA pixels differ")


if __name__ == "__main__":
    main()

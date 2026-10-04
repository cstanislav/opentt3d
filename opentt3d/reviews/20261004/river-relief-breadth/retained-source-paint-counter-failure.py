"""Retain disjoint source-paint studies; unresolved colours prohibit runtime substitution.

The colour lists below are manually inspected semantic authoring annotations.
This never creates or fits geometry, inpaints hidden water, resolves callbacks,
changes palette indices or masks any renderer comparison. All source pixels,
including undecided edge/transition paint, reconstruct exactly.
"""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT / "tools/assets"))
from contact_sheet import read_pam

ROCK = {
    (16,16,16),(32,32,32),(48,48,48),(65,64,65),(82,80,82),(90,88,90),
    (98,101,98),(115,117,115),(131,133,131),(148,149,148),(168,168,168),(184,184,184)
}
ISLAND = {
    (47,95,3),(63,111,11),(31,79,3),(250,210,0),(182,119,23),(210,154,31),(230,182,15),
    (146,147,146),(214,214,214),(166,166,166),(182,182,182),(198,198,198)
}
UNDECIDED = {(132,132,164),(68,76,92),(108,116,132),(84,92,108),(104,104,104),(127,127,127)}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    target = HERE / "source-paint-separation"
    if target.exists(): raise ValueError("Retain the previous source-paint study")
    target.mkdir()
    rows = []
    for source in json.loads((HERE / "source-index.json").read_text()):
        path = ROOT / source["portable_source"]
        original = read_pam(path)
        pixels = list(original.get_flattened_data())
        colour_set = ISLAND if source["climate"] == 3 else ROCK
        ownership = [0 if rgba[3] == 0 else 2 if rgba[:3] in colour_set else 3 if rgba[:3] in UNDECIDED else 1 for rgba in pixels]
        layers = {}
        for owner,label in ((1,"water-paint"),(2,"relief-paint"),(3,"undecided-paint")):
            # Preserve even invisible source RGB, rather than normalizing it away.
            values = [rgba if assigned == owner or (owner == 1 and assigned == 0) else (0,0,0,0)
                      for rgba,assigned in zip(pixels,ownership)]
            layer = Image.new("RGBA",original.size); layer.putdata(values)
            destination = target / f"{source['climate_name']}-{source['slope_name'].lower()}-{label}.png"
            layer.save(destination)
            layers[label] = destination
        reconstructed = bytearray(len(original.tobytes()))
        for path in layers.values():
            with Image.open(path) as retained:
                for index,value in enumerate(retained.tobytes()): reconstructed[index] |= value
        assert bytes(reconstructed) == original.tobytes()
        divisor = source["sprite_cache_to_native_divisor"]
        native = original.resize(tuple(source["native_source_size"]),Image.Resampling.NEAREST)
        assert native.resize(original.size,Image.Resampling.NEAREST).tobytes() == original.tobytes()
        counts = {label:ownership.count(owner)//(divisor*divisor) for owner,label in ((1,"water"),(2,"relief"),(3,"undecided"))}
        assert all(ownership.count(owner)%(divisor*divisor) == 0 for owner in (1,2,3))
        undecided = [{"screen_xy":[x+source["native_offset"][0],y+source["native_offset"][1]],"rgba":list(native.getpixel((x,y)))}
                     for y in range(native.height) for x in range(native.width)
                     if native.getpixel((x,y))[3] and native.getpixel((x,y))[:3] in UNDECIDED]
        mask = Image.new("L",original.size); mask.putdata(ownership)
        mask_path = target / f"{source['climate_name']}-{source['slope_name'].lower()}-ownership.png"
        mask.save(mask_path)
        rows.append({"source":source,"layers":{label:str(path.relative_to(ROOT)) for label,path in layers.items()},
            "ownership":str(mask_path.relative_to(ROOT)),"native_pixel_counts":counts,"undecided_pixels":undecided,
            "exact_complete_rgba_reconstruction":True,"reconstructed_rgba_sha256":hashlib.sha256(reconstructed).hexdigest(),
            "source_sha256":source["sha256"],"sha256":{str(path.relative_to(ROOT)):digest(path) for path in [mask_path,*layers.values()]},
            "hidden_water_inpainted":False,"palette_phase_indices_recovered":False,"runtime_binding_allowed":False,
            "scope":"Lossless paint/ownership study only. Uncertain edge colours stay in a third layer. No original paint is discarded, no hidden water is invented, no volume or world coverage is inferred, and no comparison uses this mask."})
    (target / "index.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps({"complete_source_reconstructions":8,"relief_native_pixels":sum(row["native_pixel_counts"]["relief"] for row in rows),
        "undecided_native_pixels":sum(row["native_pixel_counts"]["undecided"] for row in rows),"runtime_binding_allowed":False,"approvals":0}))


if __name__ == "__main__":
    main()

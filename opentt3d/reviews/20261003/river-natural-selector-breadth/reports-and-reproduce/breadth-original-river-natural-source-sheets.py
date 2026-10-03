"""Display complete observed originals by feature/slope/input; do not infer their internal owners."""
from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw

root = Path("build-macos")
out = root / "breadth-original-river-natural-source-sheets-registered"
assert not out.exists()
out.mkdir()
report = json.loads((root / "breadth-original-river-natural-selector-verification.json").read_text())
runs = json.loads((root / "breadth-original-river-natural-selector-runs.json").read_text())
index = []
for family in ("classic","opengfx"):
    for climate in ("temperate","arctic","tropic","toyland"):
        candidates = {}
        for row in runs:
            if row["family"] != family or row["climate"] != climate or row["backend"] != "vulkan" or not row["tracing"]:
                continue
            directory = Path(row["output"]) / "renderer3d-reference"
            sources = json.loads((directory / "river-selectors.json").read_text())["observations"]
            for source in sources:
                assert not source["absent"]
                key = (source["feature"],source["slope"],source["requested_offset"])
                candidates.setdefault(key,(source,directory / source["source_image"],row["seed"]))
        assert len(candidates) == 25,(family,climate,len(candidates))
        width,height = 360,360
        image = Image.new("RGBA",(width*5,height*5),(30,34,40,255))
        draw = ImageDraw.Draw(image)
        for number,(key,(source,path,seed)) in enumerate(sorted(candidates.items())):
            x,y = number%5*width,number//5*height
            draw.text((x+4,y+4),f"{source['feature']} slope={source['slope']} input={source['requested_offset']}",fill=(245,245,245,255))
            draw.text((x+4,y+20),f"base {source['base_sprite']} output {source['resolved_offset']} sprite {source['selected_sprite']}",fill=(205,205,205,255))
            draw.text((x+4,y+36),f"offset {source['source_offset']} height {source['source_height']} tile {source['tile_xy']}",fill=(205,205,205,255))
            with path.open('rb') as handle:
                assert handle.readline() == b"P7\n"
                fields = {}
                while True:
                    line = handle.readline()
                    if line == b"ENDHDR\n": break
                    k,v = line.decode('ascii').strip().split(' ',1)
                    fields[k] = v
                size = (int(fields['WIDTH']),int(fields['HEIGHT']))
                pixels = handle.read()
            assert [size[0]*4,size[1]*4] == source["source_size"] and len(pixels) == size[0]*size[1]*4
            original = Image.frombytes('RGBA',size,pixels)
            ox,oy = source["source_offset"]
            assert ox%4 == oy%4 == 0
            native_offset = [ox//4,oy//4]
            placement = [50+native_offset[0],52+native_offset[1]]
            assert min(placement) >= 0 and placement[0]+original.width <= 120 and placement[1]+original.height <= 104
            panel = Image.new('RGBA',(120,104))
            panel.alpha_composite(original,placement)
            image.alpha_composite(panel.resize((360,312),Image.Resampling.NEAREST),(x,y+48))
            index.append(dict(source,base_set_family=family,climate_name=climate,seed=seed,original_image=str(path),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sheet=str(out / (family+"-"+climate+".png")),
                display_scale=3,native_source_size=list(size),sprite_cache_to_native_divisor=4,
                native_tile_anchor=[50,52],native_offset=native_offset,complete_uncropped_source=True,
                raised_water_ownership_verified=False,geometry_approved=False))
        image.save(out / (family+"-"+climate+".png"))
assert len(index) == 200
(out / "index.json").write_text(json.dumps(index,indent=2)+"\n")
print(json.dumps({"sheets":8,"complete_feature_input_source_states":200,"approved_models":0,
    "scope":"Complete originals at 3x nearest-neighbour display scale, registered at original native offsets after the original 4x sprite-cache normalization, with source flags/input/output/height retained. One observed tile-local source per feature/slope/input/climate/base set, not every ground variant or phase. Original native PAM/header/registration/colour/alpha bytes remain unchanged, not cropped, clipped, extruded or turned into model/ownership approval."}))

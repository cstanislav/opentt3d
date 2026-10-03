"""Display complete actual river ground sources at their declared tile datum, no inferred bank."""
from pathlib import Path
import hashlib, json, sys
from PIL import Image, ImageDraw

sys.path.insert(0,"tools/assets")
from compare_galleries import image

root = Path("build-macos")
out = root / "breadth-original-river-selected-source-sheets"
assert not out.exists()
out.mkdir()
selected = json.loads((root / "breadth-original-river-selected-source-verification.json").read_text())["selected_sources"]
files = {(Path(row["portable_image"]).parts[-2],row["sha256"]):Path(row["portable_image"])
         for row in json.loads(Path("opentt3d/reviews/20261003/water-live-selectors/source-file-map.json").read_text())}
index = []
for climate,observed in selected.items():
    rows = observed["selected_ground_sources"]
    sheet = Image.new("RGB",(3*360,((len(rows)+2)//3)*360),(38,39,47))
    draw = ImageDraw.Draw(sheet)
    for slot,row in enumerate(rows):
        path = files[climate,row["source_image_sha256"]]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["source_image_sha256"]
        picture = image(path)
        assert list(picture.size) == [value//4 for value in row["source_size"]]
        ox,oy = row["source_offset"]
        assert ox%4 == oy%4 == 0
        offset = (50+ox//4,52+oy//4)
        assert min(offset) >= 0 and offset[0]+picture.width <= 120 and offset[1]+picture.height <= 104
        panel = Image.new("RGBA",(120,104))
        panel.alpha_composite(picture,offset)
        left,top = slot%3*360,slot//3*360
        panel = panel.resize((360,312),Image.Resampling.NEAREST)
        sheet.paste(panel,(left,top+48),panel)
        draw.text((left+6,top+5),f"{climate}, tile{row['tile_xy']}, slope{row['slope']}, sprite{row['sprite']}",fill="white")
        draw.text((left+6,top+19),"Complete source, 3x native; original tile datum",fill="white")
        draw.text((left+6,top+33),"Feature/edge unresolved; no volume or approval",fill="white")
        index.append({"source":row,"source_image":str(path),"climate":climate,"sheet":str(out / (climate+".png")),
            "tile_anchor":[50,52],"native_offset":[ox//4,oy//4],"approved":False})
    sheet.save(out / (climate+".png"))
(out / "index.json").write_text(json.dumps(index,indent=2)+"\n")
print(json.dumps({"actual_ground_source_states":len(index),"sheets":4,"inferred_bank_offsets":False,"approved":False}))

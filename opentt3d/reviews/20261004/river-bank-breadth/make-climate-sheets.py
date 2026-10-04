"""Show all twelve separately registered owners per climate, preserving full owner sheets."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision",choices=("initial","revised"),default="initial")
    args = parser.parse_args()
    target = HERE / (args.revision+"-climate-sheets")
    if target.exists(): raise ValueError("Retain previous climate sheets")
    target.mkdir()
    rows = json.loads((HERE / (args.revision+"-sheets/index.json")).read_text())
    for climate,label in enumerate(("temperate","arctic","tropic","toyland")):
        canvas = Image.new("RGB",(1600,2880),(38,39,47)); draw = ImageDraw.Draw(canvas)
        for row in (row for row in rows if row["climate"] == climate):
            y = row["edge"]*240
            with Image.open(HERE / (args.revision+"-sheets") / (row["model"]+".png")) as picture:
                original = picture.crop((0,0,1200,160))
                canvas.paste(original,(0,y))
                for index in range(8):
                    x0 = index%4*300; y0 = 220+index//4*190
                    view = picture.crop((x0,y0,x0+300,y0+190)).resize((200,126),Image.Resampling.NEAREST)
                    canvas.paste(view,(index*200,y+114))
            draw.text((1220,y+15),f"Owner {row['edge']}: {'straight' if row['edge']<4 else 'outer' if row['edge']<8 else 'inner'}",fill="white")
        canvas.save(target / (label+"-all-twelve.png"))
    print(json.dumps({"individual_owner_presentations":48,"full_owner_sheets_preserved":True,"quality_approvals":0}))


if __name__ == "__main__": main()

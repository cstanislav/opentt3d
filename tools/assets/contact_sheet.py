#!/usr/bin/env python3
"""Prepare review sheets from exported, actually resolved base-set sprite images.

Run in the art/build container (Pillow is installed only there).
"""

import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def read_pam(path):
    with path.open("rb") as source:
        if source.readline() != b"P7\n":
            raise ValueError("Expected a PAM image")
        fields = {}
        while (line := source.readline()) != b"ENDHDR\n":
            key, value = line.decode().strip().split(" ", 1)
            fields[key] = value
        return Image.frombytes("RGBA", (int(fields["WIDTH"]), int(fields["HEIGHT"])), source.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--variant", type=int, default=0)
    parser.add_argument("--stage", type=int, default=3)
    parser.add_argument("--gallery", action="store_true")
    parser.add_argument("--tight", action="store_true", help="Magnify the rendered object in gallery panels with nearest sampling")
    parser.add_argument("--gallery-kind", choices=("signal", "catenary", "depot", "crossing", "bridge", "rail", "station", "road-stop", "fence"), help="Select one model category when a run exports multiple galleries")
    parser.add_argument("--fence-style", type=int, choices=range(7), help="Select a voxel fence family from a gallery export")
    parser.add_argument("--fence-layout", type=int, choices=range(16), help="Select an individually exported railway fence layout")
    parser.add_argument("--foundation", type=int, choices=range(1,14), help="Select a voxel foundation family")
    parser.add_argument("--foundation-slope", type=int, help="Select the slope in a batch of foundation galleries")
    parser.add_argument("--foundation-context", action="store_true", help="Show the foundation with its building or running track")
    parser.add_argument("--gallery-model", type=int, help="Select a house/tree model from a batch export")
    parser.add_argument("--house-source", type=int, nargs="+", choices=range(110), help="Review every original variant/construction stage for selected houses")
    parser.add_argument("--house-layers", action="store_true", help="Keep original ground/body placement in --house-source panels")
    parser.add_argument("--house-comparison", type=int, choices=range(110), help="Compare four voxel house stages with their original ground/body layers")
    parser.add_argument("--industry-source", type=int, nargs="+", choices=range(175), help="Review all original construction states for selected industry tile definitions")
    parser.add_argument("--industry-effect-source", type=int, choices=(10,), help="Review original power-station sparks at their actual parent-relative positions")
    parser.add_argument("--industry-effect-comparison", type=int, choices=(10,), help="Compare six native voxel gantry/spark composites with their original registered layers")
    parser.add_argument("--industry-ground", action="store_true", help="Select original industry ground layers for --industry-source or --industry-comparison")
    parser.add_argument("--depot-source", type=int, choices=range(6), help="Assemble the four original depot directions from their actual layer offsets")
    parser.add_argument("--ship-depot-source", action="store_true", help="Assemble both original two-tile ship depots with their actual layer offsets")
    parser.add_argument("--ship-depot-comparison", action="store_true", help="Compare both complete voxel ship-depot axes with registered original layers")
    parser.add_argument("--dock-source", action="store_true", help="Review all six original dock sections with their ground/body layer offsets")
    parser.add_argument("--dock-comparison", action="store_true", help="Compare all four complete voxel docks with their registered original shore/water layers")
    parser.add_argument("--depot-comparison", type=int, choices=range(6), help="Compare native voxel depots with the four original layered directions")
    parser.add_argument("--vehicle-source", type=int, nargs="+", choices=range(256), help="Review all eight original directions and both cargo states of selected vehicles")
    parser.add_argument("--tree-source", type=int, nargs="+", choices=range(1576, 2010, 7), help="Review every original palette and all seven lifecycle stages of selected tree sprite families at one scale")
    parser.add_argument("--tree-comparison", type=int, choices=range(1576, 2010, 7), help="Compare one family's seven native-scale voxel views with original sources")
    parser.add_argument("--vehicle-comparison", type=int, choices=range(256), help="Compare all eight native-scale voxel directions with original vehicle sources")
    parser.add_argument("--industry-comparison", type=int, choices=range(175), help="Compare all four native-scale voxel construction stages with original industry sources")
    parser.add_argument("--registration", action="store_true", help="Keep the original tile-relative placement in an industry comparison, rather than centring cropped silhouettes")
    parser.add_argument("--source-directory", type=Path, help="Original source export for tree/vehicle/industry comparisons")
    parser.add_argument("--house-pair", type=int, nargs=2, choices=range(110), help="Join two original house tiles using their source offsets")
    parser.add_argument("--house-block", type=int, nargs=4, choices=range(110), help="Join four original house tiles in upstream north/east/west/south order, including their ground layers")
    joined_comparison = parser.add_mutually_exclusive_group()
    joined_comparison.add_argument("--house-block-comparison", type=int, choices=range(107), metavar="PRIMARY", help="Compare a complete four-tile voxel house with its registered original ground/body layers")
    joined_comparison.add_argument("--house-pair-comparison", type=int, choices=range(109), metavar="PRIMARY", help="Compare a complete two-tile voxel house with its original layers; select the original layout using --pair-axis")
    parser.add_argument("--pair-axis", choices=("x", "y"), default="y", help="World axis of the second tile in --house-pair")
    parser.add_argument("--voxel-model", help="Select a named voxel model, or 'context', from --gallery-voxels")
    parser.add_argument("--street", action="store_true", help="Select the four eye-level views of a voxel model/context")
    parser.add_argument("--animation-prefix", help="Review all named voxel animation frames sharing this prefix")
    parser.add_argument("--animation-view", type=int, choices=range(8), default=0)
    parser.add_argument("--ground-detail", type=int, nargs=2, metavar=("KIND", "VARIANT"), help="Select one ground-detail turntable from a batch")
    parser.add_argument("--trees", action="store_true")
    parser.add_argument("--vehicles", action="store_true")
    parser.add_argument("--engine-range", nargs=2, type=int, metavar=("FIRST","LAST"), help="Limit a vehicle overview to an inclusive engine range")
    parser.add_argument("--industries", action="store_true")
    parser.add_argument("--terrain", action="store_true")
    parser.add_argument("--categories", nargs="+", help="Limit terrain/infrastructure sheets to named source categories")
    parser.add_argument("--styles", nargs="+", type=int, help="Limit terrain/infrastructure sheets to selected source style IDs")
    parser.add_argument("--rail-details", action="store_true")
    parser.add_argument("--infrastructure", action="store_true")
    parser.add_argument("--stations", action="store_true")
    parser.add_argument("--bridges", type=int, choices=range(13), metavar="TYPE")
    parser.add_argument("--direction", type=int, choices=range(8), default=5)
    parser.add_argument("--loaded", action="store_true")
    parser.add_argument("--preview", action="store_true", help="Read the positional path as an image and make a bounded-size PNG preview")
    parser.add_argument("--buoy-comparison", action="store_true", help="Compare the original buoy and voxel marker at their actual tile anchors")
    parser.add_argument("--preview-scale", type=int, choices=range(1, 17), default=1, help="Nearest-pixel enlargement for manual material inspection")
    parser.add_argument("--sample", nargs=2, type=int, metavar=("X", "Y"), help="Report a source pixel while inspecting a material preview")
    parser.add_argument("--colours", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"), help="List up to 32 distinct visible colours in an artist-selected material region")
    parser.add_argument("--palette-counts", action="store_true", help="Report visible source-palette colour frequencies during --preview; never generates geometry")
    args = parser.parse_args()
    if args.engine_range and (not args.vehicles or not 0 <= args.engine_range[0] <= args.engine_range[1] < 256):
        parser.error("--engine-range requires --vehicles and an increasing0..255 range")
    if args.street and (not args.gallery or (not args.voxel_model and args.fence_style is None and args.foundation is None)):
        parser.error("Street sheets require --gallery and a voxel model, fence style or foundation")
    if args.foundation_context and (not args.gallery or args.foundation is None):
        parser.error("Foundation context requires --gallery and --foundation")
    if args.fence_layout is not None and (not args.gallery or args.fence_style != 6):
        parser.error("A railway fence layout requires --gallery --fence-style 6")
    if args.registration and args.industry_comparison is None and args.depot_comparison is None and args.house_comparison is None:
        parser.error("--registration requires an industry, depot or house comparison")
    if args.industry_ground and not (args.industry_source or args.industry_comparison is not None):
        parser.error("--industry-ground requires an industry source/comparison selection")
    if args.palette_counts and not args.preview:
        parser.error("--palette-counts requires --preview")
    if args.house_layers and not args.house_source:
        parser.error("--house-layers requires --house-source")
    if args.house_pair and args.house_block:
        parser.error("Choose a two-tile house pair or a four-tile house block")

    def industry_layers(entries):
        if not args.industry_ground:
            return entries
        return [dict(entry, sprite=entry["ground_sprite"], palette=entry["ground_palette"],
                     image=entry["ground_image"], palette_indices=entry["ground_palette_indices"],
                     sprite_offset=entry.get("ground_sprite_offset", [0, 0]),
                     sprite_size=entry.get("ground_sprite_size", [0, 0]), origin=[0, 0, 0]) for entry in entries]

    def house_image(entry, directory):
        if "ground_image" not in entry:
            parser.error("Layered house review needs a current source export with ground metadata")
        layers = []
        if entry["ground_image"]:
            gx,gy = (value//4 for value in entry["ground_sprite_offset"])
            layers.append((read_pam(directory / entry["ground_image"]),gx,gy))
        if entry["image"]:
            x,y,z = entry["origin"]
            dx,dy = entry["sprite_offset"]
            layers.append((read_pam(directory / entry["image"]),2*(y-x)+dx//4,x+y-z+dy//4))
        if not layers:
            return Image.new("RGBA", (1,1)), (0,0,0,0)
        left, top = min(x for _,x,y in layers), min(y for _,x,y in layers)
        right = max(x+image.width for image,x,y in layers)
        bottom = max(y+image.height for image,x,y in layers)
        joined = Image.new("RGBA", (right-left,bottom-top))
        for image,x,y in layers:
            joined.alpha_composite(image,(x-left,y-top))
        visible = joined.getchannel("A").getbbox()
        if not visible:
            return Image.new("RGBA", (1,1)), (0,0,0,0)
        return joined.crop(visible), (left+visible[0],top+visible[1],left+visible[2],top+visible[3])

    if args.house_block_comparison is not None or args.house_pair_comparison is not None:
        if args.source_directory is None:
            parser.error("Joined house comparison requires --source-directory")
        catalogue = json.loads((args.source_directory / "houses.json").read_text())
        records, panels = [], []
        block = args.house_block_comparison is not None
        base = args.house_block_comparison if block else args.house_pair_comparison
        kind = "block" if block else "pair"
        if args.variant != 0:
            parser.error("Complete native joined-house exports currently use original variant0")
        for stage in range(4):
            grounds, bodies = [], []
            for part in range(4 if block else 2):
                entry = next(item for item in catalogue if item["house"] == base+part and item["variant"] == 0 and item["stage"] == stage)
                gx,gy = (part//2*16,part%2*16) if block else (part*16,0) if args.pair_axis == "x" else (0,part*16)
                if entry["ground_image"]:
                    dx,dy = entry["ground_sprite_offset"]
                    grounds.append((read_pam(args.source_directory / entry["ground_image"]),2*(gy-gx)+dx//4,gx+gy+dy//4))
                if entry["image"]:
                    x,y,z = entry["origin"]
                    dx,dy = entry["sprite_offset"]
                    bodies.append((read_pam(args.source_directory / entry["image"]),2*(gy+y-gx-x)+dx//4,gx+x+gy+y-z+dy//4))
            pieces = grounds+bodies
            left,top = min(x for _,x,y in pieces),min(y for _,x,y in pieces)
            right = max(x+image.width for image,x,y in pieces)
            bottom = max(y+image.height for image,x,y in pieces)
            original = Image.new("RGBA",(right-left,bottom-top))
            for image,x,y in pieces:
                original.alpha_composite(image,(x-left,y-top))
            a = original.getchannel("A").getbbox()
            if not a:
                parser.error("Complete original house block is empty")
            source_bounds = (left+a[0],top+a[1],left+a[2],top+a[3])
            original = original.crop(a)
            name = args.directory / f"model-voxel-house-block-{base}-{stage}-native"
            model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
            origin = json.loads(name.with_suffix(".json").read_text())["tile_origin"] if name.with_suffix(".json").exists() else [96,64]
            b = model.getchannel("A").getbbox()
            if not b:
                parser.error("Complete voxel house block is empty")
            model_bounds = (b[0]-origin[0],b[1]-origin[1],b[2]-origin[0],b[3]-origin[1])
            model = model.crop(b)
            common = (min(source_bounds[0],model_bounds[0]),min(source_bounds[1],model_bounds[1]),
                      max(source_bounds[2],model_bounds[2]),max(source_bounds[3],model_bounds[3]))
            pair = []
            for image,bounds in ((original,source_bounds),(model,model_bounds)):
                canvas = Image.new("RGBA",(common[2]-common[0],common[3]-common[1]))
                canvas.alpha_composite(image,(bounds[0]-common[0],bounds[1]-common[1]))
                pair.append(canvas)
            panels.append(pair)
            records.append({"stage":stage,"original_size":list(original.size),"model_size":list(model.size),
                            "original_tile_bounds":list(source_bounds),"model_tile_bounds":list(model_bounds)})
        panel_width = max(640 if block else 480,20+4*max(image.width for pair in panels for image in pair))
        panel_height = max(360,50+4*max(image.height for pair in panels for image in pair))
        sheet = Image.new("RGB",(panel_width*4,panel_height*2),(40,40,48))
        draw = ImageDraw.Draw(sheet)
        for stage,pair in enumerate(panels):
            for row,(label,image) in enumerate(zip(("source","voxel"),pair)):
                size = records[stage]["original_size" if row == 0 else "model_size"]
                draw.text((stage*panel_width+6,row*panel_height+6),f"{label} {kind} {base}, stage {stage}, {size[0]}x{size[1]}\n4x native pixels; tile-aligned",fill="white")
                panel = Image.new("RGBA",image.size,(40,40,48,255)); panel.alpha_composite(image)
                panel = panel.resize((image.width*4,image.height*4),Image.Resampling.NEAREST)
                sheet.paste(panel,(stage*panel_width+(panel_width-panel.width)//2,(row+1)*panel_height-5-panel.height))
        output = args.directory / f"house-{kind}-{base}-source-registration.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(records,indent=2)+"\n")
        print(output)
        print(json.dumps(records))
        return
    if args.buoy_comparison:
        if args.source_directory is None:
            parser.error("--buoy-comparison requires --source-directory")
        entry = next(item for item in json.loads((args.source_directory / "infrastructure.json").read_text()) if item["category"] == "buoy")
        source = read_pam(args.source_directory / entry["image"])
        name = args.directory / "model-voxel-buoy-native"
        model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
        a,b = source.getchannel("A").getbbox(),model.getchannel("A").getbbox()
        if not a or not b:
            parser.error("Buoy comparison needs visible original and model geometry")
        x,y,z = entry["origin"]
        dx,dy = 2*(y-x)+entry["offset"][0]//4,x+y-z+entry["offset"][1]//4
        original_bounds = [a[0]+dx,a[1]+dy,a[2]+dx,a[3]+dy]
        model_bounds = [b[0]-32,b[1]-32,b[2]-32,b[3]-32]
        common = [min(original_bounds[i],model_bounds[i]) if i < 2 else max(original_bounds[i],model_bounds[i]) for i in range(4)]
        sheet = Image.new("RGB",(640,320),(40,40,48)); draw = ImageDraw.Draw(sheet)
        for column,(label,image,bounds) in enumerate((("source",source.crop(a),original_bounds),("voxel",model.crop(b),model_bounds))):
            panel = Image.new("RGBA",(common[2]-common[0],common[3]-common[1]),(40,40,48,255))
            panel.alpha_composite(image,(bounds[0]-common[0],bounds[1]-common[1]))
            panel = panel.resize((panel.width*8,panel.height*8),Image.Resampling.NEAREST)
            draw.text((column*320+6,6),f"{label}: resolved buoy{entry['sprite']}, tile-aligned at8x\nbounds {bounds}",fill="white")
            sheet.paste(panel,(column*320+(320-panel.width)//2,310-panel.height))
        output = args.directory / "buoy-source-registration.png"
        report = {"original_tile_bounds":original_bounds,"model_tile_bounds":model_bounds,"original_size":[a[2]-a[0],a[3]-a[1]],"model_size":[b[2]-b[0],b[3]-b[1]]}
        sheet.save(output); output.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
        print(output); print(json.dumps(report))
        return

    if args.house_comparison is not None:
        if args.source_directory is None:
            parser.error("--house-comparison requires --source-directory")
        entries = sorted((entry for entry in json.loads((args.source_directory / "houses.json").read_text())
                          if entry["house"] == args.house_comparison and entry["variant"] == args.variant), key=lambda entry: entry["stage"])
        if [entry["stage"] for entry in entries] != list(range(4)):
            parser.error("House comparison needs four original stage records")
        records, panels = [], []
        for stage, entry in enumerate(entries):
            original, source_bounds = house_image(entry,args.source_directory)
            name = args.directory / f"model-voxel-house-{args.house_comparison}-{args.variant}-native-{stage}"
            model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
            origin = json.loads(name.with_suffix(".json").read_text())["tile_origin"] if name.with_suffix(".json").exists() else [64,96]
            bounds = model.getchannel("A").getbbox()
            if not bounds:
                if original.getchannel("A").getbbox() is not None:
                    parser.error("Native voxel house is empty despite visible original layers")
                records.append({"stage": stage, "original_size": [0,0], "model_size": [0,0],
                                "original_tile_bounds": None, "model_tile_bounds": None, "source_empty": True})
                panels.append(None)
                continue
            model_bounds = [bounds[0]-origin[0],bounds[1]-origin[1],bounds[2]-origin[0],bounds[3]-origin[1]]
            records.append({"stage":stage,"original_size":list(original.size),"model_size":[bounds[2]-bounds[0],bounds[3]-bounds[1]],
                            "original_tile_bounds":list(source_bounds),"model_tile_bounds":model_bounds})
            if args.registration:
                common = [min(source_bounds[i],model_bounds[i]) if i < 2 else max(source_bounds[i],model_bounds[i]) for i in range(4)]
                size = (common[2]-common[0],common[3]-common[1])
                registered_source,registered_model = Image.new("RGBA",size),Image.new("RGBA",size)
                registered_source.alpha_composite(original,(source_bounds[0]-common[0],source_bounds[1]-common[1]))
                registered_model.alpha_composite(model.crop(bounds),(model_bounds[0]-common[0],model_bounds[1]-common[1]))
                original, model = registered_source, registered_model
            else:
                model = model.crop(bounds)
            panels.append((original,model))
        # Tall modules/cores must not overwrite the previous row or their labels.
        # Keep native magnification and tile registration; expand only the sheet.
        images = [image for pair in panels if pair is not None for image in pair]
        panel_width = max(320,20+4*max((image.width for image in images),default=0))
        panel_height = max(360,50+4*max((image.height for image in images),default=0))
        sheet = Image.new("RGB",(panel_width*4,panel_height*2),(40,40,48))
        draw = ImageDraw.Draw(sheet)
        for stage, pair in enumerate(panels):
            if pair is None:
                for row in range(2):
                    draw.text((stage*panel_width+6,row*panel_height+6),f"{'source' if row == 0 else 'voxel'} stage {stage}: empty",fill="white")
                continue
            for row, (label,image) in enumerate(zip(("source","voxel"),pair)):
                size = records[stage]["original_size" if row == 0 else "model_size"]
                draw.text((stage*panel_width+6,row*panel_height+6),f"{label} stage {stage}, {size[0]}x{size[1]}\n4x native pixels"+("; tile-aligned" if args.registration else ""),fill="white")
                panel = Image.new("RGBA",image.size,(40,40,48,255)); panel.alpha_composite(image)
                panel = panel.resize((image.width*4,image.height*4),Image.Resampling.NEAREST)
                sheet.paste(panel,(stage*panel_width+(panel_width-panel.width)//2,(row+1)*panel_height-5-panel.height))
        label = "registration" if args.registration else "comparison"
        output = args.directory / f"house-{args.house_comparison}-{args.variant}-source-{label}.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(records,indent=2)+"\n")
        print(output)
        print(json.dumps(records))
        return

    def depot_image(entries, direction, directory):
        parts = sorted((entry for entry in entries if entry["direction"] == direction), key=lambda entry: entry["part"])
        if not parts or parts[0]["part"] != 0:
            parser.error("Depot sources require their original ground and ordered body layers")
        images = []
        for entry in parts:
            x, y, z = entry["origin"]
            dx, dy = entry["offset"]
            images.append((read_pam(directory / entry["image"]), 2*(y-x)+dx//4, x+y-z+dy//4))
        left, top = min(x for _, x, _ in images), min(y for _, _, y in images)
        right = max(x+image.width for image, x, _ in images)
        bottom = max(y+image.height for image, _, y in images)
        joined = Image.new("RGBA", (right-left, bottom-top))
        for image, x, y in images:
            joined.alpha_composite(image, (x-left, y-top))
        return joined, (left, top, right, bottom)

    def ship_depot_image(entries, axis, directory):
        joined = []
        for entry in entries:
            if entry["style"] != axis:
                continue
            entry = dict(entry)
            origin = list(entry["origin"])
            origin[axis] += 16*entry["depot_part"]
            entry["origin"] = origin
            entry["direction"] = axis
            entry["part"] = 0 if entry["part"] == 0 else entry["part"]*2+entry["depot_part"]
            joined.append(entry)
        return depot_image(joined, axis, directory)

    def dock_image(entries, direction, directory):
        dx,dy = ((-16,0),(0,16),(16,0),(0,-16))[direction]
        joined = []
        for entry in entries:
            if entry["direction"] not in (direction,4+direction%2):
                continue
            entry = dict(entry)
            water = entry["direction"] >= 4
            origin = list(entry["origin"])
            if water:
                origin[0] += dx; origin[1] += dy
            entry["origin"] = origin
            entry["direction"] = direction
            entry["part"] = 0 if entry["part"] == 0 else 1+int(water == (dx+dy > 0))
            joined.append(entry)
        return depot_image(joined,direction,directory)

    if args.dock_comparison:
        if args.source_directory is None:
            parser.error("--dock-comparison requires --source-directory")
        entries = [entry for entry in json.loads((args.source_directory / "infrastructure.json").read_text()) if entry["category"] == "dock"]
        sheet = Image.new("RGB",(960,1280),(40,40,48))
        draw, records = ImageDraw.Draw(sheet), []
        for direction in range(4):
            original,source_bounds = dock_image(entries,direction,args.source_directory)
            name = args.directory / f"model-voxel-dock-joined-native-{direction}"
            model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
            bounds = model.getchannel("A").getbbox()
            if not bounds:
                parser.error("Native joined dock is empty")
            registered = Image.new("RGBA",model.size)
            registered.alpha_composite(original,(96+source_bounds[0],80+source_bounds[1]))
            a = registered.getchannel("A").getbbox()
            common = (min(a[0],bounds[0]),min(a[1],bounds[1]),max(a[2],bounds[2]),max(a[3],bounds[3]))
            records.append({"direction":direction,"original_size":list(original.size),"model_size":[bounds[2]-bounds[0],bounds[3]-bounds[1]],
                            "original_tile_bounds":list(source_bounds),"model_tile_bounds":[bounds[0]-96,bounds[1]-80,bounds[2]-96,bounds[3]-80]})
            x,y = direction%2*480,direction//2*640
            for row,(label,image) in enumerate((("source",registered.crop(common)),("voxel",model.crop(common)))):
                draw.text((x+6,y+row*320+6),f"{label}, dock direction {direction}, both tiles\n4x native, original tile registration",fill="white")
                panel = Image.new("RGBA",image.size,(40,40,48,255)); panel.alpha_composite(image)
                panel = panel.resize((image.width*4,image.height*4),Image.Resampling.NEAREST)
                sheet.paste(panel,(x+(480-panel.width)//2,y+(row+1)*320-5-panel.height))
        output = args.directory / "docks-source-registration.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(records,indent=2)+"\n")
        print(output)
        print(json.dumps(records))
        return

    if args.dock_source:
        entries = [entry for entry in json.loads((args.directory / "infrastructure.json").read_text()) if entry["category"] == "dock"]
        sheet = Image.new("RGB",(960,640),(48,52,60))
        draw = ImageDraw.Draw(sheet)
        for layout in range(6):
            joined,bounds = depot_image(entries,layout,args.directory)
            x,y = layout%3*320,layout//3*320
            draw.text((x+6,y+6),f"Dock section {layout}, original layers\n{joined.width}x{joined.height}, bounds {bounds}, 4x",fill="white")
            joined = joined.resize((joined.width*4,joined.height*4),Image.Resampling.NEAREST)
            sheet.paste(joined,(x+(320-joined.width)//2,y+315-joined.height),joined)
        output = args.directory / "dock-sections-source.png"
        sheet.save(output)
        print(output)
        sheet = Image.new("RGB",(960,640),(48,52,60))
        draw = ImageDraw.Draw(sheet)
        for direction in range(4):
            joined,bounds = dock_image(entries,direction,args.directory)
            x,y = direction%2*480,direction//2*320
            draw.text((x+6,y+6),f"Dock direction {direction}, joined original tiles\n{joined.width}x{joined.height}, bounds {bounds}, 4x",fill="white")
            joined = joined.resize((joined.width*4,joined.height*4),Image.Resampling.NEAREST)
            sheet.paste(joined,(x+(480-joined.width)//2,y+315-joined.height),joined)
        output = args.directory / "docks-joined-source.png"
        sheet.save(output)
        print(output)
        print(json.dumps(entries))
        return

    if args.ship_depot_comparison:
        if args.source_directory is None:
            parser.error("--ship-depot-comparison requires --source-directory")
        entries = [entry for entry in json.loads((args.source_directory / "infrastructure.json").read_text()) if entry["category"] == "ship-depot"]
        sheet = Image.new("RGB",(960,640),(40,40,48))
        draw, records = ImageDraw.Draw(sheet), []
        for axis in range(2):
            original, source_bounds = ship_depot_image(entries,axis,args.source_directory)
            name = args.directory / f"model-voxel-ship-depot-native-{axis}"
            model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
            bounds = model.getchannel("A").getbbox()
            if not bounds:
                parser.error("Native ship depot is empty")
            registered = Image.new("RGBA",model.size)
            registered.alpha_composite(original,(96+source_bounds[0],80+source_bounds[1]))
            a = registered.getchannel("A").getbbox()
            common = (min(a[0],bounds[0]),min(a[1],bounds[1]),max(a[2],bounds[2]),max(a[3],bounds[3]))
            records.append({"axis":axis,"original_size":list(original.size),"model_size":[bounds[2]-bounds[0],bounds[3]-bounds[1]],
                            "original_tile_bounds":list(source_bounds),"model_tile_bounds":[bounds[0]-96,bounds[1]-80,bounds[2]-96,bounds[3]-80]})
            for row,(label,image) in enumerate((("source",registered.crop(common)),("voxel",model.crop(common)))):
                draw.text((axis*480+6,row*320+6),f"{label}, ship depot axis {axis}, both tiles\n4x native, original tile registration",fill="white")
                panel = Image.new("RGBA",image.size,(40,40,48,255)); panel.alpha_composite(image)
                panel = panel.resize((image.width*4,image.height*4),Image.Resampling.NEAREST)
                sheet.paste(panel,(axis*480+(480-panel.width)//2,(row+1)*320-5-panel.height))
        output = args.directory / "ship-depots-source-registration.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(records,indent=2)+"\n")
        print(output)
        print(json.dumps(records))
        return

    if args.ship_depot_source:
        entries = [entry for entry in json.loads((args.directory / "infrastructure.json").read_text()) if entry["category"] == "ship-depot"]
        sheet = Image.new("RGB", (960, 400), (48, 52, 60))
        draw = ImageDraw.Draw(sheet)
        for axis in range(2):
            joined, bounds = ship_depot_image(entries, axis, args.directory)
            draw.text((axis*480+6,6), f"Ship depot axis {axis}, two original tiles\n{joined.width}x{joined.height}, tile bounds {bounds}, 4x", fill="white")
            joined = joined.resize((joined.width*4,joined.height*4),Image.Resampling.NEAREST)
            sheet.paste(joined,(axis*480+(480-joined.width)//2,395-joined.height),joined)
        output = args.directory / "ship-depots-source.png"
        sheet.save(output)
        print(output)
        print(json.dumps(entries))
        return

    if args.depot_comparison is not None:
        if args.source_directory is None:
            parser.error("--depot-comparison requires --source-directory")
        entries = [entry for entry in json.loads((args.source_directory / "infrastructure.json").read_text())
                   if entry["category"] == "depot" and entry["style"] == args.depot_comparison]
        sheet = Image.new("RGB", (1280, 640), (40, 40, 48))
        draw = ImageDraw.Draw(sheet)
        records = []
        for direction in range(4):
            original, source_bounds = depot_image(entries, direction, args.source_directory)
            name = args.directory / f"model-voxel-depot-{args.depot_comparison}-native-{direction}"
            model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
            bounds = model.getchannel("A").getbbox()
            if not bounds:
                parser.error("Native voxel depot is empty")
            model_size = [bounds[2]-bounds[0], bounds[3]-bounds[1]]
            records.append({"direction": direction, "original_size": list(original.size), "model_size": model_size,
                            "original_tile_bounds": list(source_bounds), "model_tile_bounds": [bounds[0]-64,bounds[1]-80,bounds[2]-64,bounds[3]-80]})
            if args.registration:
                registered = Image.new("RGBA", model.size)
                registered.alpha_composite(original, (64+source_bounds[0],80+source_bounds[1]))
                a = registered.getchannel("A").getbbox()
                common = (min(a[0],bounds[0]),min(a[1],bounds[1]),max(a[2],bounds[2]),max(a[3],bounds[3]))
                original, model = registered.crop(common), model.crop(common)
            else:
                model = model.crop(bounds)
            for row, (label, image) in enumerate((("source",original),("voxel",model))):
                size = records[-1]["original_size" if row == 0 else "model_size"]
                draw.text((direction*320+6,row*320+6),f"{label}, exit {direction}, {size[0]}x{size[1]}\n4x native pixels"+("; tile-aligned" if args.registration else ""),fill="white")
                panel = Image.new("RGBA",image.size,(40,40,48,255))
                panel.alpha_composite(image)
                panel = panel.resize((image.width*4,image.height*4),Image.Resampling.NEAREST)
                sheet.paste(panel,(direction*320+(320-panel.width)//2,(row+1)*320-5-panel.height))
        label = "registration" if args.registration else "comparison"
        output = args.directory / f"depot-{args.depot_comparison}-source-{label}.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(records,indent=2)+"\n")
        print(output)
        print(json.dumps(records))
        return
    if args.depot_source is not None:
        entries = [entry for entry in json.loads((args.directory / "infrastructure.json").read_text())
                   if entry["category"] == "depot" and entry["style"] == args.depot_source]
        sheet = Image.new("RGB", (1280, 480), (48, 52, 60))
        draw = ImageDraw.Draw(sheet)
        for direction in range(4):
            joined, _ = depot_image(entries, direction, args.directory)
            draw.text((direction*320+6, 6), f"depot {args.depot_source}, exit {direction}\n{joined.width}x{joined.height}, original layers, 4x", fill="white")
            joined = joined.resize((joined.width*4, joined.height*4), Image.Resampling.NEAREST)
            sheet.paste(joined, (direction*320+(320-joined.width)//2, 475-joined.height), joined)
        output = args.directory / f"depot-{args.depot_source}-all-directions.png"
        sheet.save(output)
        print(output)
        print(json.dumps(entries))
        return
    if args.industry_source:
        catalogue = json.loads((args.directory / "industries.json").read_text())
        for graphics in args.industry_source:
            entries = industry_layers(sorted((entry for entry in catalogue if entry["graphics"] == graphics), key=lambda entry: entry["stage"]))
            if [entry["stage"] for entry in entries] != list(range(4)):
                parser.error(f"Industry tile {graphics} does not have four original construction records")
            images = [read_pam(args.directory / entry["image"]) if entry["image"] else None for entry in entries]
            visible = [image for image in images if image is not None]
            scale = max(1, min(8, 300 // max((image.width for image in visible), default=1), 380 // max((image.height for image in visible), default=1)))
            sheet = Image.new("RGB", (1280, 480), (48, 52, 60))
            draw = ImageDraw.Draw(sheet)
            for entry, image in zip(entries, images):
                x = entry["stage"] * 320
                draw.text((x + 6, 6), f"industry {graphics}, {entry.get('state_kind', 'construction')} {entry['stage']}\nsprite {entry['sprite']}, procedure {entry['procedure']}\n{scale}x native pixels", fill="white")
                if image is not None:
                    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
                    sheet.paste(image, (x + (320 - image.width) // 2, 475 - image.height), image)
            label = "-ground" if args.industry_ground else ""
            output = args.directory / f"industry-{graphics:03}{label}-all-states.png"
            sheet.save(output)
            print(output)
            print(json.dumps(entries))
        return
    if args.industry_effect_source is not None or args.industry_effect_comparison is not None:
        comparison = args.industry_effect_comparison is not None
        if comparison and (args.source_directory is None or args.industry_effect_source is not None):
            parser.error("Effect comparison needs --source-directory and cannot also select an effect-source sheet")
        source_directory = args.source_directory if comparison else args.directory
        graphics = args.industry_effect_comparison if comparison else args.industry_effect_source
        entries = sorted((entry for entry in json.loads((source_directory / "industry-effects.json").read_text())
                          if entry["graphics"] == graphics), key=lambda entry: entry["frame"])
        if [entry["frame"] for entry in entries] != list(range(1,7)):
            parser.error("Power-station effects need the six original spark frames")
        sheet = Image.new("RGB", (1152,1600 if comparison else 800), (40,40,48))
        draw = ImageDraw.Draw(sheet)
        previous_effect = None
        for slot, entry in enumerate(entries):
            parent = read_pam(source_directory / entry["parent_image"])
            effect = read_pam(source_directory / entry["image"])
            entry["same_image_as_previous"] = previous_effect is not None and effect.size == previous_effect.size and effect.tobytes() == previous_effect.tobytes()
            previous_effect = effect
            dx, dy = entry["child_offset"]
            dx += entry["sprite_offset"][0]//4
            dy += entry["sprite_offset"][1]//4
            left, top = min(0,dx), min(0,dy)
            right, bottom = max(parent.width,dx+effect.width), max(parent.height,dy+effect.height)
            joined = Image.new("RGBA", (right-left,bottom-top))
            joined.alpha_composite(parent,(-left,-top))
            joined.alpha_composite(effect,(dx-left,dy-top))
            panels = [("source", joined)]
            if comparison:
                name = args.directory / f"model-voxel-power-spark-native-{entry['frame']}"
                model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
                x,y,z = entry["parent_origin"]
                px,py = entry["parent_sprite_offset"]
                registered = Image.new("RGBA",model.size)
                registered.alpha_composite(joined,(64+2*(y-x)+px//4+left,80+x+y-z+py//4+top))
                a,b = registered.getchannel("A").getbbox(), model.getchannel("A").getbbox()
                if not a or not b:
                    parser.error("A registered parent/spark composite is empty")
                entry["original_tile_bounds"] = [a[0]-64,a[1]-80,a[2]-64,a[3]-80]
                entry["model_tile_bounds"] = [b[0]-64,b[1]-80,b[2]-64,b[3]-80]
                common = (min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))
                panels = [("source",registered.crop(common)),("voxel",model.crop(common))]
            for row, (label, panel) in enumerate(panels):
                x, y = slot%3*384, (slot//3*(2 if comparison else 1)+row)*400
                draw.text((x+6,y+6), f"{label} frame {entry['frame']}, sprite {entry['sprite']}\nparent-relative {entry['child_offset']}; 4x native", fill="white")
                panel = panel.resize((panel.width*4,panel.height*4),Image.Resampling.NEAREST)
                sheet.paste(panel,(x+(384-panel.width)//2,y+395-panel.height),panel)
        output = args.directory / f"industry-effects-{graphics}-{'comparison' if comparison else 'source'}.png"
        sheet.save(output)
        if comparison:
            output.with_suffix(".json").write_text(json.dumps(entries,indent=2)+"\n")
        print(output)
        print(json.dumps(entries))
        return
    if args.industry_comparison is not None:
        if args.source_directory is None:
            parser.error("--industry-comparison requires --source-directory")
        entries = industry_layers(sorted((entry for entry in json.loads((args.source_directory / "industries.json").read_text())
                                          if entry["graphics"] == args.industry_comparison), key=lambda entry: entry["stage"]))
        if [entry["stage"] for entry in entries] != list(range(4)):
            parser.error("Comparison requires all four original industry construction records")
        panel_height = max(360, 50+5*max(entry.get("sprite_size", [0,0])[1]//4 for entry in entries))
        sheet = Image.new("RGB", (1280, panel_height*2), (40, 40, 48))
        draw = ImageDraw.Draw(sheet)
        sizes = []
        for stage, entry in enumerate(entries):
            layer = "-ground" if args.industry_ground else ""
            name = args.directory / f"model-voxel-industry{layer}-{args.industry_comparison}-native-{stage}"
            original = read_pam(args.source_directory / entry["image"]) if entry["image"] else Image.new("RGBA", (1, 1))
            exported = name.with_suffix(".pam").exists() or name.with_suffix(".png").exists()
            model = (read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")) if exported else None
            if original.getchannel("A").getbbox() is None and (model is None or model.getchannel("A").getbbox() is None):
                # Some original nonzero sprite IDs are deliberately transparent.
                # Record absent exports explicitly; never invent a passing mesh.
                sizes.append({"stage": stage, "original_size": list(original.size), "model_size": [0,0],
                              "original_tile_bounds": None, "model_tile_bounds": None,
                              "source_empty": True, "model_exported": exported})
                draw.text((stage*320+6,6), f"source {entry.get('state_kind', 'state')} {stage}\noriginal body is transparent", fill="white")
                draw.text((stage*320+6,panel_height+6), "empty body export" if exported else "no body binding; source is transparent", fill="white")
                continue
            if model is None:
                parser.error(f"Native-scale industry stage {stage} is missing for a visible original source")
            bounds = model.getchannel("A").getbbox()
            if not bounds:
                parser.error(f"Native-scale industry stage {stage} has no visible geometry")
            x, y, z = entry["origin"]
            dx, dy = entry.get("sprite_offset", [0, 0])
            original_left, original_top = 2 * (y - x) + dx // 4, x + y - z + dy // 4
            visible = original.getchannel("A").getbbox()
            source_bounds = ([original_left+visible[0],original_top+visible[1],original_left+visible[2],original_top+visible[3]]
                             if visible else None)
            sizes.append({"stage": stage, "original_size": [visible[2]-visible[0],visible[3]-visible[1]] if visible else [0,0],
                          "original_carrier_size": list(original.size), "model_size": [bounds[2]-bounds[0], bounds[3]-bounds[1]],
                          "original_carrier_tile_bounds": [original_left,original_top,original_left+original.width,original_top+original.height],
                          "original_tile_bounds": source_bounds,
                          "model_tile_bounds": [bounds[0]-64, bounds[1]-80, bounds[2]-64, bounds[3]-80]})
            if args.registration:
                # The native export places the original world-tile origin at
                # (64,80). Keep sprite drawing offsets; centring independent crops
                # hides registration errors even when their dimensions agree.
                registered = Image.new("RGBA", model.size)
                registered.alpha_composite(original, (64+original_left, 80+original_top))
                source_bounds = registered.getchannel("A").getbbox() or bounds
                common = (min(bounds[0], source_bounds[0]), min(bounds[1], source_bounds[1]),
                          max(bounds[2], source_bounds[2]), max(bounds[3], source_bounds[3]))
                original, model = registered.crop(common), model.crop(common)
            else:
                if visible:
                    original = original.crop(visible)
                model = model.crop(bounds)
            for row, (label, image) in enumerate((("source", original), ("voxel", model))):
                dimensions = sizes[-1]["original_size" if label == "source" else "model_size"]
                aligned = ", tile-aligned" if args.registration else ""
                draw.text((stage * 320 + 6, row * panel_height + 6), f"{label} {entry.get('state_kind', 'state')} {stage}, {dimensions[0]}x{dimensions[1]}\n5x native pixels{aligned}", fill="white")
                panel = Image.new("RGBA", image.size, (40, 40, 48, 255))
                panel.alpha_composite(image)
                panel = panel.resize((image.width * 5, image.height * 5), Image.Resampling.NEAREST)
                sheet.paste(panel, (stage * 320 + (320 - panel.width) // 2, (row + 1) * panel_height - 5 - panel.height))
        label = "registration" if args.registration else "comparison"
        layer = "-ground" if args.industry_ground else ""
        output = args.directory / f"industry-{args.industry_comparison}{layer}-source-{label}.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(sizes, indent=2) + "\n")
        print(output)
        print(json.dumps(sizes))
        return
    if args.vehicle_comparison is not None:
        if args.source_directory is None:
            parser.error("--vehicle-comparison requires --source-directory")
        entries = sorted((entry for entry in json.loads((args.source_directory / "vehicles.json").read_text())
                          if entry["engine"] == args.vehicle_comparison and entry["loaded"] == args.loaded), key=lambda entry: entry["direction"])
        if [entry["direction"] for entry in entries] != list(range(8)):
            parser.error("Comparison requires all eight original vehicle directions")
        sizes, panels = [], []
        for direction, entry in enumerate(entries):
            name = args.directory / f"model-voxel-vehicle-{args.vehicle_comparison}-{int(args.loaded)}-native-{direction}"
            model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
            bounds = model.getchannel("A").getbbox()
            if not bounds:
                parser.error(f"Native-scale vehicle direction {direction} is empty")
            model = model.crop(bounds)
            original = read_pam(args.source_directory / entry["image"])
            sizes.append({"direction": direction, "original_size": list(original.size), "model_size": list(model.size)})
            panels.append((original,model))
        # Ships and broad aircraft exceed the old road-vehicle panel width.
        # Preserve 5x native scale without overlapping adjacent directions.
        panel_width = max(240,20+5*max(image.width for pair in panels for image in pair))
        panel_height = max(320,60+5*max(image.height for pair in panels for image in pair))
        sheet = Image.new("RGB",(panel_width*8,panel_height*2),(40,40,48))
        draw = ImageDraw.Draw(sheet)
        for direction,pair in enumerate(panels):
            for row, (label, image) in enumerate(zip(("source","voxel"),pair)):
                draw.text((direction*panel_width+6,row*panel_height+6), f"{label} dir {direction}, {image.width}x{image.height}\n5x native pixels", fill="white")
                panel = Image.new("RGBA", image.size, (40, 40, 48, 255))
                panel.alpha_composite(image)
                panel = panel.resize((image.width * 5, image.height * 5), Image.Resampling.NEAREST)
                sheet.paste(panel,(direction*panel_width+(panel_width-panel.width)//2,row*panel_height+40+(panel_height-40-panel.height)//2))
        output = args.directory / f"vehicle-{args.vehicle_comparison}-{int(args.loaded)}-source-comparison.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(sizes, indent=2) + "\n")
        print(output)
        print(json.dumps(sizes))
        return
    if args.tree_comparison is not None:
        if args.source_directory is None:
            parser.error("--tree-comparison requires --source-directory")
        entries = sorted((entry for entry in json.loads((args.source_directory / "trees.json").read_text())
                          if entry["base"] == args.tree_comparison and entry["palette"] == 0), key=lambda entry: entry["stage"])
        if [entry["stage"] for entry in entries] != list(range(7)):
            parser.error("Comparison requires all seven original unmodified-palette stages")
        sizes = []
        panels = []
        for stage, entry in enumerate(entries):
            name = args.directory / f"model-voxel-tree-{args.tree_comparison}-native-{stage}"
            model = read_pam(name.with_suffix(".pam")) if name.with_suffix(".pam").exists() else Image.open(name.with_suffix(".png")).convert("RGBA")
            # New native views retain an object-ID-derived alpha mask, including
            # genuinely black leaf/branch pixels. Older exports were opaque black.
            # This is review framing, never geometry generation.
            alpha = model.getchannel("A")
            bounds = alpha.getbbox() if alpha.getextrema()[0] < 255 else model.convert("RGB").getbbox()
            if not bounds:
                parser.error(f"Native-scale tree stage {stage} has no visible geometry")
            model = model.crop(bounds)
            original = read_pam(args.source_directory / entry["image"])
            sizes.append({"stage": stage, "original_size": list(original.size), "model_size": list(model.size)})
            panels.append((original, model))
        panel_width = max(240, 20+5*max(image.width for pair in panels for image in pair))
        panel_height = max(320, 45+5*max(image.height for pair in panels for image in pair))
        sheet = Image.new("RGB", (7*panel_width, 2*panel_height), (40, 40, 48))
        draw = ImageDraw.Draw(sheet)
        for stage, (original, model) in enumerate(panels):
            for row, (label, image) in enumerate((("source", original), ("voxel", model))):
                draw.text((stage * panel_width + 6, row * panel_height + 6), f"{label} stage {stage}, {image.width}x{image.height}\n5x native pixels", fill="white")
                panel = Image.new("RGBA", image.size, (40, 40, 48, 255))
                panel.alpha_composite(image)
                panel = panel.resize((image.width * 5, image.height * 5), Image.Resampling.NEAREST)
                sheet.paste(panel, (stage * panel_width + (panel_width - panel.width) // 2, (row + 1) * panel_height - 5 - panel.height))
        output = args.directory / f"tree-{args.tree_comparison}-source-comparison.png"
        sheet.save(output)
        output.with_suffix(".json").write_text(json.dumps(sizes, indent=2) + "\n")
        print(output)
        print(json.dumps(sizes))
        return
    if args.tree_source:
        catalogue = json.loads((args.directory / "trees.json").read_text())
        for base in args.tree_source:
            entries = sorted((entry for entry in catalogue if entry["base"] == base), key=lambda entry: (entry["palette"], entry["stage"]))
            palettes = sorted({entry["palette"] for entry in entries})
            if not palettes or any([entry["stage"] for entry in entries if entry["palette"] == palette] != list(range(7)) for palette in palettes):
                parser.error(f"Tree {base} does not have seven original stages for each palette")
            images = [read_pam(args.directory / entry["image"]) for entry in entries]
            scale = max(1, min(8, 230 // max(image.width for image in images), 270 // max(image.height for image in images)))
            sheet = Image.new("RGB", (1680, len(palettes) * 320), (48, 52, 60))
            draw = ImageDraw.Draw(sheet)
            for entry, image in zip(entries, images):
                x, y = entry["stage"] * 240, palettes.index(entry["palette"]) * 320
                draw.text((x + 6, y + 6), f"tree {base}, stage {entry['stage']}\npalette {entry['palette']}, {image.width}x{image.height}, {scale}x", fill="white")
                image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
                sheet.paste(image, (x + (240 - image.width) // 2, y + 315 - image.height), image)
            output = args.directory / f"tree-{base}-all-stages.png"
            sheet.save(output)
            print(output)
            print(json.dumps(entries))
        return
    if args.vehicle_source:
        catalogue = json.loads((args.directory / "vehicles.json").read_text())
        for engine in args.vehicle_source:
            entries = sorted((entry for entry in catalogue if entry["engine"] == engine), key=lambda entry: (entry["loaded"], entry["direction"]))
            if len(entries) != 16:
                parser.error(f"Vehicle {engine} does not have 16 original direction/state records in this climate")
            sheet = Image.new("RGB", (1280, 1120), (48, 52, 60))
            draw = ImageDraw.Draw(sheet)
            for slot, entry in enumerate(entries):
                x, y = slot%4*320, slot//4*280
                draw.text((x+6, y+6), f"{engine}: {entry['name']}\ndir {entry['direction']}, {'loaded' if entry['loaded'] else 'empty'}, sprite {entry['sprite']}", fill="white")
                image = read_pam(args.directory / entry["image"])
                scale = max(1, min(12, 300//image.width, 225//image.height))
                image = image.resize((image.width*scale, image.height*scale), Image.Resampling.NEAREST)
                sheet.paste(image, (x+(320-image.width)//2, y+50+(225-image.height)//2), image)
            output = args.directory / f"vehicle-{engine:03}-all-states.png"
            sheet.save(output)
            print(output)
            print(json.dumps(entries))
        return
    if args.house_pair or args.house_block:
        catalogue = json.loads((args.directory / "houses.json").read_text())
        houses = args.house_block or args.house_pair
        panel_width = 640 if args.house_block else 320
        sheet = Image.new("RGB", (panel_width*4, 480), (48, 52, 60))
        draw = ImageDraw.Draw(sheet)
        for stage in range(4):
            grounds, bodies = [], []
            for slot, house in enumerate(houses):
                entry = next(item for item in catalogue if item["house"] == house and item["variant"] == args.variant and item["stage"] == stage)
                gx, gy = (slot//2*16,slot%2*16) if args.house_block else (slot*16,0) if args.pair_axis == "x" else (0,slot*16)
                if entry.get("ground_image"):
                    dx,dy = entry["ground_sprite_offset"]
                    grounds.append((read_pam(args.directory / entry["ground_image"]),2*(gy-gx)+dx//4,gx+gy+dy//4))
                if entry["image"]:
                    x,y,z = entry["origin"]
                    dx,dy = entry["sprite_offset"]
                    bodies.append((read_pam(args.directory / entry["image"]),2*(gy+y-gx-x)+dx//4,gx+x+gy+y-z+dy//4))
            pieces = grounds+bodies
            if not pieces:
                parser.error("Joined source house has no ground or body layers")
            left, top = min(x for _, x, _ in pieces), min(y for _, _, y in pieces)
            right = max(x+image.width for image, x, _ in pieces)
            bottom = max(y+image.height for image, _, y in pieces)
            joined = Image.new("RGBA", (right-left, bottom-top))
            for image, x, y in pieces:
                joined.alpha_composite(image, (x-left, y-top))
            scale = max(1, min(8, (panel_width-16)//joined.width, 410//joined.height))
            joined = joined.resize((joined.width*scale, joined.height*scale), Image.Resampling.NEAREST)
            sheet.paste(joined, (stage*panel_width+(panel_width-joined.width)//2, 55+(410-joined.height)//2), joined)
            layout = "north/east/west/south" if args.house_block else f"axis {args.pair_axis}"
            draw.text((stage*panel_width+8, 8), f"houses {houses}, {layout}\nvariant {args.variant}, stage {stage}, {scale}x native", fill="white")
        kind = "block" if args.house_block else "pair"
        output = args.directory / (f"house-{kind}-"+"-".join(f"{house:03}" for house in houses)+f"-{args.variant}.png")
        sheet.save(output)
        print(output)
        return
    if args.house_source:
        catalogue = json.loads((args.directory / "houses.json").read_text())
        for house in args.house_source:
            entries = [entry for entry in catalogue if entry["house"] == house]
            if len(entries) != 16:
                parser.error(f"House {house} does not have 16 original variant/stage records")
            sheet = Image.new("RGB", (1280, 1440), (48, 52, 60))
            draw = ImageDraw.Draw(sheet)
            for entry in entries:
                x, y = entry["stage"]*320, entry["variant"]*360
                draw.text((x+6,y+5), f"house {house}: {entry['name']}\nvariant {entry['variant']} stage {entry['stage']}\nsprite {entry['sprite']} palette {entry['palette']}", fill="white")
                if entry["image"] or (args.house_layers and entry.get("ground_image")):
                    if args.house_layers:
                        image, _ = house_image(entry,args.directory)
                    else:
                        image = read_pam(args.directory / entry["image"])
                    scale = max(1, min(12, 300//image.width, 295//image.height))
                    image = image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
                    sheet.paste(image,(x+(320-image.width)//2,y+60+(295-image.height)//2),image)
            suffix = "-layers" if args.house_layers else ""
            output = args.directory / f"house-{house:03}-all-states{suffix}.png"
            sheet.save(output)
            print(output)
            print(json.dumps([{key: entry[key] for key in ("house", "variant", "stage", "sprite", "palette", "origin", "extent", "sprite_offset", "sprite_size", "ground_sprite") if key in entry} for entry in entries]))
        return
    if args.animation_prefix:
        prefix = f"model-voxel-{args.animation_prefix}*-{args.animation_view}"
        images = {}
        for path in args.directory.glob(prefix + ".png"):
            with Image.open(path) as source:
                if "opentt3d_pam_header" in source.info:
                    images[path.stem] = path
        images.update({path.stem: path for path in args.directory.glob(prefix + ".pam")})
        if not images:
            parser.error("No matching exported animation frames")
        columns = min(6, len(images))
        sheet = Image.new("RGB", (columns*320, ((len(images)+columns-1)//columns)*320), (40,40,48))
        draw = ImageDraw.Draw(sheet)
        for index, (name,path) in enumerate(sorted(images.items())):
            if path.suffix == ".pam":
                image = read_pam(path)
            else:
                with Image.open(path) as source:
                    image = source.convert("RGBA")
            if args.animation_view < 4 and (bounds := image.convert("RGB").getbbox()):
                image = image.crop(bounds)
            scale = min(300/image.width, 280/image.height)
            image = image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.NEAREST)
            x, y = index%columns*320, index//columns*320
            draw.text((x+5,y+5), name.removeprefix("model-voxel-"), fill="white")
            sheet.paste(image,(x+(320-image.width)//2,y+30+(280-image.height)//2),image)
        output = args.directory / f"voxel-{args.animation_prefix}-animation-v{args.animation_view}.png"
        sheet.save(output)
        print(output)
        return
    if args.preview:
        image = read_pam(args.directory) if args.directory.suffix.lower() == ".pam" else Image.open(args.directory)
        with image:
            print(f"Source dimensions: {image.size}; visible bounds: {image.convert('RGBA').getchannel('A').getbbox()}")
            if args.palette_counts:
                from palette_reference import colours as palette_colours
                palette = palette_colours()
                counts = image.convert("RGBA").getcolors(image.width * image.height)
                print(json.dumps([{"pixels": count, "rgba": list(rgba),
                                   "indices": [i for i, rgb in enumerate(palette) if i and rgb == rgba[:3]]}
                                  for count, rgba in sorted(counts, reverse=True) if rgba[3]]))
            if args.sample:
                print(f"Source RGBA at {tuple(args.sample)}: {image.convert('RGBA').getpixel(tuple(args.sample))}")
            if args.colours:
                rgba = image.convert("RGBA")
                seen = set()
                left, top, right, bottom = args.colours
                for y in range(max(0, top), min(image.height, bottom)):
                    for x in range(max(0, left), min(image.width, right)):
                        colour = rgba.getpixel((x, y))
                        if colour[3] and colour not in seen:
                            if len(seen) < 32:
                                from palette_reference import colours as palette_colours
                                indices = [i for i, rgb in enumerate(palette_colours()) if rgb == colour[:3]]
                                print(f"Source colour at {(x, y)}: {colour}; DOS palette {indices}")
                            seen.add(colour)
            if args.preview_scale > 1:
                image = image.resize((image.width * args.preview_scale, image.height * args.preview_scale), Image.Resampling.NEAREST)
            image.thumbnail((2000, 1200), Image.Resampling.NEAREST)
            name = args.directory.with_name(args.directory.stem + "-preview.png")
            image.save(name)
            print(name)
        return
    if args.gallery:
        prefix = f"model-{args.gallery_kind}-*" if args.gallery_kind else "model-*"
        if args.gallery_model is not None:
            prefix = f"model-{args.gallery_model:03}-*"
        if args.voxel_model:
            prefix = f"model-voxel-{args.voxel_model}-" + ("[4-7]" if args.street else "[0-3]")
        if args.fence_style is not None:
            layout = f"layout-{args.fence_layout}-" if args.fence_layout is not None else ""
            prefix = f"model-fence-{args.fence_style}-{layout}" + ("[4-7]" if args.street else "[0-3]")
        if args.foundation is not None:
            slope = f"slope-{args.foundation_slope}-" if args.foundation_slope is not None else "slope-*-"
            prefix = f"model-foundation-{args.foundation}-{slope}" + ("context-" if args.foundation_context else "") + ("[4-7]" if args.street else "[0-3]")
        if args.ground_detail:
            prefix = "model-ground-detail-" + "-".join(map(str, args.ground_detail)) + "-[0-3]"
        images_by_name = {}
        for path in args.directory.glob(prefix + ".png"):
            with Image.open(path) as image:
                if "opentt3d_pam_header" in image.info:
                    images_by_name[path.stem] = path
        # A fresh renderer export takes precedence over an older compacted copy.
        images_by_name.update({path.stem: path for path in args.directory.glob(prefix + ".pam")})
        images = [images_by_name[name] for name in sorted(images_by_name)]
        if args.foundation is not None and len(images) > 4:
            parser.error("Multiple foundation slopes match; select --foundation-slope")
        if len(images) < 4:
            parser.error("A gallery needs four exported model views")
        sheet=Image.new("RGB",(1280,1280),(40,40,48))
        for i,path in enumerate(images[:4]):
            if path.suffix == ".pam":
                image = read_pam(path)
            else:
                with Image.open(path) as source:
                    image = source.convert("RGBA")
            if args.tight:
                bounds = image.convert("RGB").getbbox()
                if bounds:
                    image = image.crop(bounds)
                    scale = min(590 / image.width, 590 / image.height)
                    image = image.resize((max(1, round(image.width*scale)), max(1, round(image.height*scale))), Image.Resampling.NEAREST)
            sheet.paste(image,((i%2)*640+(640-image.width)//2,(i//2)*640+(640-image.height)//2),image)
        label = f"{args.gallery_model}-" if args.gallery_model is not None else args.gallery_kind+"-" if args.gallery_kind else ""
        if args.ground_detail:
            label = "ground-detail-" + "-".join(map(str, args.ground_detail)) + "-"
        if args.voxel_model:
            label = "voxel-" + args.voxel_model + ("-street-" if args.street else "-")
        if args.fence_style is not None:
            layout = f"layout-{args.fence_layout}-" if args.fence_layout is not None else ""
            label = f"fence-{args.fence_style}-{layout}" + ("street-" if args.street else "")
        if args.foundation is not None:
            slope = f"slope-{args.foundation_slope}-" if args.foundation_slope is not None else ""
            label = f"foundation-{args.foundation}-{slope}" + ("context-" if args.foundation_context else "") + ("street-" if args.street else "")
        name=args.directory/(label + ("gallery-tight.png" if args.tight else "gallery.png"))
        sheet.save(name)
        print(name)
        return
    if args.terrain or args.rail_details or args.infrastructure:
        category = "infrastructure" if args.infrastructure else "rail-details" if args.rail_details else "terrain-details"
        entries = json.loads((args.directory / (category + ".json")).read_text())
        if args.categories:
            entries = [entry for entry in entries if entry["category"] in args.categories]
            if not entries:
                parser.error("No source records match the requested categories")
        if args.styles:
            entries = [entry for entry in entries if entry["style"] in args.styles]
            if not entries:
                parser.error("No source records match the requested styles")
        for start in range(0, len(entries), 36):
            sheet = Image.new("RGB", (1440, 1080), (64, 68, 76))
            draw = ImageDraw.Draw(sheet)
            for index, entry in enumerate(entries[start:start + 36]):
                x, y = (index % 6) * 240, (index // 6) * 180
                frame = f" frame {entry['frame']}" if "frame" in entry else ""
                draw.text((x + 4, y + 4), f"{entry['category']} {entry['style']} / {entry['variant']}{frame}\nsprite {entry['sprite']}", fill="white")
                image = read_pam(args.directory / entry["image"])
                image.thumbnail((230, 144), Image.Resampling.NEAREST)
                sheet.paste(image, (x + (240 - image.width) // 2, y + 177 - image.height), image)
            label = "-".join(args.categories) + "-" if args.categories else ""
            if args.styles:
                label += "-".join(map(str,args.styles)) + "-"
            name = args.directory / f"{category}-{label}{start:03}.png"
            sheet.save(name)
            print(name)
        return
    if args.stations:
        entries = json.loads((args.directory / "stations.json").read_text())
        for start in range(0, len(entries), 24):
            sheet = Image.new("RGB", (1440, 1120), (64, 68, 76))
            draw = ImageDraw.Draw(sheet)
            for index, entry in enumerate(entries[start:start + 24]):
                x, y = (index % 6) * 240, (index // 6) * 280
                draw.text((x + 4, y + 4), f"rail {entry['railtype']} layout {entry['layout']} part {entry['part']}\nsprite {entry['sprite']}", fill="white")
                image = read_pam(args.directory / entry["image"])
                image.thumbnail((230, 240), Image.Resampling.NEAREST)
                sheet.paste(image, (x + (240 - image.width) // 2, y + 277 - image.height), image)
            name = args.directory / f"stations-{start:03}.png"
            sheet.save(name)
            print(name)
        return
    if args.vehicles:
        entries = [entry for entry in json.loads((args.directory / "vehicles.json").read_text())
                   if entry["direction"] == args.direction and entry["loaded"] == args.loaded and
                   (not args.engine_range or args.engine_range[0] <= entry["engine"] <= args.engine_range[1])]
        for start in range(0, len(entries), 48):
            sheet = Image.new("RGB", (1600, 960), (64, 68, 76))
            draw = ImageDraw.Draw(sheet)
            for slot, entry in enumerate(entries[start:start + 48]):
                x, y = (slot % 8) * 200, (slot // 8) * 160
                draw.text((x + 4, y + 4), f"{entry['engine']:03} {entry['name'][:26]}", fill="white")
                image = read_pam(args.directory / entry["image"])
                if args.preview_scale > 1:
                    scale = min(args.preview_scale,190//image.width,128//image.height)
                    image = image.resize((image.width*max(1,scale),image.height*max(1,scale)),Image.Resampling.NEAREST)
                image.thumbnail((190, 128), Image.Resampling.NEAREST)
                sheet.paste(image, (x + (200 - image.width) // 2, y + 156 - image.height), image)
            selection = f"{args.engine_range[0]}-{args.engine_range[1]}-" if args.engine_range else ""
            name = args.directory / f"vehicles-{selection}{start:03}-d{args.direction}-{'loaded' if args.loaded else 'empty'}.png"
            sheet.save(name)
            print(name)
        return
    if args.industries:
        entries = [entry for entry in json.loads((args.directory / "industries.json").read_text()) if entry["stage"] == args.stage]
        for start in range(0, len(entries), 24):
            sheet = Image.new("RGB", (1200, 1200), (64, 68, 76))
            draw = ImageDraw.Draw(sheet)
            for slot, entry in enumerate(entries[start:start + 24]):
                x, y = (slot % 6) * 200, (slot // 6) * 300
                draw.text((x + 4, y + 4), f"gfx {entry['graphics']} / sprite {entry['sprite']}\nprocedure {entry['procedure']}", fill="white")
                if entry["image"]:
                    image = read_pam(args.directory / entry["image"])
                    image.thumbnail((190, 256), Image.Resampling.NEAREST)
                    sheet.paste(image, (x + (200 - image.width) // 2, y + 295 - image.height), image)
            name = args.directory / f"industries-{start:03}-s{args.stage}.png"
            sheet.save(name)
            print(name)
        return
    if args.bridges is not None:
        entries = [entry for entry in json.loads((args.directory / "bridges.json").read_text())
                   if entry["type"] == args.bridges and entry["slot"] < 8]
        sheet = Image.new("RGB", (1600, 7 * 160), (64, 68, 76))
        draw = ImageDraw.Draw(sheet)
        for entry in entries:
            x, y = entry["slot"] * 200, entry["piece"] * 160
            draw.text((x + 4, y + 4), f"piece {entry['piece']} slot {entry['slot']}\n{entry['sprite']} pal {entry['palette']}", fill="white")
            image = read_pam(args.directory / entry["image"])
            image.thumbnail((192, 124), Image.Resampling.NEAREST)
            sheet.paste(image, (x + (200 - image.width) // 2, y + 157 - image.height), image)
        name = args.directory / f"bridges-{args.bridges:02}.png"
        sheet.save(name)
        print(name)
        return
    if args.trees:
        entries=[m for m in json.loads((args.directory/"trees.json").read_text()) if m["stage"]==args.stage]
        for start in range(0,len(entries),48):
            sheet=Image.new("RGB",(1200,1200),(64,68,76))
            draw=ImageDraw.Draw(sheet)
            for slot,entry in enumerate(entries[start:start+48]):
                x,y=(slot%8)*150,(slot//8)*200
                draw.text((x+4,y+4),f"{entry['base']} pal {entry['palette']}",fill="white")
                image=read_pam(args.directory/entry["image"])
                image.thumbnail((140,170),Image.Resampling.NEAREST)
                sheet.paste(image,(x+(150-image.width)//2,y+195-image.height),image)
            name=args.directory/f"trees-{start:03}-s{args.stage}.png"
            sheet.save(name)
            print(name)
        return
    models = [m for m in json.loads((args.directory / "houses.json").read_text()) if m["variant"] == args.variant and m["stage"] == args.stage]
    for start in range(0, len(models), 24):
        sheet = Image.new("RGB", (1200, 1200), (64, 68, 76))
        draw = ImageDraw.Draw(sheet)
        for slot, entry in enumerate(models[start:start + 24]):
            x, y = (slot % 6) * 200, (slot // 6) * 300
            draw.text((x + 5, y + 5), f"{entry['house']:03}  {entry['sprite']}\n{entry['name']}", fill="white")
            if entry["image"]:
                image = read_pam(args.directory / entry["image"])
                image.thumbnail((190, 256), Image.Resampling.NEAREST)
                sheet.paste(image, (x + (200 - image.width) // 2, y + 295 - image.height), image)
        name = args.directory / f"houses-{start:03}-v{args.variant}-s{args.stage}.png"
        sheet.save(name)
        print(name)


if __name__ == "__main__":
    main()

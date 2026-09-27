import json
import math
from pathlib import Path
import re
import unittest
from compile_voxels import compile_catalogue
from compile_vehicles import definitions as vehicle_definitions


class VoxelCompilerTests(unittest.TestCase):
    def test_gold_layout_preserves_empty_bodies_cross_owner_channels_roofs_and_wheel_poses(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("gold_") or name in ("mine_ground_site","mine_ground_bare")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in range(72,89)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",(root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0])
        empty = 0
        for graphics in range(72,89):
            for stage in range(4):
                fields = rows[graphics*4+stage].split(",")
                body = result["bindings"]["industries"].get(str(graphics),{}).get(str(stage))
                self.assertEqual(bool(body),int(fields[2],0) != 0,"An intentionally empty source body must stay empty")
                empty += not body
                self.assertIn(str(stage),result["bindings"]["industry_ground"][str(graphics)])
            if graphics < 88:
                self.assertEqual(rows[graphics*4+1],rows[graphics*4+2])
                for bindings in result["bindings"].values():
                    self.assertEqual(bindings.get(str(graphics),{}).get("1"),bindings.get(str(graphics),{}).get("2"))
        self.assertEqual(empty,54)
        self.assertEqual(result["bindings"]["industries"]["79"]["3"],result["bindings"]["industries"]["88"]["0"])
        self.assertEqual(set(result["bindings"]["industry_ground"]["88"].values()),{result["bindings"]["industry_ground"]["79"]["3"]})
        for graphics in (72,74,75):
            body = result["models"][f"gold_{graphics}_middle"]
            underlay = result["models"]["gold_bare_underlay"]
            self.assertEqual(underlay["origin"][2]+underlay["cell_size"][2],body["origin"][2],"Independent2022 soil touches the body-owned substrate without coincident top faces")
        for stage in range(4):
            joined = set()
            for graphics in range(72,88):
                for bindings in result["bindings"].values():
                    name = bindings.get(str(graphics),{}).get(str(stage))
                    if not name or name == "gold_bare_underlay": continue
                    model = result["models"][name]
                    offset = ((graphics-72)//4*32+round(model["origin"][0]*2),(graphics-72)%4*32+round(model["origin"][1]*2),round(model["origin"][2]*2))
                    placed = {(x+offset[0],y+offset[1],z+offset[2]) for x,y,z in volumes[name]}
                    self.assertFalse(joined & placed,(stage,graphics,"Cross-owner roofs, stays, fences and floors need exclusive occupancy"))
                    joined |= placed
            self.assertTrue(all(0 <= x < 128 and 0 <= y < 128 for x,y,z in joined))
            reached = {p for p in joined if p[2] <= 0}; pending = list(reached)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in joined and point not in reached:
                        reached.add(point); pending.append(point)
            self.assertEqual(reached,joined,"Even cross-owner roof cuts and descending troughs need physical support")
        for stage in ("middle","finished"):
            for x in (8,12,16):
                for name,y in ((f"gold_73_{stage}",31),(f"gold_74_{stage}",0)):
                    self.assertIn((x,y,25),volumes[name]); self.assertIn((x+2,y,25),volumes[name])
                    self.assertNotIn((x+1,y,25),volumes[name],"Three independently open troughs continue across the73/74 owner boundary")
        self.assertNotIn((15,15,34),volumes["gold_72_middle"],"The middle-stage works has an open roof")
        self.assertNotIn((12,27,12),volumes["gold_86_middle"],"The front workshop remains roofless during construction")
        for point,back in (((5,19,23),(5,18,23)),((16,19,8),(16,18,8))):
            self.assertNotIn(point,volumes["gold_75_finished"],"The defining upper/lower windows face the original visible facade")
            self.assertIn(back,volumes["gold_75_finished"])
        for graphics in (82,85,86):
            for stage in ("initial","middle","finished"):
                colours = {c for material in volumes[f"gold_{graphics}_{stage}"].values() for c in result["materials"][material-1]}
                self.assertEqual(bool(colours & set(range(245,250))),stage == "finished","Original animated pool water first appears on completion")
        poses = [volumes[f"gold_hoist_{pose:02d}"] for pose in range(3)]
        self.assertEqual(len({frozenset(p.items()) for p in poses}),3)
        self.assertEqual({p:m for p,m in poses[0].items() if p[2] < 60},{p:m for p,m in poses[1].items() if p[2] < 60})
        for pose in poses:
            self.assertNotIn((24,15,40),pose,"The winding tower is an open frame")

    def test_copper_hoist_poses_open_construction_bays_and_flues_keep_source_ownership(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("copper_") or name in ("mine_ground_site","mine_ground_bare","print_site_ground")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in range(47,52)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",(root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0])
        for graphics in range(47,52):
            states = result["bindings"]["industries"][str(graphics)]
            self.assertEqual(set(states),{"0","1","2","3"})
            self.assertEqual(states["2"],states["3"])
            self.assertEqual(rows[graphics*4+2].split(",")[2:],rows[graphics*4+3].split(",")[2:],"The last two slots must reference the same original body, independently of their ground")
            for stage,name in states.items():
                ground = result["models"][result["bindings"]["industry_ground"][str(graphics)][stage]]
                self.assertEqual(ground["origin"][2]+ground["cell_size"][2],0,"Independent ground ends where the building starts")
                self.assertEqual(result["models"][name]["origin"][2],0)
        self.assertEqual(result["bindings"]["industries"]["47"]["3"],result["bindings"]["industries"]["48"]["0"])
        poses = [volumes[f"copper_head_{i:02d}"] for i in range(3)]
        self.assertEqual(len({frozenset(cells.items()) for cells in poses}),3,"All three original wheel poses need distinct spokes")
        changed = {p for p in set().union(*poses) if len({cells.get(p) for cells in poses})>1}
        self.assertTrue(changed)
        self.assertTrue(all(9 <= x <= 21 and y == 14 and 37 <= z <= 49 for x,y,z in changed),"Animation changes the wheel only, never its supports or ground")
        for name,cells in volumes.items():
            if not name.startswith("copper_"): continue
            reached = {p for p in cells if p[2]==0}
            pending = list(reached)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in cells and point not in reached:
                        reached.add(point); pending.append(point)
            self.assertEqual(reached,set(cells),(name,"Wheel rims, stays, chimneys and roof bays need physical support"))
        for cells in poses:
            self.assertNotIn((15,9,22),cells,"The winding tower is open between its braced columns")
            self.assertNotIn((15,15,37),cells,"The wheel face must clear the supporting tower instead of being buried inside it")
        for point in ((10,6,33),(10,12,31)):
            self.assertNotIn(point,volumes["copper_engine_finished"],"Both chimney mouths remain open")
        for name,opening,back in (("copper_machine_finished",(21,15,4),(20,15,4)),
                                  ("copper_machine_finished",(10,21,11),(10,20,11)),
                                  ("copper_engine_finished",(11,17,5),(11,16,5))):
            self.assertNotIn(opening,volumes[name],"Machine bays and glazing are recessed openings")
            self.assertIn(back,volumes[name])
        self.assertNotIn((6,10,6),volumes["copper_sheds_partial"],"Construction sheds cannot have solid top caps")
        self.assertIn((9,10,6),volumes["copper_sheds_partial"])
        for stage in ("initial","partial","finished"):
            self.assertFalse(any(10 <= x < 20 for x,y,z in volumes[f"copper_sheds_{stage}"]),"The passage between storage rows stays unbuilt")

    def test_iron_ore_layout_keeps_ground_owned_roofs_supported_and_original_bodies_empty(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        for graphics in range(100,116):
            self.assertNotIn(str(graphics),source["bindings"]["industries"],"Every original iron-ore body is intentionally empty")
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("ore_")}
        source["bindings"] = {"industry_ground":{key:value for key,value in source["bindings"]["industry_ground"].items() if int(key) in range(100,116)}}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",(root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0])
        for graphics in range(100,116):
            states = result["bindings"]["industry_ground"][str(graphics)]
            self.assertEqual(set(states),{"0","1","2","3"})
            self.assertEqual(states["1"],states["2"])
            self.assertEqual(len(set(states.values())),3)
            self.assertEqual(rows[graphics*4+1],rows[graphics*4+2],"Only the original middle construction states may alias")
            for stage in range(4):
                fields = rows[graphics*4+stage].split(",")
                self.assertEqual(int(fields[2],0),0)
                self.assertEqual(int(fields[0],0),2293+graphics-100+(0,16,16,32)[stage])
                model = result["models"][states[str(stage)]]
                self.assertEqual(model["cell_size"],[0.5,0.5,0.5])
                self.assertEqual(model["origin"],[0,0,-0.5])
                cells = volumes[states[str(stage)]]
                self.assertEqual({(x,y) for x,y,z in cells if z == 0},{(x,y) for x in range(32) for y in range(32)},"Each owner covers exactly its original ground tile")
        for stage in range(4):
            joined = set()
            for graphics in range(100,116):
                name = result["bindings"]["industry_ground"][str(graphics)][str(stage)]
                offset_x,offset_y = (graphics-100)//4*32,(graphics-100)%4*32
                placed = {(x+offset_x,y+offset_y,z) for x,y,z in volumes[name]}
                self.assertFalse(joined & placed,(graphics,stage,"Roof, wall and ground ownership must remain exclusive"))
                joined |= placed
            self.assertTrue(all(0 <= x < 128 and 0 <= y < 128 for x,y,z in joined),"The joined industry stays inside its original four-by-four footprint")
            reached = {point for point in joined if point[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in joined and point not in reached:
                        reached.add(point); pending.append(point)
            self.assertEqual(reached,joined,(stage,"Cross-owner hall/works roofs, open trusses and raised hopper need physical support"))
            entrance = volumes[result["bindings"]["industry_ground"]["115"][str(stage)]]
            self.assertEqual(max(z for x,y,z in entrance),0,"The source entrance remains unbuilt through all stages")
        for name,opening,back in (("ore_111_finished",(15,6,20),(14,6,20)),("ore_114_finished",(27,12,20),(26,12,20))):
            self.assertNotIn(opening,volumes[name],"Windows are recessed apertures, not face paint")
            self.assertIn(back,volumes[name],"The glazing/recess remains behind the window rim")

    def test_steel_mill_layers_keep_open_furnace_flues_roof_joins_and_empty_stock_body(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("steel_") or name in ("mine_ground_site","mine_ground_bare")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in range(52,58)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        for name,model in result["models"].items():
            if name.startswith("steel_"):
                self.assertEqual(model["cell_size"],[0.5,0.5,0.5],"The source-sized structures must not inherit the compiler's one-unit vertical default")
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",(root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0])
        self.assertEqual(set(result["bindings"]["industries"]["55"]),{"0"},"The stock yard has no body after its initial foundation mark")
        for graphics in range(52,58):
            self.assertEqual(rows[graphics*4+1],rows[graphics*4+2],"Only source-identical construction stages may share a model")
            for category in ("industries","industry_ground"):
                states = result["bindings"][category][str(graphics)]
                if "1" in states:
                    self.assertEqual(states["1"],states["2"])
                    self.assertEqual(len(set(states.values())),3)
            for stage in range(4):
                name = result["bindings"]["industries"][str(graphics)].get(str(stage))
                body = set(volumes[name]) if name else set()
                name = result["bindings"]["industry_ground"][str(graphics)][str(stage)]
                ground = {(x,y,z-1) for x,y,z in volumes[name]}
                self.assertFalse(body & ground,(graphics,stage,"Ground/body ownership must be exclusive"))
                self.assertEqual({(x,y) for x,y,z in ground if z == -1},{(x,y) for x in range(32) for y in range(32)})
                joined = body | ground
                reached = {p for p in joined if p[2] == -1}
                pending = list(reached)
                for x,y,z in pending:
                    for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                        if p in joined and p not in reached:
                            reached.add(p); pending.append(p)
                self.assertEqual(reached,joined,(graphics,stage,"Frames, roof bays, chimneys and furnace parts need physical support"))
                colours = {c for material in volumes[name].values() for c in result["materials"][material-1]}
                self.assertEqual(bool(colours & set(range(232,241))),stage == 3,"Molten metal uses the original cycling fire palette only in completed grounds")
        self.assertTrue(all(y >= 13 for x,y,z in volumes["steel_casting_finished"]),
                        "The small raised casting-roof corner must not cover the open northern apron")
        self.assertEqual(min(z for x,y,z in volumes["steel_north_partial"]),12,
                         "The lower support columns belong to the independent ground layer")
        for name,flues in {"north":((6,22,57),(22,6,57),(6,6,47)),"casting":((12,16,91),),
                           "rolling":((24,9,41),),"service":((8,6,53),(24,6,59))}.items():
            for point in flues:
                self.assertNotIn(point,volumes[f"steel_{name}_finished"],"A completed flue must remain hollow through its top")
        for name in ("steel_boiler_ground_partial","steel_boiler_ground"):
            self.assertNotIn((26,16,14),volumes[name],"The furnace mouth must be a real recessed opening")
            self.assertIn((24,16,14),volumes[name],"The furnace lining remains behind its rim")

    def test_tram_depots_keep_open_bays_oriented_rails_and_independent_wires(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("tram_depot_")}
        source["bindings"] = {category:{"5":source["bindings"][category]["5"]}
                              for category in ("depots","depot_floors","depot_wires")}
        result = compile_catalogue(source)
        def cells(name):
            return {(x+i,y,z):material for x,y,z,length,material in result["models"][name]["runs"] for i in range(length)}
        body_palette = {1,2,3,4,5,6,7,8,9,33,34,35,36,37,38,70,71,72,73,74,75,76,77,104,105,199,200,202}
        for direction in range(4):
            name = result["bindings"]["depots"]["5"][str(direction)]
            self.assertEqual(name,result["bindings"]["depots"]["5"][str(direction+4)],
                             "All four source climates share the identical tram building")
            body = cells(name)
            self.assertTrue({c for m in body.values() for c in result["materials"][m-1]} <= body_palette)
            reached = {p for p in body if p[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in body and p not in reached:
                        reached.add(p); pending.append(p)
            self.assertEqual(reached,set(body),"Roof transformer/insulators must have physical support")
            # Check the actual entry corridors in the four original exit directions.
            for x,y,z in body:
                along,across = ((31-x,31-y),(y,31-x),(x,y),(31-y,x))[direction]
                self.assertFalse(along >= 16 and 7 <= across < 25 and z < 10,
                                 "Do not close the vehicle bay below its source lintel")
            floor = cells(result["bindings"]["depot_floors"]["5"][str(direction)])
            self.assertEqual({(x,y) for x,y,z in floor if z == 0},{(x,y) for x in range(64) for y in range(64)})
            self.assertTrue({c for m in floor.values() for c in result["materials"][m-1]} <= {3,4,5,6,7,8})
            wire = cells(result["bindings"]["depot_wires"]["5"][str(direction)])
            self.assertEqual(min(z for x,y,z in wire),38,"Contact wires retain the9.5-unit local height")
            rail_mouth, wire_mouth = set(),set()
            for volume,level,mouth in ((floor,1,rail_mouth),(wire,38,wire_mouth)):
                for x,y,z in volume:
                    along,across = ((63-x,63-y),(y,63-x),(x,y),(63-y,x))[direction]
                    if along == 63 and z == level: mouth.add(across)
            self.assertEqual(rail_mouth,{15,25,39,49},"All four embedded rails reach the original exit")
            self.assertEqual(wire_mouth,{20,44},"Each contact wire aligns with its running-track centre")
        sw = cells("tram_depot_sw")
        self.assertNotIn((4,1,5),sw,"Side glazing keeps the outer wall recess")
        self.assertIn((4,2,5),sw)

    def test_printing_works_preserves_open_construction_courtyard_flues_and_join(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("print_") or name == "mine_ground_site"}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in range(43,47)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        for graphics in range(43,47):
            states = result["bindings"]["industries"][str(graphics)]
            self.assertEqual(states["1"],states["2"])
            self.assertEqual(len(set(states.values())),3)
            for stage,name in states.items():
                cells = volumes[name]
                self.assertEqual({(x,y) for x,y,z in cells if z == 0},{(x,y) for x in range(32) for y in range(32)})
                if stage == "0": self.assertEqual({z for x,y,z in cells},{0})
                reached = {p for p in cells if p[2] == 0}
                pending = list(reached)
                for x,y,z in pending:
                    for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                        if p in cells and p not in reached:
                            reached.add(p); pending.append(p)
                self.assertEqual(reached,set(cells),(graphics,stage,"Every rafter, rim and wall must have physical support"))
        for name in ("print_north_partial","print_west_partial"):
            self.assertNotIn((12,10,35),volumes[name],"Construction has no finished main roof")
            self.assertNotIn((4,31,8),volumes[name],"Tall lower openings remain genuine apertures")
        north = volumes["print_north_finished"]
        self.assertIn((4,30,8),north)
        self.assertNotIn((4,31,8),north,"Completed glazing keeps a recessed outer face")
        for x,y,z in ((16,4,64),(10,14,98),(6,22,60),(4,26,74)):
            self.assertNotIn((x,y,z),north,"Every white flue stays open through its rim")
        self.assertNotIn((10,2,27),volumes["print_north_partial"],"The source's high back-wall opening must remain open")
        self.assertNotIn((0,5,12),volumes["print_north_partial"],"The source's tall end-wall bays must remain open")
        self.assertIn((1,5,12),north)
        self.assertIn((28,18,5),volumes["print_east_partial"],"The exposed workshop frame runs alongX, notY")
        self.assertEqual({(y,z) for x,y,z in north if x == 31 and z >= 32},
                         {(y,z) for x,y,z in volumes["print_west_finished"] if x == 0 and z >= 32})
        for name in ("print_south_partial","print_south_finished"):
            self.assertTrue(all(z == 0 for x,y,z in volumes[name] if 3 <= x < 30 and 3 <= y < 30),
                            "The original courtyard must remain empty")
        soil = volumes["print_site_ground"]
        allowed = {33,53,54,61,71,72,73,74,105,106,107,108,112,113,123,124}
        self.assertTrue({c for m in soil.values() for c in result["materials"][m-1]} <= allowed,
                        "Printing ground3924 must retain its own source palette")

    def test_factory_layers_preserve_empty_body_support_and_roof_ownership(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        table = (root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0]
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",table)
        for graphics in range(121,125):
            for stage in range(4):
                self.assertEqual([field.strip() for field in rows[graphics*4+stage].split(",")],
                                 [field.strip() for field in rows[(graphics-82)*4+stage].split(",")],
                                 "Tropical factory aliases require identical source layers and registration")
            for category in ("industries","industry_ground"):
                self.assertEqual(source["bindings"][category][str(graphics)],source["bindings"][category][str(graphics-82)])
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("factory_") or name in ("mine_ground_bare","mine_ground_site")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in range(39,43)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        self.assertNotIn("3",result["bindings"]["industries"]["42"],"The entire completed service shed is ground-owned")
        def world_cells(name):
            model = result["models"][name]
            return {(round((model["origin"][0]+x*model["cell_size"][0])*4),
                     round((model["origin"][1]+y*model["cell_size"][1])*4),
                     round((model["origin"][2]+z*model["cell_size"][2])*4))
                    for x,y,z in volumes[name]}
        for graphics in range(39,43):
            states = result["bindings"]["industries"][str(graphics)]
            self.assertEqual(states["1"],states["2"])
            self.assertEqual({z for x,y,z in volumes[states["0"]]},{0},"Excavations have no future building mass")
            ground_name = result["bindings"]["industry_ground"][str(graphics)]["3"]
            ground = volumes[ground_name]
            self.assertEqual({(x,y) for x,y,z in ground if z == 0},{(x,y) for x in range(32) for y in range(32)})
            joined = {(x,y,z-1) for x,y,z in ground}
            if "3" in states:
                body_name = states["3"]
                self.assertFalse(world_cells(body_name) & world_cells(ground_name),"Independent source owners must not overlap")
                joined |= set(volumes[body_name])
            reached = {p for p in joined if p[2] == -1}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in joined and p not in reached:
                        reached.add(p); pending.append(p)
            self.assertEqual(reached,joined,(graphics,"Upper factory bodies must meet their independently owned ground support"))
        north = volumes["factory_north_finished"]
        self.assertEqual({(y,z) for x,y,z in north if x == 31 and z >= 28},
                         {(y,z) for x,y,z in volumes["factory_west_finished"] if x == 0 and z >= 28})
        self.assertTrue(all(y >= 21 for x,y,z in volumes["factory_east_finished"]),
                        "Original2151 contains the tower only; the low dark roof belongs to2147")
        for p in ((7,13,83),(7,20,77),(7,27,103)):
            self.assertNotIn(p,north,"Keep each original flue open through its rim")
        self.assertNotIn((7,14,6),volumes["factory_south_partial"],"Construction entrance remains a real aperture")
        self.assertNotIn((23,8,6),volumes["factory_south_partial"],"The unfinished opposite wall must not appear early")
        self.assertNotIn((8,23,6),volumes["factory_south_ground"],"Completed glass retains its outer recess")
        self.assertIn((8,22,6),volumes["factory_south_ground"])
        self.assertIn((24,15,22),volumes["factory_south_ground"],"The source service shed has its ridge alongX")
        partial = volumes["factory_north_partial"]
        self.assertNotIn((2,2,20),partial,"Construction must not introduce unsupported rear posts")
        self.assertNotIn((16,11,16),partial,"Original upper construction openings remain apertures")

    def test_lumbermill_preserves_construction_voids_log_stacks_and_roof_join(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("lumber_") or name in ("mine_ground_bare","mine_ground_site")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in range(125,129)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        soil_colours = {1,2,24,33,54,60,61,62,71,72,73,74,104,105,106,107,108,112,113,122,123}
        self.assertTrue({c for m in volumes["mine_ground_bare"].values() for c in result["materials"][m-1]} <= soil_colours,
                        "Original2022 must not inherit the extra colours of construction soil3924")
        for graphics in range(125,129):
            states = result["bindings"]["industries"][str(graphics)]
            self.assertEqual(states["1"],states["2"],"Original middle construction sprites are identical")
            self.assertEqual(len(set(states.values())),3,"Distinct original initial/middle/completed artwork must not alias")
            self.assertEqual(set(result["bindings"]["industry_ground"][str(graphics)].values()),{"mine_ground_bare"})
            for stage,name in states.items():
                model,cells = result["models"][name],volumes[name]
                self.assertEqual(model["origin"],[0,0,0])
                self.assertEqual({(x,y) for x,y,z in cells if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells))
                if stage == "0":
                    self.assertEqual({z for x,y,z in cells},{0},"Initial soil/excavation must not acquire later buildings")
                if stage != "3":
                    self.assertFalse({colour for m in cells.values() for colour in result["materials"][m-1]} & {56,57,58,64,65},"Golden timber appears only on completion")
                reached = {p for p in cells if p[2] == 0}
                pending = list(reached)
                for x,y,z in pending:
                    for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                        if p in cells and p not in reached:
                            reached.add(p); pending.append(p)
                self.assertEqual(reached,set(cells),(graphics,stage,"Every beam, roof, log and chimney must reach a real support"))
        for y in (13,19,25):
            self.assertNotIn((22,y,6),volumes["lumber_shed_partial"])
            self.assertIn((21,y,6),volumes["lumber_shed_finished"])
            self.assertNotIn((22,y,6),volumes["lumber_shed_finished"],"Inset glazing must retain the outer reveal")
        self.assertEqual(result["materials"][volumes["lumber_shed_partial"][(12,16,1)]-1],[1]*6,
                         "Wall construction must not overwrite the source's dark excavation floor")
        shed = volumes["lumber_shed_finished"]
        self.assertIn((14,31,20),shed,"The source gable faces theY+ workshop entrance")
        self.assertNotIn((24,16,20),shed,"The source ridge runs alongY rather than across the workshop")
        self.assertNotIn((12,20,80),volumes["lumber_boiler_finished"],"Keep the tall chimney bore open through its cap")
        self.assertNotIn((25,21,50),volumes["lumber_boiler_finished"],"Keep the smaller chimney bore open")
        self.assertIn((8,20,80),volumes["lumber_boiler_finished"])
        self.assertNotIn((20,20,10),volumes["lumber_yard_finished"],"The canopy must have an open loading bay")
        a = {(x,z) for x,y,z in volumes["lumber_yard_finished"] if y == 31 and z >= 16}
        b = {(x,z) for x,y,z in volumes["lumber_boiler_finished"] if y == 0 and z >= 16}
        self.assertTrue(a)
        self.assertEqual(a,b,"The two original canopy owners must join without a step or missing roof cells")

    def test_airport_surfaces_keep_source_ownership_runway_lanes_and_small_terminal_support(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        ids = {0,1,2,3,14,15,16,17,18,33,34,35,45,46,48,49,50,53,54,55,56,57,58,59,60,61,62,65,66,67,68,70}
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith(("airport_surface_","airport_small_terminal_")) or name in ("airport_small_control_tank","airport_low_ground","road_depot_floor")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in ids}
                              for category in ("airport_tiles","airport_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        original = (root / "src/table/station_land.h").read_text().split("_station_display_datas_airport[] = {",1)[1].split("};",1)[0]
        body_owners = [kind != "LINE_NOTHING" for kind in re.findall(r"\bTILE_SPRITE_(LINE_NOTHING|LINE|NULL)\(",original)]
        self.assertEqual(len(body_owners),74)
        for graphics in ids:
            self.assertEqual(str(graphics) in result["bindings"]["airport_tiles"],body_owners[graphics],graphics)
            floor_name = result["bindings"]["airport_ground"][str(graphics)]["0"]
            floor = result["models"][floor_name]
            self.assertEqual({(x,y) for x,y,z in volumes[floor_name] if z == 0},{(x,y) for x in range(32) for y in range(32)})
            self.assertEqual(floor["origin"][:2],[0,0])
            self.assertEqual(floor["cell_size"][:2],[0.5,0.5])
        # The source end bars and longitudinal dashes are distinct. Ground paint
        # remains level with the aircraft running datum, including its lamps.
        for name in (n for n in volumes if n.startswith("airport_surface_runway")):
            model = result["models"][name]
            self.assertEqual({model["origin"][2]+(z+1)*model["cell_size"][2] for x,y,z in volumes[name]},{0})
            colours = {c for m in volumes[name].values() for c in result["materials"][m-1]}
            self.assertTrue({241,243} <= colours or name.endswith(("_1","_3","_4")))
        middle,end = (volumes[n] for n in ("airport_surface_runway_middle","airport_surface_runway_end"))
        white = lambda m: result["materials"][m-1][5] == 15
        self.assertTrue(white(middle[(2,15,0)]))
        self.assertFalse(white(middle[(16,15,0)]))
        self.assertEqual([y for y in range(32) if white(end[(16,y,0)])],[*range(4,8),*range(11,15),*range(18,22),*range(25,29)])
        # Source fence owners leave all usable runway/parking space open.
        for graphics in ids-{33,34,35}:
            binding = result["bindings"]["airport_tiles"].get(str(graphics))
            if not binding:
                continue
            model = result["models"][binding["0"]]
            self.assertTrue(all(x in (0,30) or y in (0,30) or z == 0 for x,y,z in volumes[binding["0"]]),graphics)
            self.assertLessEqual(max((z+1)*model["cell_size"][2] for x,y,z in volumes[binding["0"]]),3)
        # Compare actual occupied quarter-unit cells, so mixed ground/body grids
        # cannot hide overlaps or disconnected tank legs and cabin platforms.
        def occupied(name):
            model = result["models"][name]
            step = [round(v*4) for v in model["cell_size"]]
            origin = [round(v*4) for v in model["origin"]]
            return {(origin[0]+x*step[0]+dx,origin[1]+y*step[1]+dy,origin[2]+z*step[2]+dz)
                    for x,y,z in volumes[name] for dx in range(step[0]) for dy in range(step[1]) for dz in range(step[2])}
        for graphics in (33,34,35):
            ground = occupied(result["bindings"]["airport_ground"][str(graphics)]["0"])
            body = occupied(result["bindings"]["airport_tiles"][str(graphics)]["0"]) if graphics == 35 else set()
            self.assertFalse(ground & body,"Original ground and body owners must not overlap")
            joined = ground | body
            reached = {p for p in joined if p[2] == -2}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in joined and p not in reached:
                        reached.add(p); pending.append(p)
            self.assertEqual(reached,joined,(graphics,"Every wall, roof, platform and tank must reach ground"))
        self.assertNotIn((8,25,8),volumes["airport_small_control_tank"],"Keep the water tank's supporting frame open")

    def test_airport_edges_keep_climate_grounds_level_empty_owners_and_overlay_partition(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        ground_bindings = source["bindings"]["airport_ground"]
        self.assertEqual({int(g) for g in ground_bindings},set(range(74)))
        for graphics,frames in ((31,12),(39,4),(73,4)):
            self.assertEqual({int(s) for s in ground_bindings[str(graphics)]},
                             {climate*16+frame for climate in range(4) for frame in range(frames)})
            for climate in range(4):
                self.assertEqual(len({ground_bindings[str(graphics)][str(climate*16+frame)] for frame in range(frames)}),1)
        for graphics in (*range(4,13),29,37,38):
            self.assertNotIn(str(graphics),source["bindings"]["airport_tiles"],"An empty original sequence must remain empty")
        for climate in range(4):
            self.assertEqual(ground_bindings["11"][str(climate*16)],ground_bindings["13"][str(climate*16)])
            self.assertEqual(ground_bindings["29"][str(climate*16)],ground_bindings["30"][str(climate*16)])
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("airport_edge_")}
        source["bindings"] = {}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        square = {(x,y) for x in range(32) for y in range(32)}
        for name,volume in volumes.items():
            model = result["models"][name]
            self.assertEqual(model["cell_size"],[0.5,0.5,0.25])
            self.assertEqual({z for x,y,z in volume},{0})
            if "half_" not in name:
                self.assertEqual(model["origin"],[0,0,-0.25])
                self.assertEqual({(x,y) for x,y,z in volume},square,"Every independently owned surface keeps its complete footprint")
        east,west = (set(volumes["airport_edge_half_"+side]) for side in ("east","west"))
        self.assertFalse(east & west)
        self.assertEqual({(x,y) for x,y,z in east|west},square)
        self.assertTrue(all(x >= y for x,y,z in east))
        self.assertTrue(all(x < y for x,y,z in west))
        for family in ("lawn",*(f"apron_{g}" for g in range(4,13)),*(f"worn_{g}" for g in range(36,40)),*(f"runway_{g}" for g in range(40,43))):
            paint = []
            for climate in ("temperate","arctic","tropic","toyland"):
                volume = volumes[f"airport_edge_{family}_{climate}"]
                paint.append(tuple(result["materials"][volume[x,y,0]-1][5] for x,y in sorted(square)))
            self.assertEqual(len(set(paint)),4,"Distinct original climate paint must not silently alias")

    def test_low_airport_preserves_original_l_plan_fence_owners_and_independent_ground(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("airport_low_") or name == "road_depot_floor"}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in (63,64,69)}
                              for category in ("airport_tiles","airport_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                   for name,model in result["models"].items()}
        original_body = set(range(5,16)) | set(range(32,37)) | set(range(128,132))
        for graphics in (63,64,69):
            name = result["bindings"]["airport_tiles"][str(graphics)]["0"]
            body = volumes[name]
            allowed = original_body | ({8,202,204} if graphics != 69 else set())
            colours = {colour for material in body.values() for colour in result["materials"][material-1]}
            self.assertTrue(colours <= allowed)
            self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 and 0 <= z < 9 for x,y,z in body))
            self.assertFalse(any(x >= 19 and y >= 19 for x,y,z in body),"Keep the original L-plan courtyard open through the roof")
            self.assertNotIn((18,21,3),body,"The recessed entrance must remain open at its outer face")
            self.assertIn((16,21,3),body,"The recessed entrance needs its source glazing behind the reveal")
            self.assertNotIn((12,12,3),body,"The low terminal must retain a hollow interior")
            for point in ((6,9,3),(9,6,3),(26,9,3),(9,26,3),(18,19,3),(20,18,3)):
                self.assertTrue(set(result["materials"][body[point]-1]) <= set(range(128,132)),
                                "Facade piers must not repaint an entire perpendicular glazed wall")
            reached = {p for p in body if p[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in body and p not in reached:
                        reached.add(p); pending.append(p)
            self.assertEqual(reached,set(body),"The parapet, glazing and fence rails must reach actual supports")
            floor_name = result["bindings"]["airport_ground"][str(graphics)]["0"]
            self.assertEqual(floor_name,"airport_low_ground")
            floor = result["models"][floor_name]
            self.assertEqual(floor["origin"],[0,0,-0.25])
            self.assertEqual(floor["cell_size"],[0.5,0.5,0.25])
            self.assertEqual(set(volumes[floor_name]),{(x,y,0) for x in range(32) for y in range(32)})
            self.assertTrue({colour for material in volumes[floor_name].values() for colour in result["materials"][material-1]} <= set(range(3,9)))
        plain,nw,n = (volumes[name] for name in ("airport_low_building","airport_low_building_fence_nw","airport_low_building_fence_n"))
        self.assertEqual({p:m for p,m in nw.items() if p[1] != 0},plain)
        self.assertEqual({p:m for p,m in n.items() if p[0] != 0},{p:m for p,m in nw.items() if p[0] != 0})
        self.assertIn((31,0,2),nw)
        self.assertIn((0,31,2),n)

    def test_bank_keeps_joined_owners_completed_body_slots_and_independent_paving(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("bank_","mine_ground_"))}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in (58,59)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        body_palettes = {
            58:set(range(1,16)) | set(range(24,31)) | set(range(33,40)) | set(range(128,135)),
            59:set(range(2,15)) | set(range(24,30)) | set(range(34,40)) | set(range(129,135)),
        }
        ground_palettes = {
            58:{1,4,5,6,7,8,9,10,11,20,21,24,25,71,82,83,84,89,90,91,104,105,106,107,112,206},
            59:{1,2,3,4,5,6,7,8,9,10,11,19,20,21,24,25,32,71,82,83,84,85,89,90,91,98,104,105,106,112,206},
        }
        def cells(name, offset=0):
            model = result["models"][name]
            ox,oy,oz = model["origin"]
            return {(int(ox*2)+x+i+offset,int(oy*2)+y,int(oz)+z):material
                    for x,y,z,length,material in model["runs"] for i in range(length)}
        joined = {}
        for graphics,offset in ((58,0),(59,32)):
            bodies = result["bindings"]["industries"][str(graphics)]
            self.assertEqual(set(bodies),{"0","1","2","3"})
            self.assertEqual(len(set(bodies.values())),1,"The original uses its finished bank body in every construction slot")
            grounds = result["bindings"]["industry_ground"][str(graphics)]
            self.assertEqual({grounds[str(stage)] for stage in range(3)},{"mine_ground_bare"})
            self.assertNotEqual(grounds["3"],grounds["0"],"Only completion replaces the independent2022 ground with paving")
            body, ground = cells(bodies["3"],offset), cells(grounds["3"],offset)
            for volume,allowed in ((body,body_palettes[graphics]),(ground,ground_palettes[graphics])):
                colours = {colour for material in volume.values() for colour in result["materials"][material-1]}
                self.assertTrue(colours <= allowed,(graphics,sorted(colours-allowed)))
                self.assertTrue(all(offset <= x < offset+32 and 0 <= y < 32 for x,y,z in volume))
                self.assertFalse(set(joined) & set(volume),"The bank's ground and two body owners must not overlap")
                joined.update(volume)
            self.assertEqual({(x,y) for x,y,z in ground if z == -1},{(x,y) for x in range(offset,offset+32) for y in range(32)})
        reached = {p for p in joined if p[2] == -1}
        pending = list(reached)
        for x,y,z in pending:
            for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                if p in joined and p not in reached:
                    reached.add(p)
                    pending.append(p)
        self.assertEqual(reached,set(joined),"The cupola, arch and shared roof must all have physical support")
        north,south = cells("bank_north"),cells("bank_south",32)
        self.assertTrue(any((32,y,z) in south for x,y,z in north if x == 31),"The original X seam must physically join")
        for x in range(28,36):
            for z in range(1,17):
                self.assertNotIn((x,24,z),joined,"Retain the shared bank's usable entrance beneath its arch")
        self.assertIn((25,9,43),joined,"Keep the original fine white finial above its supported dome")

    def test_food_processing_retains_independent_ground_source_states_and_open_vessels(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("food_","mine_ground_"))}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in range(60,64)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        def cells(name):
            return {(x+i,y,z):material for x,y,z,length,material in result["models"][name]["runs"] for i in range(length)}
        palettes = {
            2188:{1,2,3,24,70,71,104,105,107,112},
            2189:{1,2,3,6,7,8,9,19,44,46,70,71,72,73,74,75,76,77,125,126,132,133},
            2190:{1,4,5,6,7,8,9,10,18,19,44,70,71,72,73,74,75,76,77,78,79,125,126,129,130,131,132,133,198,199,200,201,202,203},
            2191:{1,2,3,24,33,54,61,62,70,71,72,73,104,105,106,107,108,112,113,122,123,124},
            2192:{1,2,3,4,5,6,7,8,9,10,19,20,21,34,43,44,45,70,71,72,73,74,75,76,77,114,124,125,126,127,132},
            2193:{1,2,4,5,6,7,8,9,10,11,19,20,21,70,71,72,73,74,75,76,77,124,125,126,127,128,129,130,131,132,133,200,201,202,227,228,229,230,231},
            2194:{1,2,3,24,33,53,54,60,61,62,70,71,72,73,74,104,105,106,107,108,112,113,123,124},
            2195:{2,4,5,6,7,8,9,17,18,19,20,24,33,54,61,62,71,72,73,74,100,101,104,105,106,107,108,112,113,122,123,156,157,198,199,200,201,202,203,204},
            2196:{2,4,5,6,7,8,9,18,19,20,24,25,32,35,36,37,38,39,53,54,61,62,71,72,73,74,100,101,105,106,107,108,112,113,123,158,199,200,201,202,203,204},
            2197:{1,2,3,24,54,60,61,62,71,72,73,104,105,106,107,108,112,113,122,123,124},
            2198:{3,4,24,25,26,27,28,33,34,35,40,54,55,56,57,58,60,61,62,71,72,73,74,75,76,77,90,91,105,106,107,108,109,112,113,114,122,123,124,179,199,200},
            2199:{4,25,26,27,28,32,33,34,35,37,38,39,53,54,55,56,57,58,60,61,62,63,71,72,73,74,75,76,77,90,91,105,106,107,108,109,110,112,113,114,122,123,178,199,200,202,203},
        }
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",(root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0])
        aliases = {}
        for graphics in range(60,64):
            for stage in range(4):
                fields = rows[graphics*4+stage].split(",")
                sprite = int(fields[2].strip().split("|")[0],0)
                name = result["bindings"]["industries"][str(graphics)][str(stage)]
                self.assertEqual(aliases.setdefault(sprite,name),name,"Only source-identical construction slots may share geometry")
                self.assertEqual(int(fields[0].strip(),0),2022)
                self.assertEqual(result["bindings"]["industry_ground"][str(graphics)][str(stage)],"mine_ground_bare")
                volume = cells(name)
                colours = {colour for material in volume.values() for colour in result["materials"][material-1]}
                self.assertTrue(colours <= palettes[sprite],(name,sorted(colours-palettes[sprite])))
        for name in (name for name in result["models"] if name.startswith("food_")):
            volume = cells(name)
            self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in volume),name)
            reached = {p for p in volume if p[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in volume and p not in reached:
                        reached.add(p)
                        pending.append(p)
            self.assertEqual(reached,set(volume),f"{name} has unsupported walls, chimneys, pipes or fencing")
        partial, final = cells("food_silo_partial"), cells("food_silo")
        self.assertNotIn((16,16,35),partial,"The initial erected silo has an empty interior")
        self.assertIn((16,16,35),final,"Completion adds the original visible grain")
        self.assertNotIn((16,16,37),final,"Keep grain below an open rim, never substitute a closed lid")
        for name,openings in (("food_hall",((7,25,48),(15,25,41),(31,12,5))),
                              ("food_boiler",((24,6,50),(7,20,34),(13,16,5)))):
            for point in openings:
                self.assertNotIn(point,cells(name),f"{name} must retain original open chimneys and loading doors")

    def test_waterworks_keep_tropical_soil_construction_tanks_and_open_supports(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("waterworks_")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in (118,119,120)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        def cells(name):
            return {(x+i,y,z):material for x,y,z,length,material in result["models"][name]["runs"] for i in range(length)}
        # Manually inspected original2344..2352, plus4550 from a tropical export.
        palettes = {
            "waterworks_supply_initial":{3,5,7},
            "waterworks_supply_partial":set(range(2,12)) | {131,132,133,199,200,201,202,203,204},
            "waterworks_supply":set(range(2,13)) | {130,131,132,133,199,200,201,202,203,204},
            "waterworks_pump_initial":set(range(2,13)),
            "waterworks_pump_partial":set(range(2,14)) | {132,133,134,135,200,201,202,203,204},
            "waterworks_pump":set(range(2,14)) | {132,133,134,135,200,201,202,203},
            "waterworks_tower_initial":{2,5,8},
            "waterworks_tower_partial":set(range(2,9)) | set(range(198,205)),
            "waterworks_tower":set(range(1,9)) | set(range(199,206)),
            "waterworks_desert_ground":{56,57,62,63,64,65,73,74,75,76,77,108,109,110,113,114,115,116,117,118,119,123,124,126,192,195},
        }
        for name,allowed in palettes.items():
            volume = cells(name)
            colours = {colour for material in volume.values() for colour in result["materials"][material-1]}
            self.assertTrue(colours <= allowed,(name,sorted(colours-allowed)))
            self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in volume),name)
            reached = {p for p in volume if p[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in volume and p not in reached:
                        reached.add(p)
                        pending.append(p)
            self.assertEqual(reached,set(volume),f"{name} has unsupported tanks, panels or pipes")
        ground = cells("waterworks_desert_ground")
        self.assertEqual(len(ground),32*32)
        self.assertEqual(result["models"]["waterworks_desert_ground"]["origin"],[0,0,-1])
        for graphics in ("118","119","120"):
            bodies = result["bindings"]["industries"][graphics]
            self.assertEqual(set(bodies),{"0","1","2","3"})
            self.assertEqual(bodies["1"],bodies["2"],"Only source-identical intermediate states may share geometry")
            self.assertEqual(set(result["bindings"]["industry_ground"][graphics].values()),{"waterworks_desert_ground"})
        early = cells("waterworks_tower_initial")
        partial = cells("waterworks_tower_partial")
        final = cells("waterworks_tower")
        self.assertTrue(all(z < 14 for x,y,z in early))
        self.assertNotIn((16,16,33),partial,"The original construction tank must stay open")
        self.assertNotIn((16,16,20),partial,"Retain its real interior cavity")
        self.assertIn((16,16,14),partial,"The open cylinder still needs an independent structural bottom")
        self.assertIn((16,16,43),final,"Only completion closes the blue roof")
        self.assertNotIn((16,16,7),final,"Keep the tank's essential open clearance between support cages")
        self.assertNotIn((23,17,44),cells("waterworks_supply_partial"))
        self.assertIn((23,17,44),cells("waterworks_supply"),"Finished elevated pipes need explicit connected geometry")

    def test_plantations_keep_four_rooted_trees_independent_soil_and_empty_early_bodies(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("plantation_")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if int(key) in (116,117)}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        def cells(name):
            return {(x+i,y,z):material for x,y,z,length,material in result["models"][name]["runs"] for i in range(length)}
        ground = cells("plantation_ground")
        self.assertEqual(len(ground),32*32)
        self.assertEqual(result["models"]["plantation_ground"]["origin"],[0,0,-1])
        roots = ((12,12),(12,28),(28,12),(28,28))
        palettes = {
            "plantation_banana":{2,24,25,26,27,28,64,65,66,67,80,81,82,83,84,85,86},
            "plantation_rubber":{1,2,3,4,15,32,33,34,35,36,96,97,98,99,100,101},
            "plantation_ground":{3,4,24,25,26,27,28,34,35,36,54,55,56,57,63,64,65,76,89,90,91,92,96,97,98,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119},
        }
        for name,allowed in palettes.items():
            volume = cells(name)
            colours = {colour for material in volume.values() for colour in result["materials"][material-1]}
            self.assertTrue(colours <= allowed,(name,sorted(colours-allowed)))
            self.assertTrue(all(0 <= x < (32 if z == 0 else 36) and 0 <= y < (32 if z == 0 else 36) for x,y,z in volume),
                            "All roots remain on the full tile; only the original overhanging crowns may cross its edge")
            if name == "plantation_ground":
                continue
            for x,y in roots:
                self.assertTrue((x,y,0) in volume,(name,"missing original tree root",x,y))
            reached = {p for p in volume if p[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in volume and p not in reached:
                        reached.add(p)
                        pending.append(p)
            self.assertTrue(reached == set(volume),(name,"detached foliage/fruit",sorted(set(volume)-reached)[:12]))
        for graphics in ("116","117"):
            self.assertEqual(set(result["bindings"]["industries"][graphics]),{"2","3"})
            self.assertEqual(result["bindings"]["industries"][graphics]["2"],result["bindings"]["industries"][graphics]["3"])
            self.assertEqual(set(result["bindings"]["industry_ground"][graphics].values()),{"plantation_ground"})
        rubber = cells("plantation_rubber")
        for x,y in roots:
            self.assertEqual(result["materials"][rubber[x,y+1,6]-1],[15]*6,"Preserve all four white latex collectors")

    def test_paper_mill_keeps_original_state_aliases_empty_bodies_and_supported_machinery(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("paper_") or name in ("mine_ground_bare","mine_ground_site")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if 64 <= int(key) <= 71}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        table = (root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0]
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",table)
        palettes = {
            2200:{1,2,3}, 2201:{1,2,3,6,7,32,33,34,35,36,37,38},
            2202:set(range(1,16)) | set(range(32,39)) | set(range(128,135)),
            2203:{1,2,3}, 2204:{1,2,3,32,33,34,35,36,37},
            2205:{1,2,3,4,5,32,33,34,35,36,37,128,129,130,131,132,133,134},
            2206:{1,2,3,4,5,8,9,12,13,32,33,34,35,36,37,130,131,132,133,202,203,250,251,252,253,254},
            2207:set(range(1,15)) | {19,20,21,26,32,33,34,35,36,37,90,93,104,105,132,133},
            2208:set(range(1,15)) | {19,20,21,32,33,34,35,36,37,38,90,104,105,127,131,132,133,134},
            2209:set(range(1,16)) | {19,20,21,32,33,34,35,36,37,90,91,104,105,130,131,132,133},
            2210:{6,7,8,9,10,19,20,21,24,54,60,61,62,71,72,73,74,105,106,107,108,112,113,122,123,124},
            2211:{1,2,3,5,6,7,8,9,10,19,20,21,32,33,34,35,36,37,90,133},
            2212:{1,2,3,4,5,6,7,8,9,10,11,19,20,21,32,33,34,35,36,91,132,133},
            2213:{1,2,3,4,5,6,7,8,9,10,19,20,21,29,30,32,33,34,35,36,55,56,57,58,59,91,105,106,107,108,109,110,127,130,131,132},
            2214:{1,2,3,4,5,6,7,9,33,34,35,36,37},
        }
        aliases = {}
        for graphics in range(64,72):
            for stage in range(4):
                fields = rows[graphics*4+stage].split(",")
                for category,index in (("industry_ground",0),("industries",2)):
                    sprite = int(fields[index].strip(),0)
                    name = result["bindings"][category][str(graphics)].get(str(stage))
                    if sprite == 0:
                        self.assertIsNone(name,"Original empty construction bodies must stay absent")
                    else:
                        self.assertIsNotNone(name)
                        self.assertEqual(aliases.setdefault((category,sprite),name),name)
                        if category == "industries":
                            colours = {colour for *_,material in result["models"][name]["runs"] for colour in result["materials"][material-1]}
                            self.assertTrue(colours <= palettes[sprite],(name,sorted(colours-palettes[sprite])))
                self.assertEqual(result["bindings"]["industry_ground"][str(graphics)][str(stage)],"mine_ground_bare")
        def cells(name):
            return {(x+i,y,z):material for x,y,z,length,material in result["models"][name]["runs"] for i in range(length)}
        for name in (name for name in result["models"] if name.startswith("paper_")):
            volume = cells(name)
            self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in volume))
            reached = {p for p in volume if p[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in volume and p not in reached:
                        reached.add(p)
                        pending.append(p)
            self.assertEqual(reached,set(volume),f"{name} has unsupported components")
        partial = cells("paper_office_partial")
        self.assertNotIn((10,10,15),partial,"The unfinished office must stay open")
        self.assertNotIn((29,4,4),partial,"The unfinished window openings must stay empty")
        self.assertIn((29,4,4),cells("paper_office"))
        boilers = cells("paper_boiler")
        for x,y,z in ((26,4,59),(14,4,35)):
            self.assertNotIn((x,y,z),boilers,"Keep the two original chimney mouths open")
            self.assertIn((x,y,1),boilers,"Preserve source-aligned chimney feet")
        self.assertNotIn((18,26,5),boilers)
        self.assertTrue((16,26,5) in cells("paper_boiler_stocked"),"Only original2209 carries the white paper rolls")
        self.assertNotIn((20,20,2),cells("paper_yard"))
        self.assertIn((20,20,2),cells("paper_yard_lumber"),"Keep the completed lumber stockpile distinct from the empty yard")

    def test_farm_preserves_joined_owners_empty_states_hay_ground_and_open_silos(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("farm_") or name in ("mine_ground_bare","mine_ground_site")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if 33 <= int(key) <= 38}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        # Visible palette indices manually reviewed in the pinned original source.
        body_palettes = {
            33:set(range(1,15)) | {73,74,75,76,112,116,117,118,130,131,132,133,134},
            34:{1,2,3,6,7,8,9,10,11,12,13,14,73,74,75,76,77,78,112,116,117,118,128,129,130,131,132},
            35:set(range(1,11)) | set(range(73,79)),
            36:set(range(1,14)) | {34,36,112},
            37:set(range(2,12)),
            38:set(range(1,13)) | {36,72,73,74,75,76,77,116,117,118,119,166,167},
        }
        ground_palettes = {
            33:{1,2,3,4,16,24,33,54,60,61,62,70,71,72,73,82,83,84,85,89,90,91,97,104,105,106,107,108,112,113,122,123,124,206},
            34:{1,2,3,4,5,16,24,53,54,60,61,62,70,71,72,73,104,105,106,107,108,112,113,114,122,123,124},
            35:{1,2,24,40,41,53,54,55,56,57,58,59,60,61,70,71,72,73,104,105,106,107,108,112,113,114,115,116,117,118,119,122,123,124,178,179,180},
            36:{1,2,24,32,33,54,60,61,62,70,71,72,73,82,83,84,85,86,89,90,91,104,105,106,107,108,112,113,114,123,124,206},
            37:{1,2,24,32,33,40,53,54,55,56,57,58,60,61,62,70,71,72,73,82,83,84,85,88,89,90,91,96,104,105,106,107,108,112,113,122,123,124,206},
            38:{1,2,24,33,54,55,56,57,58,60,61,62,70,71,72,73,74,82,83,84,89,90,104,105,106,107,108,112,113,122,123},
        }
        def cells(name, offset=(0,0,0)):
            model = result["models"][name]
            ox,oy,oz = model["origin"]
            return {(int(ox*2)+x+i+offset[0],int(oy*2)+y+offset[1],int(oz)+z+offset[2]):material
                    for x,y,z,length,material in model["runs"] for i in range(length)}
        def rooted(volume):
            reached = {p for p in volume if p[2] == 0}
            pending = list(reached)
            for x,y,z in pending:
                for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if p in volume and p not in reached:
                        reached.add(p)
                        pending.append(p)
            return reached
        for graphics in range(33,39):
            states = result["bindings"]["industries"][str(graphics)]
            self.assertEqual(set(states),{"0","1","2","3"} if graphics < 35 else {"1","2","3"})
            self.assertEqual(len(set(states.values())),1,"The original repeats its completed artwork")
            name = states["3"]
            colours = {colour for *_,material in result["models"][name]["runs"] for colour in result["materials"][material-1]}
            self.assertTrue(colours <= body_palettes[graphics],(graphics,sorted(colours-body_palettes[graphics])))
            ground = cells(result["bindings"]["industry_ground"][str(graphics)]["3"])
            ground_colours = {colour for material in ground.values() for colour in result["materials"][material-1]}
            self.assertTrue(ground_colours <= ground_palettes[graphics],(graphics,sorted(ground_colours-ground_palettes[graphics])))
            self.assertEqual({(x,y) for x,y,z in ground if z == -1},{(x,y) for x in range(32) for y in range(32)})
            body = cells(name)
            self.assertFalse(set(body) & set(ground),"A raised ground-owned hay pile must not intersect the shelter")
            if graphics >= 35:
                self.assertEqual(rooted(body),set(body),f"Farm graphic {graphics} has floating components")
                self.assertEqual(result["bindings"]["industry_ground"][str(graphics)]["0"],"mine_ground_bare")
        north,south = cells("farm_house_north"),cells("farm_house_south",(0,32,0))
        self.assertFalse(set(north)&set(south),"The farmhouse's two owners must be exclusive")
        joined = north | south
        self.assertEqual(rooted(joined),set(joined),"The joined house, glazing and chimneys must remain grounded")
        self.assertTrue(any((x,32,z) in south for x,y,z in north if y == 31),"The farmhouse must physically join across the original Y seam")
        silos = cells("farm_silos")
        for y in (10,24):
            self.assertNotIn((7,y,34),silos,"Keep the original dark silo aperture open")
            self.assertIn((7,y,0),silos)
        shelters = cells("farm_hay_sheds")
        self.assertNotIn((27,8,5),shelters,"The hay shelters must remain open")
        self.assertIn((8,14,4),cells("farm_hay_ground"),"Raised hay belongs to original ground2110")

    def test_oilwell_animation_keeps_source_aliases_rooted_frames_and_fixed_supports(self):
        root = Path(__file__).resolve().parents[2]
        source = json.loads((root / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items()
                            if name.startswith("oilwell_") or name in ("mine_ground_bare","mine_ground_site")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if 29 <= int(key) <= 32}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        table = (root / "src/table/industry_land.h").read_text().split("_industry_draw_tile_data",1)[1].split("};",1)[0]
        rows = re.findall(r"\bM\(\s*([^\n]+)\)",table)
        aliases = {}
        for graphics in range(29,33):
            for stage in range(4):
                fields = rows[graphics*4+stage].split(",")
                for category,index in (("industry_ground",0),("industries",2)):
                    sprite = int(fields[index].strip(),0)
                    name = result["bindings"][category][str(graphics)].get(str(stage))
                    if sprite == 0:
                        self.assertIsNone(name,"The first construction body must stay absent")
                    else:
                        self.assertIsNotNone(name)
                        self.assertEqual(aliases.setdefault((category,sprite),name),name)
        bodies = [result["models"][aliases[("industries",sprite)]] for sprite in range(2174,2180)]
        frames = [{(x+i,y,z):material for x,y,z,length,material in body["runs"] for i in range(length)} for body in bodies]
        self.assertEqual(len({tuple(sorted(frame.items())) for frame in frames}),6,"Every distinct horsehead pose needs its own volume")
        for frame in frames:
            supported = {point for point in frame if point[2] == 0}
            self.assertTrue(supported)
            pending = list(supported)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in frame and point not in supported:
                        supported.add(point)
                        pending.append(point)
            self.assertEqual(supported,set(frame),"Walking beam, head, rod and frame must remain supported in every pose")
            self.assertNotIn((12,16,5),frame,"Keep the open frame below the motor")
            self.assertEqual({p:m for p,m in frame.items() if p[0] < 22 and p[2] < 20},
                             {p:m for p,m in frames[0].items() if p[0] < 22 and p[2] < 20},"Animation must not move the motor or its fixed feet")
            self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in frame))
        ground = result["models"]["oilwell_ground"]
        self.assertEqual(ground["origin"],[0,0,-1])
        self.assertEqual(ground["occupied"],32*32)

    def test_oilrig_joined_construction_keeps_supported_parts_open_water_and_heli_contact(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("oilrig_")}
        source["bindings"] = {category:{key:value for key,value in source["bindings"][category].items() if 24 <= int(key) <= 28}
                              for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        for graphics, states in result["bindings"]["industries"].items():
            for stage, name in states.items():
                if graphics == "25":
                    allowed = {1,4,7,9,73,76,118,151,152,153,187,188,189} | set(range(232,239))
                elif stage == "0":
                    allowed = set(range(70,80)) | {250,251,252,253,254}
                else:
                    allowed = set(range(2,16)) | set(range(70,80)) | set(range(114,122)) | set(range(128,135)) | {250,251,252,253,254}
                    if graphics == "26" and stage == "3":
                        allowed |= {169,241,242,243,244,255}
                colours = {colour for *_,material in result["models"][name]["runs"] for colour in result["materials"][material-1]}
                self.assertTrue(colours <= allowed,(graphics,stage,sorted(colours-allowed)))
        self.assertNotIn("24",result["bindings"]["industries"],"The water-only oilrig tile must stay empty")
        self.assertEqual(set(result["bindings"]["industries"]["25"]),{"3"})
        for graphics in (26,27,28):
            states = result["bindings"]["industries"][str(graphics)]
            self.assertEqual(states["1"],states["2"])
            self.assertEqual(len(set(states.values())),3)
        for stage in range(4):
            joined = set()
            for x,y,graphics in ((0,2,25),(1,0,26),(1,1,27),(1,2,28)):
                name = result["bindings"]["industries"].get(str(graphics),{}).get(str(stage))
                if name is None:
                    continue
                model = result["models"][name]
                self.assertEqual(model["cell_size"],[0.5,0.5,1])
                ox,oy,oz = model["origin"]
                cells = {(int(ox*2)+x*32+cx+i,int(oy*2)+y*32+cy,int(oz)+cz)
                         for cx,cy,cz,length,_ in model["runs"] for i in range(length)}
                self.assertTrue(joined.isdisjoint(cells),"Industry ownership must not duplicate a joined cell")
                joined.update(cells)
            supported = {cell for cell in joined if cell[2] == 0}
            self.assertTrue(supported)
            pending = list(supported)
            for x,y,z in pending:
                for neighbour in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if neighbour in joined and neighbour not in supported:
                        supported.add(neighbour)
                        pending.append(neighbour)
            self.assertEqual(len(supported),len(joined),f"Unattached oilrig structure in stage{stage}: {len(joined-supported)} cells")
            self.assertNotIn((48,40,8),joined,"The sea between pilings must remain open")
            if stage == 0:
                self.assertEqual(max(z for x,y,z in joined),26,"The earliest source contains pilings, without the later deck or buildings")
            if stage in (1,2):
                self.assertNotIn((28,36,80),joined,"The intermediate source has no erected derrick")
            if stage >= 1:
                # The original oilrig airport terminal is (31,9), delta_z=54.
                self.assertIn((62,18,53),joined)
                self.assertNotIn((62,18,54),joined)
                self.assertFalse(any(54 <= x < 70 and 10 <= y < 26 and z >= 54 for x,y,z in joined))
        ground = result["models"]["oilrig_water_ground"]
        self.assertEqual(ground["origin"],[0,0,-1])
        self.assertEqual(ground["occupied"],32*32)

    def test_authored_prisms_keep_concavities_winding_axes_and_component_offsets(self):
        outline = [[0,0],[4,0],[4,1],[1,1],[1,4],[0,4]]
        expected_plane = {(u,v) for u in range(4) for v in range(4) if u == 0 or v == 0}
        for axis in range(3):
            plane = [d for d in range(3) if d != axis]
            for points in (outline,list(reversed(outline))):
                source = self.source([["use","angle",[1,1,1]]])
                source["components"] = {"angle":[["prism","wall",axis,0,2,points]]}
                model = compile_catalogue(source)["models"]["house"]
                actual = {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
                expected = set()
                for u,v in expected_plane:
                    for depth in range(2):
                        point = [1,1,1]
                        point[axis] += depth
                        point[plane[0]] += u
                        point[plane[1]] += v
                        expected.add(tuple(point))
                self.assertEqual(actual,expected)
        # Half-cell crossings use exact rational intervals, including a diagonal
        # through sample centres. Reversing the outline must not shift the wing.
        triangle = [[0,0],[4,0],[0,4]]
        source = self.source([["prism","wall",2,0,1,triangle]])
        first = compile_catalogue(source)["models"]["house"]
        source["models"]["house"]["ops"][0][-1].reverse()
        self.assertEqual(first,compile_catalogue(source)["models"]["house"])
        self.assertEqual(first["occupied"],6)

    def test_prisms_reject_clipped_self_crossing_and_degenerate_outlines(self):
        outlines = [
            [[0,0],[4,4],[4,0],[0,3]], [[0,0],[4,0],[4,0],[0,4]],
            [[0,0],[1,1],[2,2]], [[0,0],[9,0],[0,4]],
            [[0,0],[-1,0],[0,4]], [[0,0],[4.5,0],[0,4]],
            [[0,0],[4,0]], [[0,0],[4,0,1],[0,4]],
        ]
        for outline in outlines:
            with self.subTest(outline=outline), self.assertRaises(ValueError):
                compile_catalogue(self.source([["prism","wall",2,0,1,outline]]))
        for axis,low,high in ((3,0,1),(2,-1,1),(2,0,6),(2,2,2)):
            with self.subTest(axis=axis,low=low,high=high), self.assertRaises(ValueError):
                compile_catalogue(self.source([["prism","wall",axis,low,high,[[0,0],[4,0],[0,4]]]]))

    def test_aircraft_source_aliases_and_thin_parts_remain_supported(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("aircraft_")}
        source["bindings"] = {"vehicles":{str(engine):source["bindings"]["vehicles"][str(engine)] for engine in range(215,256)}}
        result, definitions = compile_catalogue(source), vehicle_definitions()
        source_families, model_families = {}, {}
        for engine in range(215,256):
            definition = definitions[str(engine)]
            self.assertEqual(definition["sprites"],definition["loaded_sprites"],"The aircraft cargo-state alias lacks original sprite evidence")
            states = result["bindings"]["vehicles"][str(engine)]
            toyland = engine in (248,249,250,251,252,255)
            first = "6" if toyland else "0"
            self.assertEqual(states[first],states[str(int(first)+1)])
            # Toyland reuses sprite numbers with replacement artwork. Those are
            # separate source families even when the direction arrays coincide.
            signature = (toyland,tuple(definition["sprites"]))
            source_families.setdefault(signature,set()).add(states[first])
            model_families.setdefault(states[first],set()).add(signature)
            if toyland:
                self.assertEqual(set(states),{"6","7"})
        self.assertTrue(all(len(names) == 1 for names in source_families.values()),"One source aircraft family acquired inconsistent aliases")
        self.assertTrue(all(len(signatures) == 1 for signatures in model_families.values()),"Different original aircraft were collapsed into one volume")
        for name,model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
            origin, step = model["origin"], model["cell_size"]
            self.assertEqual(min(origin[2]+z*step[2] for x,y,z in cells),0,name)
            supported = {next(p for p in cells if origin[2]+p[2]*step[2] == 0)}
            pending = list(supported)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in cells and point not in supported:
                        supported.add(point)
                        pending.append(point)
            self.assertEqual(len(supported),len(cells),f"Detached propeller, engine, wing, tailplane or landing gear in {name}: {len(cells-supported)} cells outside the first component")

    def test_helicopter_rotors_remain_separate_clear_and_attached_at_original_height(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("aircraft_helicopter_","aircraft_rotor_"))}
        source["bindings"] = {"infrastructure":{"3901":source["bindings"]["infrastructure"]["3901"]}}
        result = compile_catalogue(source)
        states = result["bindings"]["infrastructure"]["3901"]
        self.assertEqual(set(states),{"0","1","2","3"})
        self.assertEqual(len(set(states.values())),4)
        volumes = {}
        for name,model in result["models"].items():
            origin = [round(v*4) for v in model["origin"]]
            self.assertEqual(model["cell_size"],[0.25,0.25,0.25])
            lift = 20 if name.startswith("aircraft_rotor_") else 0
            volumes[name] = {(origin[0]+x+i,origin[1]+y,origin[2]+z+lift) for x,y,z,length,_ in model["runs"] for i in range(length)}
        for body in (name for name in volumes if name.startswith("aircraft_helicopter_")):
            for rotor in states.values():
                self.assertFalse(volumes[body]&volumes[rotor],f"Rotor intersects cabin or tail: {body}/{rotor}")
                self.assertTrue(any((x,y,z-1) in volumes[body] for x,y,z in volumes[rotor]),f"Floating rotor spindle: {body}/{rotor}")

    def test_toyland_layers_meet_at_ground_without_coplanar_wrapping_or_floating_parts(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_toy_")}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(91,110)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        floors = {name for states in result["bindings"]["house_ground"].values() for name in states.values()}
        for name,model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
            origin,step = model["origin"],model["cell_size"]
            low = [origin[d]+min(p[d] for p in cells)*step[d] for d in range(3)]
            high = [origin[d]+(max(p[d] for p in cells)+1)*step[d] for d in range(3)]
            self.assertTrue(all(0 <= low[d] < high[d] <= 16 for d in (0,1)),name)
            if name in floors:
                self.assertEqual(high[2],0,"Ground side faces must end where the gift wrapping starts")
                self.assertEqual({(x,y) for x,y,z in cells},{(x,y) for x in range(32) for y in range(32)})
                continue
            self.assertEqual(low[2],0,f"Floating or buried body/wrapping floor in {name}")
            visited = {p for p in cells if origin[2]+p[2]*step[2] == 0}
            pending = list(visited)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in cells and point not in visited:
                        visited.add(point); pending.append(point)
            self.assertEqual(len(visited),len(cells),f"Unsupported bow, glazing, pavilion storey or vessel handle in {name}: {sorted(cells-visited)[:8]}")
        for house in (107,109):
            self.assertEqual(set(result["bindings"]["houses"][str(house)]),{"1","2","3"},"Statue first states must remain genuinely empty")

    def test_tropical_flats_and_church_keep_roof_braces_setback_and_real_arcades(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_tropic_civic_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in (82,83)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        bodies,grounds = result["bindings"]["houses"],result["bindings"]["house_ground"]
        self.assertEqual(bodies["82"]["1"],bodies["82"]["2"])
        self.assertEqual(set(bodies["83"]),{"1","2","3"})
        self.assertEqual(len(set(bodies["83"].values())),1)
        self.assertTrue(all(set(states.values()) == {"mine_ground_site"} for states in grounds.values()))
        frame,finished = cells["house_tropic_civic_flats_frame"],cells["house_tropic_civic_flats"]
        self.assertIn((4,20,20),cells["house_tropic_civic_flats_site"])
        self.assertNotIn((20,4,20),cells["house_tropic_civic_flats_site"],"The first foundation wall was rotated onto the wrong source edge")
        self.assertNotIn((10,10,139),frame); self.assertIn((10,10,139),finished)
        self.assertNotIn((3,4,145),finished,"The inset top storey was stretched to the lower slab footprint")
        self.assertIn((6,7,163),finished)
        church = cells["house_tropic_civic_church"]
        self.assertNotIn((0,0,1),church); self.assertNotIn((0,0,1),finished)
        for y in (6,14,22):
            self.assertNotIn((26,y,10),church,"A lower source arcade was filled")
            self.assertNotIn((27,y,35),church,"An upper source arch lost its recess")
            self.assertIn((25,y,35),church)
        self.assertNotIn((28,14,55),church)
        self.assertIn((8,15,73),church)
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending = [p for p in volume if model["origin"][2]+p[2]*model["cell_size"][2] <= 0]
            visited = set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Unsupported apartment/church floor, window, arch or finial in {name}: {sorted(set(volume)-visited)[:8]}")

    def test_tropical_small_houses_preserve_open_frames_body_gardens_and_four_hut_plans(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_tropic_small_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(78,82)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        bodies,grounds = result["bindings"]["houses"],result["bindings"]["house_ground"]
        floor = {(x,y) for x in range(32) for y in range(32)}
        for house in range(78,82):
            self.assertEqual(set(grounds[str(house)].values()),{"mine_ground_site"},"The source body-owned garden must disappear with the building, leaving the original soil")
        for house,family,roof in ((78,"colonial",(16,15,43)),(79,"bungalow",(12,12,26)),(80,"striped",(12,15,18))):
            states = bodies[str(house)]
            self.assertEqual(states["1"],states["2"]); self.assertNotEqual(states["2"],states["3"])
            frame,finished = cells[states["1"]],cells[states["3"]]
            self.assertNotIn(roof,frame); self.assertIn(roof,finished)
            self.assertNotEqual({(x,y) for x,y,z in frame if z == 1},floor)
            self.assertEqual({(x,y) for x,y,z in finished if z == 1},floor)
        self.assertEqual(set(bodies["81"]),{str(v*4+s) for v in range(4) for s in (1,2,3)})
        hut_names = []
        for variant in range(4):
            states = [bodies["81"][str(variant*4+stage)] for stage in (1,2,3)]
            self.assertEqual(len(set(states)),1); hut_names.append(states[0])
        self.assertEqual(len(set(hut_names)),4)
        for variant,name in enumerate(hut_names):
            self.assertEqual({(x,y) for x,y,z in cells[name] if z == 1},floor)
            top = max(z for x,y,z in cells[name])
            if variant in (1,3):
                self.assertGreater(top,48)
            else:
                self.assertLess(top,30)
        self.assertNotIn((26,16,8),cells["house_tropic_small_colonial"])
        self.assertIn((24,16,8),cells["house_tropic_small_colonial"])
        self.assertNotIn((18,20,5),cells["house_tropic_small_bungalow"])
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending = [p for p in volume if model["origin"][2]+p[2]*model["cell_size"][2] <= 0]
            visited = set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Unsupported tropical wall, pane, roof or garden palm in {name}: {sorted(set(volume)-visited)[:8]}")
            if name != "mine_ground_site":
                self.assertEqual(min(model["origin"][2]+p[2]*model["cell_size"][2] for p in volume),0)

    def test_joined_gold_office_keeps_open_glass_slots_roof_well_and_permanent_gardens(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_arctic_twin_")}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(74,78)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        bodies,grounds = result["bindings"]["houses"],result["bindings"]["house_ground"]
        for plain,snow in ((74,76),(75,77)):
            for stage in range(3):
                self.assertEqual(bodies[str(plain)][str(stage)],bodies[str(snow)][str(stage)])
            self.assertEqual(grounds[str(plain)],grounds[str(snow)])
            self.assertEqual(len(set(grounds[str(plain)].values())),1)
            self.assertEqual(bodies[str(plain)]["1"],bodies[str(plain)]["2"])
            a,b = (cells[bodies[str(house)]["3"]] for house in (plain,snow))
            self.assertEqual(set(a),set(b)); self.assertNotEqual(a,b)
        for north,south in ((74,75),(76,77)):
            for stage in (1,2,3):
                a,b = (cells[bodies[str(house)][str(stage)]] for house in (north,south))
                self.assertEqual({(y,z) for x,y,z in a if x == 31},{(y,z) for x,y,z in b if x == 0},"The two-tile gold office lost its original physicalX seam")
        for part,x in (("north",20),("south",10)):
            frame,finished = (cells[f"house_arctic_twin_{part}{suffix}"] for suffix in ("_frame",""))
            self.assertNotIn((x,26,30),frame); self.assertIn((x,26,30),finished)
            self.assertNotIn((x,16,69),frame); self.assertIn((x,16,69),finished)
        self.assertTrue(any(z > 73 for x,y,z in cells["house_arctic_twin_north"]))
        self.assertFalse(any(z > 73 for x,y,z in cells["house_arctic_twin_south"]),"The source's single roof plant was duplicated on its secondary tile")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Unsupported gold frame, glass, coping or roof plant in {name}: {sorted(set(volume)-visited)[:8]}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_balcony_office_and_rib_tower_keep_distinct_construction_heights_and_facades(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_arctic_final_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(70,74)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        bodies,grounds = result["bindings"]["houses"],result["bindings"]["house_ground"]
        for plain,snow in ((70,71),(72,73)):
            self.assertEqual(bodies[str(plain)]["0"],bodies[str(snow)]["0"])
            self.assertEqual(bodies[str(plain)]["1"],bodies[str(snow)]["1"])
            self.assertEqual(grounds[str(plain)],grounds[str(snow)])
            a,b = (cells[bodies[str(house)]["3"]] for house in (plain,snow))
            self.assertEqual(set(a),set(b)); self.assertNotEqual(a,b)
        for house in (70,71):
            self.assertEqual(bodies[str(house)]["2"],bodies[str(house)]["3"])
            self.assertTrue(all(grounds[str(house)][str(stage)] == "mine_ground_site" for stage in range(3)))
        for house in (72,73):
            self.assertEqual(bodies[str(house)]["1"],bodies[str(house)]["2"])
            self.assertLess(max(z for x,y,z in cells[bodies[str(house)]["2"]]),21)
            self.assertGreater(max(z for x,y,z in cells[bodies[str(house)]["3"]]),69)
            self.assertEqual(grounds[str(house)]["1"],grounds[str(house)]["3"])
        balcony = cells["house_arctic_final_balcony"]
        self.assertNotIn((30,16,18),balcony); self.assertIn((20,20,18),balcony)
        self.assertNotIn((15,15,51),cells["house_arctic_final_balcony_frame"])
        self.assertIn((15,15,50),balcony)
        self.assertNotIn((17,17,19),cells["house_arctic_final_rib_frame"])
        tower = cells["house_arctic_final_rib"]
        self.assertEqual(result["materials"][tower[(28,10,20)]-1][1],source["materials"]["arctic_rib_glass"][1],"An orthogonal rib brush painted the glass side wall solid")
        self.assertEqual(result["materials"][tower[(10,28,20)]-1][3],source["materials"]["arctic_rib_glass"][3])
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Unsupported balcony, fascia, glass or colonnade in {name}: {sorted(set(volume)-visited)[:8]}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_arctic_hotel_keeps_two_tile_roof_seams_body_owned_paving_and_empty_sites(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_arctic_hotel_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(66,70)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        bodies,grounds = result["bindings"]["houses"],result["bindings"]["house_ground"]
        for plain,snow in ((66,68),(67,69)):
            self.assertEqual(set(bodies[str(plain)]),{"1","2","3"})
            self.assertEqual(set(bodies[str(snow)]),{"1","2","3"})
            self.assertEqual(bodies[str(plain)]["1"],bodies[str(snow)]["1"])
            self.assertEqual(grounds[str(plain)],grounds[str(snow)])
            for house in (plain,snow):
                self.assertEqual(bodies[str(house)]["2"],bodies[str(house)]["3"])
                self.assertTrue(any(z > 1 for x,y,z in cells[grounds[str(house)]["0"]]))
                self.assertTrue(all(grounds[str(house)][str(stage)] == "mine_ground_site" for stage in (1,2,3)),"The source body-owned paving must not become an independent ground")
            a,b = (cells[bodies[str(house)]["3"]] for house in (plain,snow))
            self.assertEqual(set(a),set(b)); self.assertNotEqual(a,b)
        for north,south in ((66,67),(68,69)):
            for stage in (1,2,3):
                a,b = (cells[bodies[str(house)][str(stage)]] for house in (north,south))
                seam_a = {(x,z) for x,y,z in a if y == 31}
                seam_b = {(x,z) for x,y,z in b if y == 0}
                self.assertEqual(seam_a,seam_b,f"The hotel structure/roof/foreground seam is broken in {north}/{stage}")
                self.assertTrue(any(z > 30 for x,z in seam_a) if stage > 1 else any(z > 5 for x,z in seam_a))
        self.assertNotIn((12,14,26),cells["house_arctic_hotel_north_frame"])
        self.assertIn((12,14,40),cells["house_arctic_hotel_north"])
        self.assertNotIn((18,18,20),cells["house_arctic_hotel_south"],"The source's lower rear setback became a full-width upper storey")
        self.assertNotIn((12,18,40),cells["house_arctic_hotel_south"],"The main roof was stretched over the lower south pavilion")
        for part in ("north","south"):
            self.assertFalse(any(x >= 30 and z > 2 for x,y,z in cells[f"house_arctic_hotel_{part}"]),"The facade/roof must leave the original foreground planting strip exposed")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Detached hotel masonry, window, veranda or roof in {name}: {sorted(set(volume)-visited)[:8]}")
            self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})

    def test_small_arctic_house_and_corner_shop_preserve_source_snow_and_empty_stage_rules(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_arctic_late_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(62,66)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        bodies,grounds = result["bindings"]["houses"],result["bindings"]["house_ground"]
        for stage in range(3):
            self.assertEqual(bodies["62"][str(stage)],bodies["63"][str(stage)])
            self.assertEqual(grounds["62"][str(stage)],"mine_ground_site")
            self.assertEqual(grounds["63"][str(stage)],"mine_ground_site")
        for house in (64,65):
            self.assertEqual(set(bodies[str(house)]),{"1","2","3"},"The source's absent first shop body acquired geometry")
            self.assertEqual(len(set(bodies[str(house)].values())),1)
            self.assertEqual(set(grounds[str(house)].values()),{"mine_ground_site"})
        for family in ("small","corner"):
            a,b = (cells[f"house_arctic_late_{family}{suffix}"] for suffix in ("","_snow"))
            self.assertEqual(set(a),set(b)); self.assertNotEqual(a,b)
        self.assertNotIn((9,10,29),cells["house_arctic_late_small_frame"])
        self.assertIn((9,10,29),cells["house_arctic_late_small"])
        self.assertNotIn((9,17,5),cells["house_arctic_late_small_frame"])
        self.assertIn((7,21,9),cells["house_arctic_late_small"],"The low porch roof lost its actual support")
        corner = cells["house_arctic_late_corner"]
        self.assertNotIn((26,26,6),corner,"The chamfered corner entrance was filled")
        self.assertNotIn((28,28,60),corner,"The corner was replaced with an uncut box")
        self.assertIn((26,26,11),corner)
        self.assertEqual(corner[(26,26,11)],cells["house_arctic_late_corner_snow"][(26,26,11)],"Roof snow must preserve the red-white entrance canopy")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Unsupported porch, window, cornice, canopy or chimney in {name}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_arctic_shop_and_church_keep_ground_owned_sites_hollow_roof_and_late_glazing(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("house_arctic_shop","house_arctic_church")) or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(58,62)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for plain,snow in ((58,59),(60,61)):
            a,b = (result["bindings"]["houses"][str(house)] for house in (plain,snow))
            self.assertEqual(set(a),{"1","2","3"}); self.assertEqual(set(b),set(a))
            self.assertEqual(a["1"],b["1"])
            self.assertEqual(a["2"],a["3"]); self.assertEqual(b["2"],b["3"])
            self.assertEqual(set(cells[a["3"]]),set(cells[b["3"]]))
            self.assertNotEqual(cells[a["3"]],cells[b["3"]])
            for house in (plain,snow):
                grounds = result["bindings"]["house_ground"][str(house)]
                self.assertTrue(any(z > 1 for x,y,z in cells[grounds["0"]]),"The original ground-owned early walls/piers disappeared")
                self.assertEqual(grounds["1"],"mine_ground_site"); self.assertEqual(grounds["2"],"mine_ground_site")
        frame,finished = cells["house_arctic_church_frame"],cells["house_arctic_church"]
        self.assertNotIn((12,30,28),frame); self.assertIn((12,30,28),finished)
        self.assertNotIn((18,25,40),finished,"The steep roof became a filled triangular placeholder")
        self.assertIn((6,25,25),finished); self.assertIn((29,25,25),finished)
        self.assertNotIn((30,16,39),frame); self.assertIn((30,16,39),finished,"The original late annex roof is missing")
        self.assertEqual(finished[(29,25,25)],cells["house_arctic_church_snow"][(29,25,25)],"Roof snow must not replace the tall stone side supports")
        shop = cells["house_arctic_shop"]
        self.assertNotIn((29,15,5),shop); self.assertIn((27,15,5),shop)
        self.assertIn((30,16,20),shop,"The small original entrance gable roof is missing")
        self.assertNotIn((25,16,40),shop); self.assertIn((24,16,40),shop,"The loft glazing must remain exposed above the porch roof")
        self.assertNotIn((1,10,8),cells["house_arctic_shop_frame"],"The incomplete rear frame became a finished perimeter wall")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Unsupported roof, frame, glazing, steps or masonry in {name}: {sorted(set(volume)-visited)[:8]}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_log_cabin_layouts_keep_distinct_plans_chimney_ground_and_completed_snow(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_cabin_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in (56,57)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for house in (56,57):
            for category in ("houses","house_ground"):
                states = result["bindings"][category][str(house)]
                self.assertEqual(set(states),set(map(str,range(16))))
                for stage in range(4):
                    self.assertEqual(states[str(stage)],states[str(4+stage)])
                    self.assertEqual(states[str(8+stage)],states[str(12+stage)])
            self.assertNotEqual(result["bindings"]["houses"][str(house)]["3"],result["bindings"]["houses"][str(house)]["11"])
        for family in ("large","small"):
            plain,snow = cells[f"house_cabin_{family}"],cells[f"house_cabin_{family}_snow"]
            self.assertEqual(set(plain),set(snow)); self.assertNotEqual(plain,snow)
        for family,point in (("large",(28,20,0)),("small",(10,29,0))):
            self.assertEqual(cells[f"house_cabin_{family}_ground"][point],cells[f"house_cabin_{family}_ground_snow"][point],"The original bare approach must remain visible through the snow")
            plain,snow = cells[f"house_cabin_{family}_ground"],cells[f"house_cabin_{family}_ground_snow"]
            self.assertEqual(set(plain),set(snow)); self.assertNotEqual(plain,snow)
        for variant in range(4):
            for stage in range(3):
                key = str(variant*4+stage)
                self.assertEqual(result["bindings"]["houses"]["56"][key],result["bindings"]["houses"]["57"][key])
                self.assertEqual(result["bindings"]["house_ground"]["56"][key],"mine_ground_site")
        large_colours = {c for m in cells["house_cabin_large"].values() for c in result["materials"][m-1]}
        small_colours = {c for m in cells["house_cabin_small"].values() for c in result["materials"][m-1]}
        self.assertTrue(large_colours & set(range(122,127)))
        self.assertFalse(small_colours & set(range(122,127)),"The smaller original cabin acquired a chimney")
        self.assertNotIn((14,15,3),cells["house_cabin_large"])
        self.assertIn((14,13,3),cells["house_cabin_large"])
        self.assertNotIn((11,12,3),cells["house_cabin_small"])
        self.assertIn((23,7,8),cells["house_cabin_large"])
        self.assertNotIn((23,7,12),cells["house_cabin_large"],"The lower cabin roof was raised into the main roof")
        self.assertIn((7,20,8),cells["house_cabin_small"])
        self.assertNotIn((7,20,12),cells["house_cabin_small"],"The small cabin lost its separate low roof")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Detached cabin wall, roof, chimney or timber stack in {name}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_ribbed_and_setback_towers_preserve_roof_voids_real_setbacks_and_source_snow(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_arctic_tower_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(52,56)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for plain,snow in ((52,53),(54,55)):
            a,b = (result["bindings"]["houses"][str(house)] for house in (plain,snow))
            self.assertEqual(a["0"],b["0"]); self.assertEqual(a["1"],b["1"])
            self.assertEqual(a["2"],a["3"]); self.assertEqual(b["2"],b["3"])
            self.assertEqual(set(cells[a["3"]]),set(cells[b["3"]]))
            self.assertNotEqual(cells[a["3"]],cells[b["3"]])
            self.assertEqual(result["bindings"]["house_ground"][str(plain)],result["bindings"]["house_ground"][str(snow)])
            for name in (a["1"],a["3"],b["3"]):
                colours = {c for material in cells[name].values() for c in result["materials"][material-1]}
                self.assertTrue(colours & set(range(198,206)),f"{name} lost the original recolourable vertical ribs")
        frame,finished = cells["house_arctic_tower_ribbed_frame"],cells["house_arctic_tower_ribbed"]
        self.assertNotIn((15,15,73),frame); self.assertIn((15,15,73),finished)
        self.assertIn((9,27,44),finished); self.assertIn((25,27,37),finished)
        self.assertNotIn((9,27,45),finished); self.assertNotIn((25,27,38),finished)
        self.assertNotIn((17,27,10),finished,"The opening between the source's two lower wings was filled")
        frame,finished = cells["house_arctic_tower_setback_frame"],cells["house_arctic_tower_setback"]
        self.assertNotIn((15,15,64),frame); self.assertIn((15,15,58),frame)
        self.assertIn((4,4,71),finished); self.assertIn((12,12,96),finished)
        self.assertNotIn((4,4,73),finished,"The upper pavilion was stretched to the lower tower's footprint")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Unsupported rib, roof, floor or pavilion in {name}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_face_paint_retains_voids_and_unselected_material_faces(self):
        source = {"format":1,"materials":{"base":[1,2,3,4,5,6],"trim":[10,11,12,13,14,15]},"models":{
            "plain":{"size":[3,2,2],"ops":[["box","base",0,0,0,1,2,2]]},
            "painted":{"extends":"plain","ops":[["face_paint","trim",12,0,0,0,3,2,2]]}
        },"bindings":{}}
        result = compile_catalogue(source)
        a,b = (result["models"][name] for name in ("plain","painted"))
        self.assertEqual(a["occupied"],b["occupied"])
        self.assertEqual([run[:4] for run in a["runs"]],[run[:4] for run in b["runs"]])
        for run in b["runs"]:
            self.assertEqual(result["materials"][run[4]-1],[1,2,12,13,5,6])
        for mask in (0,64,-1,True):
            source["models"]["painted"]["ops"][0][2] = mask
            with self.assertRaises(ValueError):
                compile_catalogue(source)

    def test_arctic_cottage_and_glass_office_keep_individual_snow_timing_and_open_structures(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_arctic_next_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(48,52)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        bindings = result["bindings"]["houses"]
        self.assertEqual(bindings["48"]["2"],bindings["49"]["2"],"The cottage gained snow before its completed source state")
        self.assertNotEqual(bindings["50"]["2"],bindings["51"]["2"],"The snowy office lost its genuine stage2 snow")
        for plain,snow in ((48,49),(50,51)):
            for stage in ("0","1"):
                self.assertEqual(bindings[str(plain)][stage],bindings[str(snow)][stage])
            a,b = (cells[bindings[str(house)]["3"]] for house in (plain,snow))
            self.assertEqual(set(a),set(b),"Snow changed the source structural silhouette")
            self.assertNotEqual(a,b)
            for house in (plain,snow):
                ground = result["bindings"]["house_ground"][str(house)]
                self.assertTrue(all(ground[str(stage)] == "mine_ground_site" for stage in range(3)))
        frame,finished = cells["house_arctic_next_cottage_frame"],cells["house_arctic_next_cottage"]
        self.assertNotIn((16,11,3),frame)
        self.assertIn((16,11,3),finished)
        self.assertNotIn((17,14,3),finished)
        self.assertIn((15,14,3),finished)
        self.assertIn((24,14,0),finished,"The porch stair no longer reaches the original ground")
        office = cells["house_arctic_next_glass"]
        self.assertNotIn((12,12,32),office,"The glass office became a solid placeholder")
        self.assertNotIn((1,8,4),cells["house_arctic_next_glass_frame"],"The construction bay was filled")
        self.assertIn((30,10,18),office,"The source lower front wing is missing")
        self.assertNotIn((30,17,4),office,"The front-wing entrance lost its recess")
        for p in ((1,8,4),(5,5,4),(25,8,4),(5,30,4)):
            self.assertTrue(set(result["materials"][office[p]-1]) & set(range(128,134)),"A grid brush filled an entire office facade instead of its thin mullions")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Detached frame, antenna, porch or roof in {name}: {sorted(set(volume)-visited)[:8]}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_arctic_low_houses_keep_open_construction_and_completed_only_snow_and_paving(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_arctic_low_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in range(44,48)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for plain,snow in ((44,45),(46,47)):
            a,b = (result["bindings"]["houses"][str(house)] for house in (plain,snow))
            for stage in ("0","1","2"):
                self.assertEqual(a[stage],b[stage],"Snow was applied before the original completed state")
            self.assertEqual(a["2"],a["3"])
            self.assertEqual(set(cells[a["3"]]),set(cells[b["3"]]),"Snow changed the original structural footprint")
            self.assertNotEqual(cells[a["3"]],cells[b["3"]])
            for house in (plain,snow):
                grounds = result["bindings"]["house_ground"][str(house)]
                self.assertTrue(all(grounds[str(stage)] == "mine_ground_site" for stage in range(3)))
            frame,finished = cells[a["1"]],cells[a["3"]]
            self.assertNotIn((20,9,5),frame,"The unfinished source window gained glazing")
            self.assertIn((20,9,5),finished)
            self.assertNotIn((21,17,4),finished,"The recessed entrance became a flat wall")
            self.assertIn((19,17,4),finished)
            self.assertNotIn((12,17,7),frame,"The open construction interior was filled")
        for name in ("house_arctic_low_ground","house_arctic_low_ground_snow"):
            self.assertIn((27,7,1),cells[name],"The original rear stack lost its raised volume")
            self.assertNotIn((27,27,1),cells[name],"The rear stack moved onto the entrance side")
        for name,volume in cells.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][d]+p[d]*model["cell_size"][d] < 16 for p in volume for d in (0,1)))
            pending,visited = [p for p in volume if p[2] == 0],set()
            while pending:
                p = pending.pop()
                if p in visited:
                    continue
                visited.add(p); x,y,z = p
                pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in volume and q not in visited)
            self.assertEqual(len(visited),len(volume),f"Detached roof, dormer, window or joist in {name}")
            if "ground" in name:
                self.assertEqual({(x,y) for x,y,z in volume if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_shopping_mall_preserves_joined_footprints_ground_owned_structures_and_empty_states(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_mall_")}
        source["bindings"] = {category:{str(house):states for house in range(40,44) if (states := source["bindings"][category].get(str(house))) is not None} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        self.assertNotIn("43",result["bindings"]["houses"],"The source's ground-owned south pavilion gained an invented body")
        for house in (41,42):
            self.assertEqual(set(result["bindings"]["houses"][str(house)]),{"2","3"})
        for house in range(40,44):
            ground = result["bindings"]["house_ground"][str(house)]
            self.assertEqual(ground["0"],ground["1"])
            self.assertEqual(ground["2"],ground["3"])
            for stage in range(4):
                floor = cells[ground[str(stage)]]
                self.assertEqual({(x,y) for x,y,z in floor if z == 0},{(x,y) for x in range(32) for y in range(32)})
                name = result["bindings"]["houses"].get(str(house),{}).get(str(stage))
                body = cells[name] if name else {}
                self.assertFalse(set(body) & set(floor),f"Mall{house} stage{stage} has coincident source layers")
                combined = dict(floor); combined.update(body)
                self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in combined),"A mall part escaped its original tile")
                pending,visited = [p for p in combined if p[2] == 0],set()
                while pending:
                    p = pending.pop()
                    if p in visited:
                        continue
                    visited.add(p); x,y,z = p
                    pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in combined and q not in visited)
                self.assertEqual(len(visited),len(combined),f"Mall{house} stage{stage} has unsupported glazing, roof ribs or piers")
        # The long original L-shaped roof/footing crosses the north/east/west tile
        # boundaries. Four isolated pyramids can match overall bounds but lose it.
        for stage in (0,2):
            joined = {}
            for house in (40,41,42):
                ground = cells[result["bindings"]["house_ground"][str(house)][str(stage)]]
                body_name = result["bindings"]["houses"].get(str(house),{}).get(str(stage))
                joined[house] = set(ground) | (set(cells[body_name]) if body_name else set())
            north = joined[40]
            for house,axis in ((41,1),(42,0)):
                a = {tuple(p[d] for d in range(3) if d != axis) for p in north if p[axis] == 31 and p[2] > 0}
                b = {tuple(p[d] for d in range(3) if d != axis) for p in joined[house] if p[axis] == 0 and p[2] > 0}
                self.assertTrue(a and b)
                self.assertEqual(a,b,f"Mall{house} stage{stage} breaks the shared wing/roof at the tile boundary")
            self.assertNotIn((24,24,1),north,"The original inner courtyard was filled by a square pavilion")
        east = cells["house_mall_41_ground"]
        self.assertNotIn((8,28,6),east)
        self.assertIn((8,26,6),east,"The source's recessed entrance became a flat facade")
        south = cells["house_mall_43_ground"]
        self.assertTrue(any(z >= 26 for x,y,z in south),"The source ground-owned pavilion lost its roof")
        colours = {c for name,volume in cells.items() if "site" not in name for material in volume.values() for c in result["materials"][material-1]}
        self.assertTrue({128,131,134,192,193,194,195,184} <= colours)

    def test_navigation_buoy_keeps_waterline_contact_open_cage_and_exposed_beacon(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("water_buoy")}
        source["bindings"] = {"infrastructure":{"693":source["bindings"]["infrastructure"]["693"]}}
        result = compile_catalogue(source)
        model = result["models"]["water_buoy"]
        cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertEqual(model["origin"],[5,5,-0.5])
        self.assertTrue((12,12,18) not in cells,"The open buoy cage became an opaque box")
        self.assertTrue(all(0 <= model["origin"][axis]+p[axis]*model["cell_size"][axis] < 16 for p in cells for axis in (0,1)))
        solid = {p:m for p,m in cells.items() if not set(result["materials"][m-1]) & set(range(250,255))}
        pending,visited = [next(iter(solid))],set()
        while pending:
            p = pending.pop()
            if p in visited:
                continue
            visited.add(p); x,y,z = p
            pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in solid and q not in visited)
        self.assertEqual(len(visited),len(solid),"A buoy leg, brace or lantern became detached")
        self.assertTrue(all(p[2] == 1 for p in cells if p not in solid),"Original foam left the water plane")
        colours = {c for m in cells.values() for c in result["materials"][m-1]}
        self.assertTrue({239,240,250,251,252,253,254} <= colours)
        beacon = [p for p,m in cells.items() if 240 in result["materials"][m-1]]
        self.assertTrue(beacon)
        self.assertTrue(any((x,y+1,z) not in cells for x,y,z in beacon),"The original beacon was buried inside an opaque lantern")
        toy = result["models"]["water_buoy_toyland"]
        toy_cells = {(x+i,y,z):m for x,y,z,length,m in toy["runs"] for i in range(length)}
        self.assertTrue((12,12,18) in toy_cells,"The original solid Toyland marker was replaced with the ordinary open frame")
        toy_colours = {c for m in toy_cells.values() for c in result["materials"][m-1]}
        self.assertTrue({193,206,164,239,240,250,251,252,253,254} <= toy_colours)
        self.assertEqual(toy["origin"],model["origin"])

    def test_cinema_keeps_empty_first_state_open_entrance_and_original_lamps(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_cinema_") or name == "mine_ground_site"}
        source["bindings"] = {category:{"39":source["bindings"][category]["39"]} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        self.assertEqual(result["bindings"]["houses"]["39"],{str(stage):"house_cinema_39" for stage in (1,2,3)})
        model = result["models"]["house_cinema_39"]
        cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertTrue((9,25,8) not in cells and (9,23,8) in cells,"The recessed entrance was replaced with a flat front wall")
        colours = {colour for material in cells.values() for colour in result["materials"][material-1]}
        self.assertTrue({241,242,243,244} <= colours)
        self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells))
        pending,visited = [p for p in cells if p[2] == 0],set()
        while pending:
            p = pending.pop()
            if p in visited:
                continue
            visited.add(p); x,y,z = p
            pending.extend(q for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if q in cells and q not in visited)
        self.assertEqual(len(visited),len(cells),"A pier, rooflight, step or lamp became detached")
        floor = result["models"]["house_cinema_ground"]
        self.assertEqual({(x+i,y) for x,y,z,length,material in floor["runs"] for i in range(length)},{(x,y) for x in range(32) for y in range(32)})
        self.assertEqual(floor["origin"][2]+floor["cell_size"][2],0)

    def test_toyland_tree_families_keep_real_lifecycles_open_frames_and_source_recolouring(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        bases = range(1947,2010,7)
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("tree_toy_")}
        source["bindings"] = {"trees":{str(base):source["bindings"]["trees"][str(base)] for base in bases}}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for base in bases:
            self.assertEqual(set(result["bindings"]["trees"][str(base)]),set(map(str,range(7))))
        for name,volume in cells.items():
            self.assertTrue(any(z == 0 for x,y,z in volume),f"Missing ground contact in {name}")
            pending = [point for point in volume if point[2] == 0]
            visited = set()
            while pending:
                point = pending.pop()
                if point in visited:
                    continue
                visited.add(point)
                x,y,z = point
                pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in volume and p not in visited)
            self.assertEqual(len(visited),len(volume),f"Detached candy, cloth, rib, disc or collar in {name}; sample {sorted(set(volume)-visited)[:10]}")
        def palette(name):
            return {colour for material in cells[name].values() for colour in result["materials"][material-1]}
        for family in ("cone","parasol","umbrella","globe"):
            self.assertFalse(palette(f"tree_toy_{family}_06") & set(range(198,206)),f"The original bare {family} still has company foliage")
        for family in ("lollipop","mushroom","striped","tiers"):
            self.assertTrue(palette(f"tree_toy_{family}_06") & set(range(198,206)),f"The original last {family} state incorrectly lost all its coloured structure")
        self.assertFalse(any(palette(f"tree_toy_cylinder_{stage:02}") & set(range(198,206)) for stage in range(7)),"The original silver/black cylinder acquired company colours")
        self.assertTrue(set(cells["tree_toy_umbrella_06"]) < set(cells["tree_toy_umbrella_05"]) < set(cells["tree_toy_umbrella_04"]) < set(cells["tree_toy_umbrella_03"]),"Umbrella panel loss became a recolour-only alias")
        self.assertTrue((30,24,25) not in cells["tree_toy_umbrella_03"],"The open umbrella became a filled cone")
        self.assertTrue((30,24,40) not in cells["tree_toy_parasol_03"],"The shallow parasol lost its open underside")
        cloth_tops = [max(z for (x,y,z),material in cells[f"tree_toy_parasol_{stage:02}"].items() if set(result["materials"][material-1]) & set(range(198,206))) for stage in (3,4,5)]
        self.assertGreater(cloth_tops[0],cloth_tops[1]); self.assertGreater(cloth_tops[1],cloth_tops[2])
        tiers = [[(35,24,z) in cells[f"tree_toy_tiers_{stage:02}"] for z in (22,44,64)] for stage in range(7)]
        self.assertEqual(tiers,[[False,False,False],[True,False,False],[True,True,False],[True,True,True],[True,True,True],[False,True,True],[False,False,True]])
        self.assertTrue(all((35,24,z) not in cells["tree_toy_tiers_03"] for z in (32,52)),"Separate disc gaps were filled")

    def test_radial_material_sectors_preserve_voids_and_filter_shedding(self):
        source = {"format":1,"materials":{"blue":198,"gold":65},"models":{
            "ring":{"size":[12,12,8],"ops":[["lathe","blue",[6,6],[[0,5,3],[6,5,3]]]]},
            "painted":{"extends":"ring","ops":[["radial_paint","gold",[6,6],0,6,4,1]]},
            "shed":{"extends":"painted","ops":[["radial_erase",[6,6],0,6,4,3,"blue"]]}
        },"bindings":{}}
        result = compile_catalogue(source)
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        self.assertEqual(set(cells["ring"]),set(cells["painted"]))
        self.assertNotIn((6,6,3),cells["painted"],"A radial colour brush filled an original aperture")
        for point,material in cells["painted"].items():
            x,y,z = point
            self.assertEqual(material,2 if x >= 6 and y >= 6 else 1)
            self.assertEqual(point in cells["shed"],not (x < 6 and y >= 6))
        for op in (["radial_paint","gold",[6,6],0,6,0,1],
                   ["radial_paint","gold",[6,6],0,6,33,1],
                   ["radial_erase",[6,6],6,0,4,1],
                   ["radial_erase",[6,6],0,6,4,16],
                   ["radial_erase",[6,6],0,6,4,1,"missing"]):
            source["models"]["shed"]["ops"] = [op]
            with self.assertRaises(ValueError):
                compile_catalogue(source)

    def test_suspended_and_arctic_houses_preserve_source_states_snow_and_ground_contacts(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_next_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):source["bindings"][category][str(house)] for house in (36,37,38)} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for house in (36,37,38):
            states = result["bindings"]["houses"][str(house)]
            self.assertTrue(all(str(state) not in states for state in (0,4,8,12)),"An absent original first body was invented")
            self.assertEqual(states["1"],states["2"],"Source-identical early states stopped sharing geometry")
            self.assertEqual(result["bindings"]["house_ground"][str(house)]["0"],"mine_ground_site")
        frame,finished = volumes["house_next_cable_frame"],volumes["house_next_cable"]
        self.assertLess(set(frame),set(finished))
        self.assertNotIn((32,32,60),frame,"The original two-mast state gained a fabricated building")
        self.assertNotIn((32,32,60),finished,"The round glazed office lost its real interior")
        self.assertIn((32,20,60),finished)
        self.assertTrue(all((31,y,108) in finished for y in range(4,60)),"The suspension beam between the masts disappeared")
        self.assertNotIn((31,32,108),frame)
        for family in ("arctic_villa","arctic_narrow","garden_villa","garden_narrow"):
            plain,snow = volumes[f"house_next_{family}"],volumes[f"house_next_{family}_snow"]
            self.assertEqual(set(plain),set(snow),"Snow changed the original matching footprint/roof silhouette")
            self.assertNotEqual(plain,snow)
            palette = {c for material in snow.values() for c in result["materials"][material-1]}
            self.assertTrue({211,212,213,214} <= palette,"The original snow palette was flattened")
        for name,cells in volumes.items():
            model = result["models"][name]
            self.assertTrue(all(0 <= model["origin"][axis]+point[axis]*model["cell_size"][axis] < 16 for point in cells for axis in (0,1)),f"{name} left its original tile")
            if "ground" in name or "garden" in name:
                self.assertEqual({(x,y) for x,y,z in cells if z == 0},{(x,y) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)
            remaining = set(cells)
            while remaining:
                visited,pending = set(),[next(iter(remaining))]
                while pending:
                    point = pending.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in remaining and p not in visited)
                self.assertTrue(any(z == 0 for x,y,z in visited),f"Detached roof/cable/porch/hedge in {name}: {len(visited)} cells, sample {sorted(visited)[:12]}")
                remaining -= visited

    def test_open_wagons_preserve_cargo_voids_climate_variants_and_rail_contact(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("wagon_open_")}
        source["bindings"] = {"vehicles":{engine:states for engine,states in source["bindings"]["vehicles"].items() if any(name.startswith("wagon_open_") for name in states.values())}}
        result,definitions = compile_catalogue(source),vehicle_definitions()
        self.assertEqual(len(result["bindings"]["vehicles"]),30)
        for engine,states in result["bindings"]["vehicles"].items():
            definition = definitions[engine]
            for state,name in states.items():
                other = states[str(int(state)^1)]
                self.assertEqual(name == other,definition["sprites"] == definition["loaded_sprites"],f"Original cargo-state selection was lost for wagon {engine}")
        for engine in (39,69,101):
            self.assertEqual(set(result["bindings"]["vehicles"][str(engine)]),{"2","3"},"Arctic paper artwork leaked into other climates")
        for engine in (40,41,42,43,70,71,72,73,102,103,104,105):
            self.assertEqual(set(result["bindings"]["vehicles"][str(engine)]),{"4","5"})
        for first,second in ((59,91),(63,95),(64,96),(65,97),(66,98),(69,101),(70,102),(41,71),(41,103),(42,72),(42,104),(43,73),(43,105)):
            self.assertEqual(result["bindings"]["vehicles"][str(first)],result["bindings"]["vehicles"][str(second)])
            self.assertEqual(definitions[str(first)]["sprites"],definitions[str(second)]["sprites"])
            self.assertEqual(definitions[str(first)]["loaded_sprites"],definitions[str(second)]["loaded_sprites"])
        volumes = {}
        for name,model in result["models"].items():
            cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            self.assertEqual(model["origin"][2],0.5,"Wagon support no longer meets the original running-rail height")
            contact_y = {model["origin"][1]+(y+0.5)*model["cell_size"][1] for x,y,z in cells if z == 0}
            self.assertEqual(contact_y,{-1.375,-1.125,1.125,1.375},name)
            visited = {next(iter(cells))}
            pending = list(visited)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in cells and point not in visited:
                        visited.add(point); pending.append(point)
            self.assertEqual(len(visited),len(cells),f"Detached bogie, restraint, canopy or cargo in {name}: {sorted(cells.keys()-visited)[:8]}")
            if name.endswith("_empty"):
                self.assertNotIn((20,6,20),cells,"A genuinely empty deck/bin became a filled placeholder")
            if "steel" in name and name.endswith("_loaded"):
                for x in (8,20,32):
                    self.assertTrue(all((x,6,z) not in cells for z in range(12,32)),"A steel coil lost its actual through-hole")
            if "paper" in name:
                self.assertIn((20,6,35),cells,"The source canopy disappeared")
                self.assertNotIn((20,6,34),cells,"The raised paper canopy merged into its cargo")
        self.assertIn((14,1,25),volumes["wagon_open_wood_empty"])
        self.assertNotIn((14,1,25),volumes["wagon_open_wood_tropic_empty"],"Tropical wood acquired the normal middle stakes")
        self.assertNotEqual(volumes["wagon_open_coal_empty"][(20,1,18)],volumes["wagon_open_coal_arctic_empty"][(20,1,18)],"Arctic copper-colour tub aliased the grey temperate artwork")
        latex = volumes["wagon_open_rubber_loaded"]
        self.assertTrue(all((x,y,21) in latex and (x,y,22) not in latex for x in range(4,37) for y in range(3,9)),"Liquid latex must retain its level surface below the rim")

    def test_toy_wagons_keep_independent_source_states_and_real_cargo_openings(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("wagon_toy_")}
        source["bindings"] = {"vehicles":{engine:states for engine,states in source["bindings"]["vehicles"].items() if any(name.startswith("wagon_toy_") for name in states.values())}}
        result,definitions = compile_catalogue(source),vehicle_definitions()
        self.assertEqual(len(result["models"]),16)
        self.assertEqual(len(result["bindings"]["vehicles"]),24)
        for engine,states in result["bindings"]["vehicles"].items():
            self.assertEqual(set(states),{"6","7"},"Toyland art cannot be selected from overlapping ordinary sprite numbers")
            self.assertNotEqual(states["6"],states["7"],"A loaded Toyland wagon lost its independent cargo volume")
            self.assertNotEqual(definitions[engine]["sprites"],definitions[engine]["loaded_sprites"])
        for first in (44,45,46,47,48,51,52,53):
            for second in (first+30,first+62):
                self.assertEqual(result["bindings"]["vehicles"][str(first)],result["bindings"]["vehicles"][str(second)])
                self.assertEqual(definitions[str(first)]["sprites"],definitions[str(second)]["sprites"])
                self.assertEqual(definitions[str(first)]["loaded_sprites"],definitions[str(second)]["loaded_sprites"])
        volumes = {}
        for name,model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
            volumes[name] = cells
            self.assertEqual(model["origin"][2]+min(z for x,y,z in cells)*model["cell_size"][2],0.5)
            self.assertEqual({model["origin"][1]+(y+0.5)*model["cell_size"][1] for x,y,z in cells if z == 0},{-1.375,-1.125,1.125,1.375})
            visited = {next(iter(cells))}; pending = list(visited)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in cells and point not in visited:
                        visited.add(point); pending.append(point)
            self.assertEqual(visited,cells,f"Unsupported Toyland tank frame, canopy, bubble or cargo: {name}")
            if name.endswith("_empty"):
                self.assertNotIn((20,6,20),cells)
        for family in ("battery","drinks","plastic"):
            for x in (8,20,32):
                self.assertIn((x,6,23),volumes[f"wagon_toy_{family}_loaded"],"The original three solid upright cargo pieces became hollow/absent")
        for x in (8,20,32):
            self.assertNotIn((x,5,22),volumes["wagon_toy_bubble_loaded"],"Bubble interiors must stay see-through")
        cola = volumes["wagon_toy_cola_empty"]
        self.assertFalse(any((x,y,20) in cola for x in (8,19,30) for y in (1,6,10)),"Opaque cola shell hides its originally visible empty/load state")
        self.assertIn((20,6,24),volumes["wagon_toy_cola_loaded"])
        self.assertNotIn((20,6,25),volumes["wagon_toy_cola_loaded"],"The cola liquid rose beyond its level fill surface")

    def test_closed_wagons_preserve_climate_art_cargo_aliases_and_open_ventilation(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        engines = (27,28,30,31,32,37,38,49,50,57,58,60,61,62,67,68,79,80,89,90,92,93,94,99,100,111,112)
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("wagon_closed_")}
        source["bindings"] = {"vehicles":{str(engine):source["bindings"]["vehicles"][str(engine)] for engine in engines}}
        result,definitions = compile_catalogue(source),vehicle_definitions()
        for engine in engines:
            states = result["bindings"]["vehicles"][str(engine)]
            self.assertEqual(definitions[str(engine)]["sprites"],definitions[str(engine)]["loaded_sprites"],"A closed-cargo alias lacks original source evidence")
            for state,name in states.items():
                self.assertEqual(name,states[str(int(state)^1)],"Closed source-identical cargo states changed geometry")
        for engine in (27,28):
            self.assertEqual(set(result["bindings"]["vehicles"][str(engine)]),set(map(str,range(8))),"A conventional coach lost its distinct source-climate artwork")
        for engine in (38,68,100):
            self.assertEqual(set(result["bindings"]["vehicles"][str(engine)]),{"2","3","4","5"})
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        self.assertIn((20,7,33),volumes["wagon_closed_oil"],"The ordinary tank lost its raised filler")
        self.assertNotIn((20,7,33),volumes["wagon_closed_oil_tropic"],"A temperate tank fitting leaked into tropical art")
        for name in ("wagon_closed_livestock","wagon_closed_livestock_fast","wagon_closed_toys_y"):
            self.assertNotIn((6,2,14),volumes[name],"An original ventilation opening became a painted opaque box")
        for name,cells in volumes.items():
            if "oil" not in name:
                self.assertNotIn((20,7,20),cells,"A closed van's interior was filled instead of retaining its actual shell")
            model = result["models"][name]
            self.assertEqual(model["origin"][2],0.5,"The wheels lost the established running-rail contact height")
            self.assertEqual(min(z for x,y,z in cells),0)
            contact_y = {model["origin"][1]+(y+0.5)*model["cell_size"][1] for x,y,z in cells if z == 0}
            self.assertEqual(contact_y,{-1.375,-1.125,1.125,1.375},"Wagon treads no longer straddle both original running rails at +/-1.25")
            visited,pending = set(),[next(iter(cells))]
            while pending:
                point = pending.pop()
                if point in visited:
                    continue
                visited.add(point)
                x,y,z = point
                pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
            self.assertEqual(len(visited),len(cells),f"Detached bogie, buffer, vent bar or filler in {name}")

    def test_city_houses_preserve_real_open_frames_absent_bodies_and_theatre_lights(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_city_") or name == "mine_ground_site"}
        source["bindings"] = {category:{str(house):states for house in range(28,32) if (states := source["bindings"][category].get(str(house))) is not None} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for house in (29,31):
            self.assertTrue(all(str(stage) not in result["bindings"]["houses"][str(house)] for stage in (0,4,8,12)),"An originally absent first body was invented")
            self.assertEqual(result["bindings"]["house_ground"][str(house)]["0"],"mine_ground_site")
        for family,height in (("heritage",77),("ribbed",68),("gold",59)):
            frame,finished = volumes[f"house_city_{family}_frame"],volumes[f"house_city_{family}"]
            self.assertNotIn((16,16,height),frame,"An unfinished original roof well was filled")
            self.assertIn((16,16,height),finished)
            self.assertLess(max(z for x,y,z in volumes[f"house_city_{family}_site"]),max(z for x,y,z in frame))
        self.assertFalse(any(z >= 90 for x,y,z in volumes["house_city_heritage_frame"]),"The glazed turret appeared during open-frame construction")
        self.assertTrue(any(z >= 96 for x,y,z in volumes["house_city_heritage"]))
        gold = volumes["house_city_gold"]
        self.assertTrue(any(x == 0 for x,y,z in gold if 22 <= z < 45) and any(x == 31 for x,y,z in gold if 22 <= z < 45),"The original stepped-out gold facade became a straight box")
        self.assertTrue(all(2 <= x < 30 and 2 <= y < 30 for x,y,z in gold if z == 0),"An upper facade overhang moved the actual ground contact")
        theatre_indices = {colour for material in volumes["house_city_theatre"].values() for colour in result["materials"][material-1]}
        self.assertTrue({241,242,243,244} <= theatre_indices,"The original four marquee palette entries were flattened")
        for name,cells in volumes.items():
            self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells),f"{name} left its original tile")
            remaining = set(cells)
            while remaining:
                visited,pending = set(),[next(iter(remaining))]
                while pending:
                    point = pending.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in remaining and p not in visited)
                self.assertTrue(any(z == 0 for x,y,z in visited),f"Detached facade, roof, chimney or sign in {name}: {len(visited)} cells, sample {sorted(visited)[:12]}")
                remaining -= visited

    def test_toyland_cargo_keeps_source_families_open_beds_and_distinct_loads(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        definitions = vehicle_definitions()
        self.assertTrue(all(str(engine) in source["bindings"]["vehicles"] for engine in range(116,204)),"An original road engine has no voxel cargo bindings")
        engines = (*range(174,186),*range(192,204))
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("road_toy_")}
        source["bindings"] = {"vehicles":{str(engine):source["bindings"]["vehicles"][str(engine)] for engine in engines}}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for first in (174,177,180,183,192,195,198,201):
            states = result["bindings"]["vehicles"][str(first)]
            self.assertNotEqual(definitions[str(first)]["sprites"],definitions[str(first)]["loaded_sprites"])
            empty,loaded = volumes[states["0"]],volumes[states["1"]]
            self.assertLess(set(empty),set(loaded),"Visible Toyland cargo was reduced to a recolour or a closed-state alias")
            self.assertNotIn((8,5,17),empty,"The original empty cargo space was filled")
            for point,material in empty.items():
                if point[0] >= 28 or point[2] < 7:
                    self.assertEqual(loaded[point],material,"Loading changed the face cab or running gear")
            for engine in range(first,first+3):
                self.assertEqual(definitions[str(engine)]["sprites"],definitions[str(first)]["sprites"])
                self.assertEqual(definitions[str(engine)]["loaded_sprites"],definitions[str(first)]["loaded_sprites"])
                self.assertEqual(result["bindings"]["vehicles"][str(engine)],states,"Original source-identical eras lost their shared body")
            if first in (192,195,198):
                self.assertTrue(all((x,5,18) in loaded for x in (8,21)),"An upright battery, can or plastic load lost its solid centre")
            if first == 201:
                self.assertIn((14,5,33),empty,"The original bubble canopy was lost")
                self.assertNotIn((7,5,16),loaded,"Source see-through bubbles became opaque cargo blocks")
                self.assertTrue(any(147 <= colour <= 153 for point,material in loaded.items() if point not in empty for colour in result["materials"][material-1]))
        for name,cells in volumes.items():
            self.assertEqual(min(z for x,y,z in cells),0,"A Toyland wheel floats above the road")
            self.assertLess(max(x for x,y,z in cells),40,"The Toyland nose exceeds the original road-body length")
            visited,pending = set(),[next(iter(cells))]
            while pending:
                point = pending.pop()
                if point in visited:
                    continue
                visited.add(point)
                x,y,z = point
                pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
            self.assertEqual(len(visited),len(cells),f"Detached wheel, frame, canopy or load in {name}")

    def test_climate_road_art_keeps_food_overrides_roofed_paper_and_real_open_loads(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("road_climate_")}
        source["bindings"] = {"vehicles":{str(engine):source["bindings"]["vehicles"][str(engine)] for engine in range(156,174)}}
        result,definitions = compile_catalogue(source),vehicle_definitions()
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for engine in range(156,159):
            states = result["bindings"]["vehicles"][str(engine)]
            self.assertEqual(set(states),{"2","3","4","5"},"Different food-vans cannot acquire a shared default climate body")
            self.assertEqual(states["2"],states["3"])
            self.assertEqual(states["4"],states["5"])
            arctic,tropic = volumes[states["2"]],volumes[states["4"]]
            self.assertEqual(set(arctic),set(tropic),"Original rear-panel recolouring moved geometry")
            self.assertTrue(all(colour < 198 for colour in result["materials"][arctic[1,4,14]-1]))
            self.assertTrue(all(198 <= colour <= 205 for colour in result["materials"][tropic[1,4,14]-1]))
        for engine in range(159,174):
            states = result["bindings"]["vehicles"][str(engine)]
            empty,loaded = volumes[states["0"]],volumes[states["1"]]
            identical = definitions[str(engine)]["sprites"] == definitions[str(engine)]["loaded_sprites"]
            self.assertEqual(states["0"] == states["1"],identical)
            if not identical:
                self.assertLess(set(empty),set(loaded),"Cargo needs real additional volume")
            if engine in range(159,162):
                self.assertIn((14,5,28),empty,"The paper canopy was confused with the same-numbered steel platform")
                self.assertNotIn((8,5,18),empty)
                self.assertIn((8,5,18),loaded)
            if engine in range(171,174):
                self.assertNotIn((14,5,20),empty,"The empty latex vat lost its open interior")
                self.assertIn((14,5,20),loaded)
        for name,cells in volumes.items():
            visited,pending = set(),[next(iter(cells))]
            while pending:
                point = pending.pop()
                if point in visited:
                    continue
                visited.add(point)
                x,y,z = point
                pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
            self.assertEqual(len(visited),len(cells),f"Detached tank, canopy, wheel or load in {name}")
            self.assertEqual(min(z for x,y,z in cells),0)

    def test_vehicle_climate_bindings_require_complete_bounded_cargo_pairs(self):
        source = self.source([["box","wall",0,0,0,2,2,2]])
        source["bindings"] = {"vehicles":{"156":{"2":"house","3":"house","4":"house","5":"house"}}}
        self.assertEqual(set(compile_catalogue(source)["bindings"]["vehicles"]["156"]),{"2","3","4","5"})
        for engine,states in (("156",{"2":"house"}), ("156",{"0":"house","1":"house","4":"house"}),
                              ("156",{"8":"house","9":"house"}), ("256",{"0":"house","1":"house"})):
            source["bindings"] = {"vehicles":{engine:states}}
            with self.subTest(engine=engine,states=states), self.assertRaises(ValueError):
                compile_catalogue(source)

    def test_open_road_cargo_keeps_empty_beds_grounded_loads_and_upright_hollow_coils(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        engines = (124,125,*range(141,153))
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("road_open_")}
        source["bindings"] = {"vehicles":{str(engine):source["bindings"]["vehicles"][str(engine)] for engine in engines}}
        result,definitions = compile_catalogue(source),vehicle_definitions()
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for engine in engines:
            states = result["bindings"]["vehicles"][str(engine)]
            self.assertNotEqual(definitions[str(engine)]["sprites"],definitions[str(engine)]["loaded_sprites"])
            self.assertNotEqual(states["0"],states["1"],"Distinct original cargo states were aliased")
            empty,loaded = volumes[states["0"]],volumes[states["1"]]
            self.assertLess(set(empty),set(loaded),"Cargo must add real occupied volume")
            for point,material in empty.items():
                x,y,z = point
                if x >= 28 or z < 7:
                    self.assertEqual(loaded[point],material,"Cargo changed the cab or running gear")
            if engine in (124,125,141,142,143,147,148,149):
                self.assertNotIn((14,5,18),empty,"The original empty tipper/hopper is not open")
                self.assertIn((14,5,18),loaded)
            if engine in (150,151,152):
                for x in (8,21):
                    self.assertTrue(all((x,5,z) not in loaded for z in range(12,25)),"An upright coil's original central opening was filled")
                    self.assertIn((x+3,5,20),loaded,"An upright coil lost its surrounding steel")
            for name in states.values():
                model,cells = result["models"][name],volumes[name]
                self.assertEqual(model["cell_size"],[0.25,0.25,0.25])
                self.assertEqual(model["origin"][2],0)
                self.assertEqual(min(z for x,y,z in cells),0,"Tyres no longer meet the original road height")
                visited,pending = set(),[next(iter(cells))]
                while pending:
                    point = pending.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(len(visited),len(cells),f"Detached wheel, load, stake or strap in {name}")

    def test_flat_variants_preserve_empty_ground_sites_open_roofs_and_unbuilt_rear_wings(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_flats_") or name == "mine_ground_site"}
        source["bindings"] = {category:{"27":source["bindings"][category]["27"]} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        bodies = result["bindings"]["houses"]["27"]
        self.assertNotIn("0",bodies)
        self.assertNotIn("4",bodies)
        for stage in (1,2,3):
            self.assertEqual(bodies[str(stage)],bodies[str(stage+4)])
        for stage in range(4):
            self.assertEqual(bodies[str(stage+8)],bodies[str(stage+12)])
        volumes = {name:{(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        self.assertNotIn((8,15,24),volumes["house_flats_tan_shell"],"The original unfinished roof well was sealed")
        self.assertIn((8,15,26),volumes["house_flats_tan"])
        self.assertNotIn((15,6,12),volumes["house_flats_brick_frame"],"Rear apartment wings appeared before their original completed state")
        self.assertIn((15,6,12),volumes["house_flats_brick"])
        front = {(x,y) for x,y,z in volumes["house_flats_brick"] if z >= 32}
        self.assertTrue(front and min(x for x,y in front) >= 22,"The tall source facades moved behind their lower wings")
        self.assertTrue(any(y < 13 for x,y in front) and any(y >= 16 for x,y in front),"The two source towers no longer sit along the correct tile axis")
        brick = result["models"]["house_flats_brick"]
        self.assertTrue(any(z >= 35 and 131 in result["materials"][material-1] for x,y,z,length,material in brick["runs"]),"The fifth original window storey was lost")
        for name,cells in volumes.items():
            self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells),"A flat's contact/roof crosses its original tile")
            remaining = set(cells)
            while remaining:
                visited,pending = set(),[next(iter(remaining))]
                while pending:
                    point = pending.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in remaining and p not in visited)
                self.assertTrue(any(z == 0 for x,y,z in visited),f"Detached apartment component in {name}")
                remaining -= visited

    def test_suburban_variants_keep_ground_owned_construction_and_supported_open_shells(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_suburban_") or name == "mine_ground_site"}
        source["bindings"] = {category:{"26":source["bindings"][category]["26"]} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        bodies,grounds = result["bindings"]["houses"]["26"],result["bindings"]["house_ground"]["26"]
        self.assertNotIn("0",bodies)
        self.assertNotIn("1",bodies)
        self.assertEqual(set(grounds),{"0","1"},"The bungalow's early structure belongs to its original ground layer")
        volumes = {name:{(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for name,cells in volumes.items():
            with self.subTest(model=name):
                self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells))
                remaining = set(cells)
                while remaining:
                    visited,pending = set(),[next(iter(remaining))]
                    while pending:
                        point = pending.pop()
                        if point in visited:
                            continue
                        visited.add(point)
                        x,y,z = point
                        pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in remaining and p not in visited)
                    self.assertTrue(any(z == 0 for x,y,z in visited),"An original house, roof, garage or chimney floats")
                    remaining -= visited
        for variant in (1,2,3):
            site,shell,finished = (volumes[bodies[str(variant*4+stage)]] for stage in (0,1,2))
            contact = lambda cells:{(x,y) for x,y,z in cells if z == 0}
            self.assertEqual(contact(site),contact(shell),"Construction shifted its original main-house contact")
            self.assertLessEqual(contact(shell),contact(finished))
            self.assertLess(max(z for x,y,z in site),max(z for x,y,z in shell))
            self.assertEqual(bodies[str(variant*4+2)],bodies[str(variant*4+3)])
        for name in grounds.values():
            self.assertEqual({(x,y) for x,y,z in volumes[name] if z == 0},{(x,y) for x in range(32) for y in range(32)},"Ground-only construction shrank the playable tile")
        self.assertNotIn((20,19,12),volumes[grounds["1"]],"The original roofless ground-layer rooms were filled")
        self.assertNotIn((6,8,15),volumes["house_suburban_gable_pair_shell"])
        self.assertIn((6,8,15),volumes["house_suburban_gable_pair"])

    def test_old_houses_keep_original_variant_footprints_and_finished_or_empty_first_states(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("house_old_") or name == "mine_ground_site"}
        source["bindings"] = {category:{house:source["bindings"][category][house] for house in ("24","25")} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        old = result["bindings"]["houses"]["24"]
        self.assertEqual(set(old),set(map(str,range(16))))
        self.assertEqual(len({old[str(variant*4)] for variant in range(4)}),4,"Four distinct original houses became a generic alias")
        for variant in range(4):
            self.assertEqual(len({old[str(variant*4+stage)] for stage in range(4)}),1,"Original old-house first stages already have their finished body")
        cottages = result["bindings"]["houses"]["25"]
        self.assertEqual(set(cottages),{"1","2","3"},"The cottage's genuinely empty first body was fabricated")
        self.assertEqual(len(set(cottages.values())),1)
        for house in ("24","25"):
            self.assertEqual(set(result["bindings"]["house_ground"][house]),{"0"},"Original mature gardens must retain their separate source selection")
        for name,model in result["models"].items():
            if name == "mine_ground_site":
                continue
            with self.subTest(model=name):
                cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
                if "straw" in name:
                    colours = {colour for x,y,z,length,material in model["runs"] for colour in result["materials"][material-1]}
                    self.assertFalse(colours & (set(range(52,70)) | set(range(122,128))),"Pale/brown thatch acquired an unrelated yellow or red palette ramp")
                for x,y,z in cells:
                    self.assertTrue(0 <= model["origin"][0]+x*0.5 < 16 and 0 <= model["origin"][1]+y*0.5 < 16)
                while cells:
                    visited,pending = set(),[next(iter(cells))]
                    while pending:
                        point = pending.pop()
                        if point in visited:
                            continue
                        visited.add(point)
                        x,y,z = point
                        pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                    self.assertTrue(any(z == 0 for x,y,z in visited),"A roof/chimney or timber member is detached from its grounded house")
                    cells -= visited

    def test_dock_sections_keep_level_decks_open_walkways_and_original_climate_details(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("water_dock_")}
        source["bindings"] = {"docks":source["bindings"]["docks"]}
        result = compile_catalogue(source)
        for graphics,states in result["bindings"]["docks"].items():
            self.assertEqual(set(states),{"0","1"})
            self.assertNotEqual(states["0"],states["1"],"Distinct Toyland source detail was aliased")
            for climate,name in states.items():
                with self.subTest(graphics=graphics,climate=climate):
                    model = result["models"][name]
                    cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                    canonical = {(x,y,z) if int(graphics)%2 == 0 else (y,x,z) for x,y,z in cells}
                    self.assertEqual(model["cell_size"],[0.5,0.5,0.5])
                    self.assertEqual(model["origin"],[0,0,-0.5])
                    self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells),"Dock left the original playable tile")
                    self.assertTrue(all((x,y,32) in canonical for x in range(32) for y in range(6,26)),"A joined deck lost its doubled sixteen-unit terrain elevation")
                    self.assertFalse(any(8 <= y < 24 and z >= 33 for x,y,z in canonical),"A bollard or lamp blocks the central walkway")
                    remaining = set(cells)
                    while remaining:
                        visited, pending = set(), [next(iter(remaining))]
                        while pending:
                            point = pending.pop()
                            if point in visited:
                                continue
                            visited.add(point)
                            x,y,z = point
                            pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in remaining and p not in visited)
                        def ground_layer(point):
                            x,y,z = point
                            if int(graphics) >= 4:
                                return 0
                            along = x if int(graphics)%2 == 0 else y
                            return along if int(graphics) in (0,3) else 31-along
                        self.assertTrue(any(z <= ground_layer((x,y,z))+1 for x,y,z in visited),"A pile, rail or lamp floats above its actual land/water support")
                        remaining -= visited
                    colours = {colour for material in cells.values() for colour in result["materials"][material-1]}
                    if int(graphics) >= 4:
                        animated = {241,242,243,250,251,252,253,254}
                        self.assertEqual(colours & animated,animated if climate == "0" else set(),"Original lamp/foam climate selection changed")
                    else:
                        self.assertTrue(colours & set(range(198,206)),"Original company-coloured bank railing was lost")
                        for x,y,z in canonical:
                            terrain_step = x if int(graphics) in (0,3) else 31-x
                            self.assertGreaterEqual(z,terrain_step,"A bank pile protrudes below the supporting slope's tile boundary")

    def test_ship_depots_preserve_two_tile_joins_open_water_and_all_original_ship_clearances(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("ship_","water_depot_"))}
        source["bindings"] = {"ship_depots":source["bindings"]["ship_depots"]}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for axis in range(2):
            parts = result["bindings"]["ship_depots"][str(axis)]
            self.assertEqual(set(parts),{"0","1"})
            sections = []
            for part in range(2):
                name = parts[str(part)]
                model, cells = result["models"][name], volumes[name]
                self.assertEqual(model["cell_size"],[0.5,0.5,0.5])
                self.assertEqual(model["origin"],[0,0,-0.5])
                self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells),"A grounded depot wall leaves its own tile")
                visited, pending = set(), [next(iter(cells))]
                while pending:
                    point = pending.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(len(visited),len(cells),"A roof, wall or window has become detached")
                canonical = {(x,y,z) if axis == 0 else (y,x,z) for x,y,z in cells}
                self.assertTrue(all((x,y,z) not in canonical for x in range(32) for y in range(4,28) for z in range(24)),"Waterway was filled or an entrance was closed")
                sections.append(canonical)
            self.assertEqual({(y,z) for x,y,z in sections[0] if x == 31},{(y,z) for x,y,z in sections[1] if x == 0},"The two original depot tiles no longer meet")
            blocked = {(y,z) for cells in sections for x,y,z in cells}
            for name,model in result["models"].items():
                if not name.startswith("ship_"):
                    continue
                for direction in (-1,1):
                    cross_section = {(math.floor((8+direction*(model["origin"][1]+(y+0.5)*model["cell_size"][1]))/0.5),
                                      math.floor((model["origin"][2]+(z+0.5)*model["cell_size"][2]+0.5)/0.5)) for x,y,z in volumes[name]}
                    self.assertFalse(blocked & cross_section,f"{name} strikes the roof/wall while traversing depot axis {axis}, direction {direction}")

    def test_ship_families_keep_waterline_connected_hardware_open_holds_and_real_source_aliases(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("ship_")}
        source["bindings"] = {"vehicles": {str(engine):source["bindings"]["vehicles"][str(engine)] for engine in range(204,215)}}
        result = compile_catalogue(source)
        volumes = {}
        for name,model in result["models"].items():
            cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            with self.subTest(model=name):
                visited, pending = set(), [next(iter(cells))]
                while pending:
                    point = pending.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(len(visited),len(cells),"A mast, propeller, cabin, captain or derrick is detached")
                self.assertLess(model["origin"][2]+min(z for x,y,z in cells)*model["cell_size"][2],0)
                self.assertGreater(model["origin"][2]+max(z for x,y,z in cells)*model["cell_size"][2],0)
                colours = {c for material in cells.values() for c in result["materials"][material-1]}
                self.assertTrue(colours & set(range(198,206)),"Original company hull colour was flattened")
        for x in (40,80):
            self.assertNotIn((x,13,14),volumes["ship_cargo_freighter"],"The genuine dark cargo hold was filled")
            self.assertIn((x,13,7),volumes["ship_cargo_freighter"],"The hold lost its recessed floor")
        definitions = vehicle_definitions()
        for engine,states in result["bindings"]["vehicles"].items():
            self.assertEqual(definitions[engine]["sprites"],definitions[engine]["loaded_sprites"])
            self.assertEqual(states["0"],states["1"])
        self.assertNotEqual(result["bindings"]["vehicles"]["206"],result["bindings"]["vehicles"]["209"])
        self.assertNotEqual(result["bindings"]["vehicles"]["211"],result["bindings"]["vehicles"]["213"])

    def test_authored_hull_sections_keep_flared_sides_connected_bow_and_independent_deck_faces(self):
        source = self.source([["hull","wall",6,[[0,1,2,0,6],[3,3,5,0,6],[8,3,5,1,7],[12,0,0.6,2,7]],"window",1]])
        source["models"]["house"]["size"] = [12,12,8]
        result = compile_catalogue(source)
        cells = {(x+i,y,z):material for x,y,z,length,material in result["models"]["house"]["runs"] for i in range(length)}
        self.assertGreater(len({y for x,y,z in cells if x == 4 and z == 5}),len({y for x,y,z in cells if x == 4 and z == 0}))
        self.assertGreater(len({y for x,y,z in cells if x == 4}),len({y for x,y,z in cells if x == 11}))
        self.assertEqual({(x,11-y,z) for x,y,z in cells},set(cells))
        deck = result["materials"][cells[4,5,5]-1]
        self.assertEqual(deck[:5],[74]*5)
        self.assertEqual(deck[5],135)
        self.assertEqual(result["materials"][cells[0,5,5]-1],[74]*6,"The authored rim was painted over")
        visited, pending = set(), [next(iter(cells))]
        while pending:
            point = pending.pop()
            if point in visited:
                continue
            visited.add(point)
            x,y,z = point
            pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
        self.assertEqual(visited,set(cells))
        plain = self.source([["hull","wall",6,[[0,1,2,0,6],[3,3,5,0,6],[8,3,5,1,7],[12,0,0.6,2,7]]]])
        plain["models"]["house"]["size"] = [12,12,8]
        model = compile_catalogue(plain)["models"]["house"]
        self.assertEqual(set(cells),{(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)},"Deck painting changed hull occupancy")

    def test_hull_profiles_reject_clipping_invalid_sections_and_ambiguous_parameters(self):
        profiles = ([[0,1,2,0,4]], [[0,1,2,0,4],[0,1,2,0,4]],
                    [[0,1,4,0,4],[8,1,2,0,4]], [[0,1,2,4,2],[8,1,2,0,4]],
                    [[0,1,2,0,4],[9,1,2,0,4]], [[0,1,2,0,4],[8,1,2,0,6]],
                    [[0,1,2,0,4],[8,-1,2,0,4]], [[0,1,2,0,4],[8,1,0,0,4]],
                    [[0,1,2,0,4],[8,1,float("nan"),0,4]])
        for profile in profiles:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                compile_catalogue(self.source([["hull","wall",3,profile]]))
        for extra in (("missing",1),("window",-1),("window",1.5)):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                compile_catalogue(self.source([["hull","wall",3,[[0,1,2,0,4],[8,1,2,0,4]],*extra]]))

    def test_stadium_blocks_keep_permanent_joined_pitches_empty_first_bodies_and_supported_stands(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("stadium_")}
        houses = tuple(map(str,(*range(20,24),*range(32,36))))
        source["bindings"] = {category: {key:source["bindings"][category][key] for key in houses} for category in ("houses","house_ground")}
        result = compile_catalogue(source)
        volumes = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for house in houses:
            self.assertEqual(set(result["bindings"]["houses"][house]),{"1","2","3"},"The original empty body stage was invented")
            self.assertEqual(len(set(result["bindings"]["houses"][house].values())),1)
            self.assertEqual(set(result["bindings"]["house_ground"][house]),{"0","1","2","3"})
            self.assertEqual(len(set(result["bindings"]["house_ground"][house].values())),1)
        for family in ("soccer","gridiron"):
            floor = {}
            for slot, suffix in enumerate(("n","e","w","s")):
                name = f"stadium_{family}_ground_{suffix}"
                model = result["models"][name]
                self.assertEqual(set(volumes[name]),{(x,y,0) for x in range(32) for y in range(32)})
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0,"Pitch no longer meets original map height")
                for (x,y,z),material in volumes[name].items():
                    floor[x+slot//2*32,y+slot%2*32] = result["materials"][material-1][5]
                body_name = f"stadium_{family}_stand_{suffix}"
                cells = set(volumes[body_name])
                while cells:
                    pending, connected = [next(iter(cells))], set()
                    while pending:
                        point = pending.pop()
                        if point in connected:
                            continue
                        connected.add(point)
                        x,y,z = point
                        pending.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in connected)
                    self.assertTrue(any(z == 0 for x,y,z in connected),f"Floating stand, lamp, spectator or goal in {body_name}")
                    cells -= connected
                # Original goal sprite ownership crosses one sub-tile; the actual
                # complete stadium footprint is the four-tile32x32 block.
                for x,y,z in volumes[body_name]:
                    if z == 0:
                        self.assertTrue(0 <= x*0.5+slot//2*16 < 32)
                        self.assertTrue(0 <= y*0.5+slot%2*16 < 32)
            self.assertEqual(set(floor),{(x,y) for x in range(64) for y in range(64)})
            if family == "soccer":
                self.assertTrue(all(floor[x,32] == 15 for x in range(12,52)),"Centre line breaks at the tile seam")
                self.assertEqual(floor[12,20],15)
                self.assertEqual(floor[51,20],15)
            else:
                for y in range(4,64,8):
                    self.assertEqual(floor[31,y],15)
                    self.assertEqual(floor[32,y],15,"Yard line breaks at the tile seam")
        for name in ("stadium_soccer_stand_n","stadium_gridiron_stand_n"):
            colours = {c for material in volumes[name].values() for c in result["materials"][material-1]}
            self.assertTrue(set(range(227,232)) <= colours,"The original moving crowd palette was flattened")
            if "gridiron" in name:
                self.assertTrue(set(range(241,245)) <= colours,"The original scoreboard phases were flattened")
                self.assertNotIn((31,8,3),volumes[name],"The H goal was filled below its crossbar")
        self.assertNotIn((31,27,4),volumes["stadium_soccer_stand_w"],"The pedestrian gate is blocked")

    def test_modular_and_rooflight_offices_keep_supported_states_and_original_ground_limits(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("house_modular_office","house_sawtooth_warehouse","house_rooflight_office"))}
        source["bindings"] = {"houses": {key:source["bindings"]["houses"][key] for key in ("17","18","19")}}
        result = compile_catalogue(source)
        volumes = {}
        for name,model in result["models"].items():
            cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            with self.subTest(model=name):
                visited, todo = set(), [next(iter(cells))]
                while todo:
                    point = todo.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(len(visited),len(cells),"A module, core, roof panel or stair landing is unsupported")
                contacts = [point for point in cells if model["origin"][2]+point[2]*model["cell_size"][2] <= 0 < model["origin"][2]+(point[2]+1)*model["cell_size"][2]]
                self.assertTrue(contacts)
                for axis in (0,1):
                    self.assertGreaterEqual(model["origin"][axis]+min(p[axis] for p in contacts)*model["cell_size"][axis],0)
                    self.assertLessEqual(model["origin"][axis]+(max(p[axis] for p in contacts)+1)*model["cell_size"][axis],16)
        self.assertLess(max(z for x,y,z in volumes["house_modular_office_site"]),30,"The first pavilion already contains later tall cores")
        self.assertIn((6,7,90),volumes["house_modular_office_shell"],"Construction lost its original tall cores")
        for name in ("house_modular_office_shell","house_modular_office"):
            colours = {c for material in volumes[name].values() for c in result["materials"][material-1]}
            self.assertTrue(colours & set(range(198,206)),"Original red/blue/orange/green recolouring was baked to one variant")
        self.assertIn((29,8,0),volumes["house_sawtooth_warehouse"],"The loading ramp no longer reaches ground")
        self.assertNotIn((29,8,0),volumes["house_sawtooth_warehouse_shell"])
        self.assertIn((5,21,10),volumes["house_sawtooth_warehouse"])
        self.assertNotIn((5,21,10),volumes["house_sawtooth_warehouse_shell"])
        self.assertIn((5,5,37),volumes["house_rooflight_office"])
        self.assertNotIn((5,5,37),volumes["house_rooflight_office_shell"],"The unglazed rooflight frame was filled")

    def test_stucco_and_mansard_shops_keep_source_footprints_and_distinct_construction(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("house_stucco_shops","house_mansard_shops"))}
        source["bindings"] = {"houses": {key:source["bindings"]["houses"][key] for key in ("15","16")}}
        result = compile_catalogue(source)
        volumes = {}
        for name,model in result["models"].items():
            cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            contacts = [point for point in cells if model["origin"][2]+point[2]*model["cell_size"][2] <= 0 < model["origin"][2]+(point[2]+1)*model["cell_size"][2]]
            self.assertTrue(contacts,name)
            bounds = [[model["origin"][axis]+min(p[axis] for p in contacts)*model["cell_size"][axis] for axis in (0,1)],
                      [model["origin"][axis]+(max(p[axis] for p in contacts)+1)*model["cell_size"][axis] for axis in (0,1)]]
            self.assertEqual(bounds,[[4,2],[13,14]] if "stucco" in name else [[2,0],[15,16]],name)
        for states in result["bindings"]["houses"].values():
            self.assertEqual(set(states),{"0","1","2","3"})
            self.assertEqual(states["2"],states["3"])
        self.assertIn((2,5,14),volumes["house_stucco_shops"])
        self.assertNotIn((2,5,14),volumes["house_stucco_shops_shell"])
        self.assertIn((0,3,18),volumes["house_mansard_shops"])
        self.assertNotIn((0,3,18),volumes["house_mansard_shops_shell"])
        self.assertNotIn((12,16,40),volumes["house_mansard_shops"],"The open roof well was capped")
        self.assertIn((12,16,39),volumes["house_mansard_shops"],"The roof well lost its floor")
        self.assertNotIn((12,16,40),volumes["house_mansard_shops_shell"])
        self.assertIn((0,0,16),volumes["house_mansard_shops_site"],"The original first-stage raised frame became a generic excavation")
        self.assertNotIn((0,3,8),volumes["house_mansard_shops_site"])

    def test_closed_road_cargo_families_keep_clearance_vents_and_real_source_states(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("road_van_","road_tanker_"))}
        selected = {name for name in source["models"]}
        source["bindings"] = {"vehicles": {engine:states for engine,states in source["bindings"]["vehicles"].items() if set(states.values()) <= selected}}
        result = compile_catalogue(source)
        for name,model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            with self.subTest(model=name):
                self.assertLessEqual((max(z for x,y,z in cells)+1)*0.25,7.25)
                self.assertLessEqual((max(y for x,y,z in cells)+1)*0.25,2.75)
                for x in (7,14,33):
                    for y in (0,10):
                        self.assertIn((x,y,0),cells)
                if "livestock" in name:
                    self.assertNotIn((4,1,16),cells,"The defining livestock vents were filled")
                    self.assertIn((4,1,18),cells,"The livestock slats are missing")
                if "tanker" in name:
                    self.assertNotIn((1,1,9),cells,"The rounded tank became a box")
                    self.assertIn((14,5,27),cells,"The filler is missing")
        definitions = vehicle_definitions()
        for engine,states in result["bindings"]["vehicles"].items():
            self.assertEqual(set(states),{"0","1"})
            self.assertEqual(definitions[engine]["sprites"],definitions[engine]["loaded_sprites"])
            self.assertEqual(states["0"],states["1"])

    def test_bus_families_keep_grounded_wheels_clearance_and_source_permitted_aliases(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("road_bus_")}
        source["bindings"] = {"vehicles": {str(engine): source["bindings"]["vehicles"][str(engine)] for engine in range(116,123)}}
        result = compile_catalogue(source)
        for name, model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            with self.subTest(model=name):
                self.assertLessEqual(model["origin"][2]+(max(z for x,y,z in cells)+1)*model["cell_size"][2], 7.25)
                self.assertLessEqual((max(y for x,y,z in cells)-min(y for x,y,z in cells)+1)*model["cell_size"][1], 2.75)
                for x in (9,32):
                    for y in (0,10):
                        self.assertIn((x,y,0), cells, "A wheel lost contact with the road")
                self.assertNotIn((18,5,17), cells, "The passenger interior was filled")
                visited, todo = set(), [next(iter(cells))]
                while todo:
                    point = todo.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(len(visited),len(cells),"A wheel, bonnet or face component is detached")
        definitions = vehicle_definitions()
        for engine in map(str,range(116,123)):
            self.assertEqual(definitions[engine]["sprites"],definitions[engine]["loaded_sprites"])
            self.assertEqual(result["bindings"]["vehicles"][engine]["0"],result["bindings"]["vehicles"][engine]["1"])
        self.assertEqual(definitions["117"]["sprites"],definitions["118"]["sprites"])
        self.assertEqual(result["bindings"]["vehicles"]["117"],result["bindings"]["vehicles"]["118"])
        self.assertNotEqual(result["bindings"]["vehicles"]["117"],result["bindings"]["vehicles"]["120"],"Distinct climate artwork was merged by sprite number")

    def source(self, ops):
        return {"format": 1, "materials": {"wall": 74, "window": [134,135,136,137,134,135]},
                "models": {"house": {"size": [8,6,5], "ops": ops}},
                "bindings": {"houses": {"1": {"3": "house"}}}}

    def test_cutouts_repeats_and_paint_preserve_empty_cells(self):
        result = compile_catalogue(self.source([
            ["box", "wall", 0,0,0,8,6,5], ["erase", 2,2,0,6,4,5],
            ["repeat", [2,0,0], 4, [["paint", "window", 0,0,1,1,6,3]]]]))
        model = result["models"]["house"]
        self.assertEqual(model["occupied"], 200)
        cells = {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertNotIn((2,2,1), cells)
        self.assertEqual(cells[0,0,1], 2)
        self.assertEqual(cells[1,0,1], 1)
        self.assertEqual(result["materials"][1], [134,135,136,137,134,135])

    def test_authored_ellipsoid_has_rounded_corners_and_connected_symmetric_cells(self):
        result = compile_catalogue(self.source([["ellipsoid", "wall", 0,0,0,4,4,4]]))
        model = result["models"]["house"]
        cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertEqual(len(cells), 32)
        self.assertNotIn((0,0,0), cells)
        self.assertIn((0,1,1), cells)
        self.assertEqual(cells, {(3-x,y,z) for x,y,z in cells})
        self.assertEqual(cells, {(z,x,y) for x,y,z in cells})
        visited, todo = set(), [(1,1,1)]
        while todo:
            point = todo.pop()
            if point in visited:
                continue
            visited.add(point)
            x,y,z = point
            todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
        self.assertEqual(visited, cells)

    def test_ellipsoid_material_brush_never_expands_the_authored_silhouette(self):
        ops = [["box", "wall", 1,1,1,7,5,4], ["erase", 3,2,1,5,4,4]]
        def cells(operations):
            model = compile_catalogue(self.source(operations))["models"]["house"]
            return {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
        original = cells(ops)
        painted = cells(ops + [["ellipsoid_paint", "window", 0,0,0,6,6,5]])
        self.assertEqual(set(painted), set(original))
        self.assertNotIn((3,2,2), painted)
        self.assertEqual(painted[6,1,1], 1)
        self.assertEqual(painted[2,2,2], 2)
        self.assertEqual(set(painted.values()), {1,2})

    def test_thin_voxel_lines_are_reversible_connected_and_bounded(self):
        def cells(ops):
            model = compile_catalogue(self.source(ops))["models"]["house"]
            return {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        line = cells([["line", "wall", 1,1,1,6,4,3]])
        self.assertEqual(len(line), 11)
        self.assertIn((1,1,1), line)
        self.assertIn((6,4,3), line)
        self.assertEqual(line, cells([["line", "wall", 6,4,3,1,1,1]]))
        self.assertEqual(cells([["line", "wall", 2,2,0,2,2,4]]), {(2,2,z) for z in range(5)})
        self.assertEqual(cells([["line", "wall", 2,2,2,2,2,2]]), {(2,2,2)})
        visited, todo = set(), [(1,1,1)]
        while todo:
            point = todo.pop()
            if point in visited:
                continue
            visited.add(point)
            x,y,z = point
            todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in line and p not in visited)
        self.assertEqual(visited, line)
        with self.assertRaises(ValueError):
            cells([["line", "wall", 0,0,0,8,0,0]])

    def test_inheritance_is_independent_and_cycles_are_rejected(self):
        source = self.source([["box", "wall", 0,0,0,8,6,5]])
        source["models"]["shell"] = {"extends": "house", "ops": [["erase", 0,0,2,8,6,5]]}
        result = compile_catalogue(source)
        self.assertEqual(result["models"]["house"]["occupied"], 240)
        self.assertEqual(result["models"]["shell"]["occupied"], 96)
        source["models"]["house"]["extends"] = "shell"
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_lathe_keeps_a_connected_hollow_waist_and_symmetric_footprint(self):
        source = self.source([["lathe", "wall", [4,4], [[0,3.9,2.3],[3,2,0.5],[6,3.5,2]]]])
        source["models"]["house"]["size"] = [8,8,6]
        model = compile_catalogue(source)["models"]["house"]
        cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertTrue(all((3,3,z) not in cells for z in range(6)), "The cooling passage was capped")
        self.assertEqual(cells, {(7-x,y,z) for x,y,z in cells})
        self.assertEqual(cells, {(y,x,z) for x,y,z in cells})
        self.assertGreater(max(abs(x+0.5-4) for x,y,z in cells if z == 0),
                           max(abs(x+0.5-4) for x,y,z in cells if z == 3), "The outer wall lost its waist")
        visited, todo = set(), [next(iter(cells))]
        while todo:
            point = todo.pop()
            if point in visited:
                continue
            visited.add(point)
            x,y,z = point
            todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
        self.assertEqual(visited, cells, "The profiled wall has detached rings")

    def test_lathe_transform_and_component_offset_keep_authored_placement(self):
        def cells(angle, offset):
            source = self.source([["use", "ring", offset]])
            source["models"]["house"]["size"] = [12,12,8]
            source["components"] = {"ring": [["lathe", "window", [5,5], [[0,2,1],[3,2,1]], [2,1,angle]]]}
            model = compile_catalogue(source)["models"]["house"]
            return {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
        original = cells(0,[0,0,0])
        self.assertEqual(cells(90,[0,0,0]), {(y,x,z): material for (x,y,z),material in original.items()})
        self.assertEqual(cells(0,[1,2,3]), {(x+1,y+2,z+3): material for (x,y,z),material in original.items()})

    def test_lathe_rejects_invalid_profiles_and_silent_clipping(self):
        profiles = ([[0,2,1]], [[0,2,1],[0,3,1]], [[1,2,1],[0,3,1]],
                    [[0,2,2],[3,3,1]], [[0,2,-1],[3,3,1]], [[0,2,1],[3,float("nan"),1]],
                    [[False,2,1],[3,3,1]], [[0,2,1],[6,3,1]])
        for profile in profiles:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                compile_catalogue(self.source([["lathe", "wall", [4,3], profile]]))
        for transform in ([0,1,0], [1,1,361], [1,1,float("inf")], [2,2,0]):
            with self.subTest(transform=transform), self.assertRaises(ValueError):
                compile_catalogue(self.source([["lathe", "wall", [4,3], [[0,3,1],[4,3,1]], transform]]))

    def test_inner_lathe_paint_preserves_exterior_grain_occupancy_and_rim(self):
        profile = [[0,3,2],[4,3,2]]
        source = self.source([["lathe", "wall", [4,4], profile],
                              ["paint", "grain", 6,3,1,7,4,2], ["erase", 6,3,2,7,4,3]])
        source["models"]["house"]["size"] = [8,8,5]
        source["materials"]["grain"] = 59
        def cells(result):
            return {(x+i,y,z): result["materials"][material-1]
                    for x,y,z,length,material in result["models"]["house"]["runs"] for i in range(length)}
        original = cells(compile_catalogue(source))
        source["models"]["house"]["ops"].append(["lathe_paint_inner", "window", [4,4], profile])
        painted = cells(compile_catalogue(source))
        self.assertEqual(set(original), set(painted))
        self.assertNotIn((6,3,2), painted, "Face painting filled an existing opening")
        self.assertEqual(painted[6,3,1][0], 134)  # Inward -X face.
        self.assertEqual(painted[6,3,1][1:], [59]*5, "Lining leaked onto exterior grain or horizontal faces")
        self.assertEqual(painted[6,3,3][5], 74, "The original top rim was repainted")
        self.assertEqual(painted[6,3,0][4], 74)
        source["models"]["house"]["ops"][-1].extend([[1,1,0], [2,617]])
        grain = cells(compile_catalogue(source))
        self.assertEqual(grain, cells(compile_catalogue(source)), "Inner-face grain is not deterministic")
        self.assertEqual(set(grain), set(original))
        changed = 0
        for point, faces in grain.items():
            for face, colour in enumerate(faces):
                self.assertIn(colour, (original[point][face], painted[point][face]))
                if original[point][face] == painted[point][face]:
                    self.assertEqual(colour, original[point][face], "Grain changed an exterior face")
                changed += colour != original[point][face]
        self.assertGreater(changed, 0)
        self.assertLess(changed, sum(a != b for point in original for a,b in zip(original[point],painted[point])))
        for invalid in ([0,1], [1,-1], [True,0], [1,0,2]):
            source["models"]["house"]["ops"][-1][-1] = invalid
            with self.subTest(grain=invalid), self.assertRaises(ValueError):
                compile_catalogue(source)

    def test_names_and_state_identifiers_are_portable(self):
        source = self.source([["box", "wall", 0,0,0,2,2,2]])
        source["models"]["../outside"] = source["models"]["house"]
        with self.assertRaises(ValueError):
            compile_catalogue(source)
        del source["models"]["../outside"]
        source["bindings"]["houses"]["1"] = {"65536": "house"}
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_invalid_geometry_and_bindings_fail_before_runtime(self):
        for ops in ([["box", "wall", -1,0,0,2,2,2]], [["box", "missing", 0,0,0,2,2,2]],
                    [["repeat", [1,0,0], 0, []]], [["gable", "wall", 0,0,0,4,4,3,"z"]]):
            with self.subTest(ops=ops), self.assertRaises(ValueError):
                compile_catalogue(self.source(ops))
        source = self.source([["box", "wall", 0,0,0,2,2,2]])
        source["bindings"]["houses"]["1"]["3"] = "absent"
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_transpose_keeps_cell_materials_and_occupancy(self):
        source = self.source([["box", "window", 1,2,3,3,5,4]])
        source["models"]["house"]["transpose_xy"] = True
        model = compile_catalogue(source)["models"]["house"]
        cells = {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertEqual(model["size"], [6,8,5])
        self.assertEqual(model["occupied"], 6)
        self.assertEqual(cells, {(x,y,3): 2 for x in range(2,5) for y in range(1,3)})

    def test_barrel_shell_keeps_open_interior_and_connected_steps(self):
        source = self.source([["barrel", "wall", 0,0,1,8,6,5,"x"]])
        model = compile_catalogue(source)["models"]["house"]
        cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertNotIn((4,3,1), cells)
        self.assertIn((4,3,4), cells)
        self.assertIn((0,3,1), cells)
        for x in range(7):
            a = {z for z in range(5) if (x,3,z) in cells}
            b = {z for z in range(5) if (x+1,3,z) in cells}
            self.assertTrue(a & b)

    def test_barrel_end_fill_and_axis_rotation_retain_the_same_roof(self):
        def cells(source):
            model = compile_catalogue(source)["models"]["house"]
            return {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        shell = cells(self.source([["barrel", "wall", 0,0,1,8,6,5,"x"]]))
        filled = cells(self.source([["barrel_fill", "wall", 0,0,1,8,6,5,"x"]]))
        self.assertLess(shell, filled)
        self.assertIn((4,3,1), filled)
        turned = self.source([["barrel", "wall", 0,0,1,6,8,5,"y"]])
        turned["models"]["house"]["size"] = [6,8,5]
        self.assertEqual(cells(turned), {(y,x,z) for x,y,z in shell})
        with self.assertRaises(ValueError):
            compile_catalogue(self.source([["barrel", "wall", 0,0,1,2,6,5,"x"]]))

    def test_rotated_components_preserve_quarter_turn_cells_and_parent_content(self):
        source = self.source([["box", "window", 0,0,0,1,1,1],
                              ["rotate_z", 90, [3,3,0], [["use", "arm"]]]])
        source["components"] = {"arm": [["box", "wall", 1,2,1,3,3,2]]}
        model = compile_catalogue(source)["models"]["house"]
        cells = {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertEqual(cells, {(0,0,0): 2, (3,1,1): 1, (3,2,1): 1})
        source["components"]["arm"] = [["use", "arm"]]
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_rotated_thin_components_are_connected_and_never_silently_clipped(self):
        source = self.source([["rotate_z", 30, [4,3,0], [["box", "wall", 1,2,1,7,3,2]]]])
        model = compile_catalogue(source)["models"]["house"]
        cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        visited, todo = set(), [next(iter(cells))]
        while todo:
            point = todo.pop()
            if point in visited:
                continue
            visited.add(point)
            x,y,z = point
            todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z)) if p in cells and p not in visited)
        self.assertEqual(visited, cells)
        source["models"]["house"]["ops"][0][2] = [20,20,0]
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_detail_cell_size_is_explicit_and_inherited_without_rescaling(self):
        source = self.source([["box", "wall", 1,1,1,3,3,3]])
        source["models"]["house"]["cell_size"] = [0.25,0.25,1]
        source["models"]["child"] = {"extends": "house"}
        result = compile_catalogue(source)
        self.assertEqual(result["models"]["child"]["cell_size"], [0.25,0.25,1])
        self.assertEqual(result["models"]["child"]["runs"], result["models"]["house"]["runs"])
        source["models"]["child"]["cell_size"] = [0.5,0.5,1]
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_material_erasure_opens_all_inherited_glazing_without_removing_walls(self):
        source = self.source([["box", "wall", 0,0,0,8,6,5], ["box", "window", 1,1,1,3,3,3]])
        source["models"]["construction"] = {"extends": "house", "ops": [["erase_material", "window"]]}
        models = compile_catalogue(source)["models"]
        self.assertEqual(models["house"]["occupied"], 240)
        self.assertEqual(models["construction"]["occupied"], 232)
        self.assertTrue(all(run[4] == 1 for run in models["construction"]["runs"]))

    def test_variant_material_replacement_preserves_shape_and_parent_shading(self):
        source = self.source([["box", "wall", 1,1,0,7,5,5], ["paint", "window", 1,1,1,2,5,4], ["erase", 3,2,0,5,4,5]])
        source["materials"]["brick"] = [71,73,72,75,70,77]
        source["models"]["brick_variant"] = {"extends": "house", "ops": [["replace_material", "wall", "brick"]]}
        source["bindings"]["houses"]["1"]["7"] = "brick_variant"
        models = compile_catalogue(source)["models"]
        def cells(model):
            return {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
        parent, variant = cells(models["house"]), cells(models["brick_variant"])
        self.assertEqual(parent.keys(), variant.keys())
        self.assertEqual(variant, {point: 3 if material == 1 else material for point,material in parent.items()})
        self.assertIn(1, parent.values())
        self.assertNotIn(1, variant.values())
        source["models"]["brick_variant"]["ops"][0][2] = "unknown"
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_authored_scatter_is_repeatable_bounded_and_never_fills_openings(self):
        source = self.source([["box", "wall", 0,0,0,8,6,5], ["erase", 2,2,0,6,4,5],
                              ["scatter_paint", "window", 3, 719, 0,0,4,8,6,5]])
        first = compile_catalogue(source)
        self.assertEqual(first, compile_catalogue(source))
        def cells(result):
            return {(x+i,y,z): material for x,y,z,length,material in result["models"]["house"]["runs"] for i in range(length)}
        painted = cells(first)
        self.assertEqual(len(painted), 200)
        self.assertNotIn((3,3,4), painted)
        self.assertTrue(any(material == 2 for material in painted.values()))
        self.assertTrue(all(material == 1 for (x,y,z),material in painted.items() if z < 4))
        source["models"]["house"]["ops"][-1][3] += 1
        changed = cells(compile_catalogue(source))
        self.assertEqual(painted.keys(), changed.keys())
        self.assertNotEqual(painted, changed)
        source["models"]["house"]["ops"][-1][2] = 0
        with self.assertRaises(ValueError):
            compile_catalogue(source)

    def test_clustered_colour_grain_preserves_voxel_geometry_and_masked_materials(self):
        ops = [["box", "wall", 0,0,0,8,6,5], ["erase", 0,0,0,1,1,1],
               ["paint", "window", 7,0,0,8,6,5],
               ["scatter_paint", "grain", 3, 1576, 0,0,0,8,6,5, "wall", [2,2,2]]]
        source = self.source(ops)
        source["materials"]["grain"] = 109
        model = compile_catalogue(source)["models"]["house"]
        self.assertEqual(model, compile_catalogue(source)["models"]["house"])
        cells = {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertEqual(len(cells), 8*6*5-1)
        self.assertNotIn((0,0,0), cells)
        groups = {}
        for (x,y,z), material in cells.items():
            if x == 7:
                self.assertEqual(material, 2)
            else:
                groups.setdefault((x//2,y//2,z//2), set()).add(material)
        self.assertTrue(all(len(colours) == 1 for colours in groups.values()))
        self.assertEqual({next(iter(colours)) for colours in groups.values()}, {1,3})
        for block in ([0,2,2], [2,-1,2], [2,2.5,2], [2,2], [2048,2,2]):
            with self.subTest(block=block), self.assertRaises(ValueError):
                invalid = self.source(ops[:-1]+[ops[-1][:-1]+[block]])
                invalid["materials"]["grain"] = 109
                compile_catalogue(invalid)

    def check_column_lifecycle(self, family, base, first_bark, last_bark=109, first_dying_shape_unchanged=False):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith(f"tree_{family}_")}
        source["bindings"] = {"trees": {str(base): source["bindings"]["trees"][str(base)]}}
        result = compile_catalogue(source)
        self.assertEqual(set(result["bindings"]["trees"][str(base)]), set(map(str, range(7))))
        occupied = []
        for stage in range(7):
            model = result["models"][f"tree_{family}_{stage:02}"]
            cells = {(x+i, y, z): material for x, y, z, length, material in model["runs"] for i in range(length)}
            occupied.append(len(cells))
            with self.subTest(stage=stage):
                self.assertTrue(any(z == 0 for x, y, z in cells))
                visited, todo = set(), [next(iter(cells))]
                while todo:
                    point = todo.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x, y, z = point
                    todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(visited, set(cells), "A leaf/branch cluster floats away from its trunk")
                if stage == 6:
                    colours = {colour for material in cells.values() for colour in result["materials"][material-1]}
                    self.assertTrue(colours <= set(range(first_bark, last_bark+1)), "The bare stage retained foliage paint")
        self.assertLess(occupied[0], occupied[1])
        self.assertLess(occupied[1], occupied[2])
        self.assertLess(occupied[2], occupied[3])
        if first_dying_shape_unchanged:
            self.assertEqual(occupied[4], occupied[3])
            self.assertNotEqual(result["models"][f"tree_{family}_04"]["runs"], result["models"][f"tree_{family}_03"]["runs"])
        else:
            self.assertLess(occupied[4], occupied[3])
        self.assertLess(occupied[5], occupied[4])
        self.assertLess(occupied[6], occupied[5])

    def test_lime_lifecycle_keeps_branches_connected_and_sheds_actual_leaf_volume(self):
        self.check_column_lifecycle("lime", 1576, 105)

    def test_silver_lifecycle_keeps_branches_connected_and_sheds_actual_leaf_volume(self):
        self.check_column_lifecycle("silver", 1583, 104)

    def test_spruce_lifecycle_keeps_hanging_boughs_attached_to_wood(self):
        self.check_column_lifecycle("spruce", 1590, 104, 110)

    def test_olive_column_lifecycle_retains_grey_forks_and_real_foliage_loss(self):
        self.check_column_lifecycle("olive_column", 1597, 2, 7)

    def test_temperate_tree_lifecycles_keep_rooted_branches_and_real_foliage_loss(self):
        families = (
            ("autumn", 1604, 2, 7), ("vase", 1611, 105, 109),
            ("elm", 1618, 105, 109), ("low_spread", 1625, 105, 109),
            ("pear", 1632, 105, 109), ("tall_spread", 1639, 105, 109),
            ("round", 1646, 105, 109), ("silvergreen", 1653, 2, 7),
            ("redspread", 1660, 2, 7), ("cedar", 1667, 2, 7),
            ("rust", 1674, 2, 7), ("oliveround", 1681, 105, 109),
            ("teal", 1688, 105, 109), ("tanspread", 1695, 105, 109),
            ("gold", 1702, 2, 7),
        )
        for family, base, first_bark, last_bark in families:
            with self.subTest(family=family):
                self.check_column_lifecycle(f"temperate_{family}", base, first_bark, last_bark)

    def test_arctic_and_tropical_lifecycles_remain_rooted_and_snow_preserves_occupancy(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith(("tree_arctic_", "tree_tropical_"))}
        source["bindings"] = {"trees": {base: states for base, states in source["bindings"]["trees"].items() if all(name in source["models"] for name in states.values())}}
        result = compile_catalogue(source)
        self.assertEqual(len(result["bindings"]["trees"]), 30)
        for base, states in result["bindings"]["trees"].items():
            self.assertEqual(set(states), set(map(str, range(7))))
            for stage, name in states.items():
                with self.subTest(base=base, stage=stage):
                    model = result["models"][name]
                    cells = {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
                    roots = {p for p in cells if p[2] == 0}
                    self.assertTrue(roots)
                    if base == "1926":
                        self.assertGreater(min(y for x,y,z in roots), max(x for x,y,z in roots), "The peach palm's bent foot must extend along positive Y, toward the source's right-hand side")
                    visited, todo = set(roots), list(roots)
                    for x,y,z in todo:
                        for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                            if point in cells and point not in visited:
                                visited.add(point)
                                todo.append(point)
                    self.assertEqual(len(visited), len(cells), "Detached foliage or a branch lost its root connection")
                    self.assertLessEqual(model["origin"][2], 0)
                    self.assertGreaterEqual(model["origin"][2]+model["cell_size"][2], 0)
                    if name.startswith("tree_arctic_snow_"):
                        dry = result["models"][name.replace("tree_arctic_snow_", "tree_arctic_")]
                        self.assertEqual(set(cells), {(x+i,y,z) for x,y,z,length,_ in dry["runs"] for i in range(length)}, "Snow paint changed the tree footprint or filled foliage openings")
                        for material in set(cells.values()):
                            self.assertIn(result["materials"][material-1][3], range(210,215), "The lit positive-Y face lost its snow")
                            self.assertIn(result["materials"][material-1][5], range(210,215), "An upward branch face lost its snow")

    def test_cactus_lifecycles_keep_grounded_forks_and_source_green_to_brown_states(self):
        self.check_column_lifecycle("saguaro", 1912, 104, 111)
        self.check_column_lifecycle("column_cactus", 1919, 104, 111, first_dying_shape_unchanged=True)
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith(("tree_saguaro_","tree_column_cactus_"))}
        source["bindings"] = {"trees": {key:source["bindings"]["trees"][key] for key in ("1912","1919")}}
        result = compile_catalogue(source)
        for family, maximum_height in (("saguaro",27),("column_cactus",11)):
            for stage in range(7):
                model = result["models"][f"tree_{family}_{stage:02}"]
                cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                colours = {colour for material in cells.values() for colour in result["materials"][material-1]}
                with self.subTest(family=family,stage=stage):
                    self.assertLessEqual(model["origin"][2]+(max(z for x,y,z in cells)+1)*model["cell_size"][2],maximum_height)
                    self.assertLessEqual(model["origin"][2]+min(z for x,y,z in cells)*model["cell_size"][2],0)
                    if stage < 4:
                        self.assertTrue(colours <= set(range(88,95)))
                    elif stage < 6:
                        self.assertTrue(colours & set(range(88,95)))
                        self.assertTrue(colours & set(range(104,112)))
            if family == "saguaro":
                model = result["models"]["tree_saguaro_03"]
                cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
                self.assertIn((3,9,44),cells,"The high rising arm is missing")
                self.assertIn((19,9,26),cells,"The lower opposite arm is missing")
                self.assertIn((11,16,22),cells,"The forward fork is missing")
                self.assertNotIn((7,9,40),cells,"The characteristic fork gap was filled")

    def test_tropical_palms_keep_connected_fronds_root_anchors_and_distinct_lifecycle_materials(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("tree_palm_")}
        source["bindings"] = {"trees": {key:source["bindings"]["trees"][key] for key in ("1821","1828")}}
        result = compile_catalogue(source)
        for family, base, green in (("bent","1821",set(range(96,103))), ("tuft","1828",set(range(88,95)))):
            self.assertEqual(set(result["bindings"]["trees"][base]),set(map(str,range(7))))
            occupied = []
            for stage in range(7):
                model = result["models"][f"tree_palm_{family}_{stage:02}"]
                cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                occupied.append(len(cells))
                with self.subTest(family=family,stage=stage):
                    visited, todo = set(), [next(iter(cells))]
                    while todo:
                        point = todo.pop()
                        if point in visited:
                            continue
                        visited.add(point)
                        x,y,z = point
                        todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                    self.assertEqual(len(visited),len(cells),"A frond or leaf blade is detached from the stem")
                    roots = [(x,y,z) for x,y,z in cells if model["origin"][2]+z*model["cell_size"][2] <= 0]
                    self.assertTrue(roots)
                    for axis in (0,1):
                        self.assertLessEqual((max(p[axis] for p in roots)-min(p[axis] for p in roots)+1)*model["cell_size"][axis],1)
                    colours = {colour for material in cells.values() for colour in result["materials"][material-1]}
                    if stage < 4:
                        allowed = green | set(range(114,122)) | (set(range(7,14)) if family == "tuft" else set())
                        self.assertTrue(colours <= allowed)
                    if stage < 6:
                        self.assertTrue(colours & green)
                    if stage >= 4:
                        self.assertTrue(colours & set(range(104,112)))
                    if stage == 6:
                        self.assertFalse(colours & (set(range(88,95)) | set(range(96,103))))
                    root_colours = {colour for point in roots for colour in result["materials"][cells[point]-1]}
                    self.assertEqual(bool(root_colours & set(range(7,14))),family == "tuft","The source-specific white foot was lost or aliased")
            self.assertTrue(occupied[0] < occupied[1] < occupied[2] < occupied[3])
            self.assertTrue(occupied[3] > occupied[4] > occupied[5] > occupied[6])
        for stage in range(7):
            self.assertNotEqual(result["models"][f"tree_palm_bent_{stage:02}"]["runs"],result["models"][f"tree_palm_tuft_{stage:02}"]["runs"])

    def test_locomotives_keep_rail_contact_connected_fittings_and_distinct_toyland_art(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("rail_loco_")}
        source["bindings"] = {"vehicles":{engine:states for engine,states in source["bindings"]["vehicles"].items() if any(name.startswith("rail_loco_") for name in states.values())}}
        result,definitions = compile_catalogue(source),vehicle_definitions()
        for engine,states in result["bindings"]["vehicles"].items():
            for state,name in states.items():
                self.assertEqual(name,states[str(int(state)^1)],"Original locomotive body artwork has identical cargo states")
            if definitions[engine]["climates"] == ["Y"]:
                self.assertEqual(set(states),{"6","7"})
            for climate in definitions[engine]["climates"]:
                for loaded in range(2):
                    self.assertTrue(str("TASY".index(climate)*2+loaded) in states or str(loaded) in states,(engine,climate,loaded))
        for first,second in ((0,2),(8,3),(9,4)):
            self.assertNotEqual(result["bindings"]["vehicles"][str(first)]["0"],result["bindings"]["vehicles"][str(second)]["6"],"Different Toyland artwork aliased an ordinary locomotive")
        self.assertEqual(result["bindings"]["vehicles"]["8"],result["bindings"]["vehicles"]["10"])
        self.assertEqual(result["bindings"]["vehicles"]["13"],result["bindings"]["vehicles"]["15"])
        for engine in (1,16,17,18,19,20,21):
            states = result["bindings"]["vehicles"][str(engine)]
            self.assertEqual(set(states),{"2","3","4","5"})
            self.assertNotEqual(states["2"],states["4"],"Distinct Arctic/tropical locomotive artwork was aliased")
        for normal,toy in ((17,5),(16,6),(55,56),(84,88)):
            first = result["bindings"]["vehicles"][str(normal)]
            second = result["bindings"]["vehicles"][str(toy)]
            self.assertFalse(set(first.values()) & set(second.values()),"Independent Toyland eyes/lamp/body artwork was lost")
        for name,model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
            self.assertEqual(model["origin"][2]+min(z for x,y,z in cells)*model["cell_size"][2],0.5)
            self.assertEqual({model["origin"][1]+(y+0.5)*model["cell_size"][1] for x,y,z in cells if z == 0},{-1.375,-1.125,1.125,1.375},name)
            visited = {next(iter(cells))}; pending = list(visited)
            for x,y,z in pending:
                for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                    if point in cells and point not in visited:
                        visited.add(point); pending.append(point)
            self.assertEqual(len(visited),len(cells),f"Detached locomotive wheels, chimney, cab or fittings in {name}: {sorted(cells-visited)[:8]}")
            if name in ("rail_loco_kirby","rail_loco_jubilee","rail_loco_a4","rail_loco_ploddyphut","rail_loco_powernaut","rail_loco_mightymover"):
                self.assertNotIn((4,6,20),cells,"The steam cab lost its actual rear opening")
                self.assertNotIn((9,0,2),cells,"The first steam driving wheel lost its open spoke aperture")
                self.assertIn((10,0,3),cells,"The original coupled driving-rod connection disappeared")

    def test_sh_electric_has_connected_running_gear_and_open_pantograph_frames(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name == "rail_sh_electric" or name.startswith("rail_collector_sh_")}
        source["bindings"] = {"vehicles": {engine: source["bindings"]["vehicles"][engine] for engine in ("23", "24")}}
        models = compile_catalogue(source)["models"]
        model = models["rail_sh_electric"]
        cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        visited, todo = set(), [next(iter(cells))]
        while todo:
            point = todo.pop()
            if point in visited:
                continue
            visited.add(point)
            x,y,z = point
            todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
        self.assertEqual(visited, cells, "A wheel or roof member is detached")
        for name,x in (("rail_collector_sh_front",12),("rail_collector_sh_rear",28)):
            collector = models[name]
            frame = {(x+i,y,z) for x,y,z,length,_ in collector["runs"] for i in range(length)}
            self.assertEqual(collector["origin"][2],model["origin"][2]+24*model["cell_size"][2],"The separate collector mount detached from the roof insulator")
            for y in (4, 9):
                self.assertNotIn((x,y,7),frame,"The pantograph diamond was filled in")
                self.assertIn((x,y,14),frame)
                self.assertIn((x,y,23),cells,"The separate frame lost its fixed roof insulator")
        self.assertEqual({model["origin"][1]+(y+0.5)*model["cell_size"][1] for x,y,z in cells if z == 0},{-1.375,-1.125,1.125,1.375},"SH electric wheel treads must straddle the running rails")

    def test_electric_collectors_are_connected_and_touch_fixed_roof_insulators(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name in ("rail_sh_electric","rail_loco_tim","rail_loco_asiastar") or name.startswith("rail_collector_")}
        source["bindings"] = {category:{engine:states for engine,states in source["bindings"][category].items() if engine in ("23","24","25","26")} for category in ("vehicles","vehicle_collectors")}
        result = compile_catalogue(source)
        def cells(model):
            return {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
        for engine,parts in result["bindings"]["vehicle_collectors"].items():
            body = result["models"][result["bindings"]["vehicles"][engine]["0"]]
            surface = {(body["origin"][0]+(x+0.5)*body["cell_size"][0],body["origin"][1]+(y+0.5)*body["cell_size"][1],body["origin"][2]+(z+1)*body["cell_size"][2]) for x,y,z in cells(body)}
            for name in parts.values():
                frame = result["models"][name]
                occupied = cells(frame)
                visited = {next(iter(occupied))}; pending = list(visited)
                for x,y,z in pending:
                    for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                        if point in occupied and point not in visited:
                            visited.add(point); pending.append(point)
                self.assertEqual(visited,occupied,name)
                feet = {(frame["origin"][0]+(x+0.5)*frame["cell_size"][0],frame["origin"][1]+(y+0.5)*frame["cell_size"][1],frame["origin"][2]) for x,y,z in occupied if z == 0}
                joined = feet & surface
                self.assertTrue(joined,(engine,name,"collector floats above the roof"))
                self.assertGreater(max(y for x,y,z in joined)-min(y for x,y,z in joined),1,"The collector needs both transverse roof supports")
        for engine in ("23","25"):
            broken = json.loads(json.dumps(source))
            broken["bindings"]["vehicle_collectors"][engine]["2"] = "rail_collector_single"
            with self.assertRaisesRegex(ValueError,"complete independently mounted collectors"):
                compile_catalogue(broken)

    def test_refinery_vessels_frames_and_pipes_keep_source_states_openings_and_ground_contact(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("refinery_") or name == "mine_ground_site"}
        source["bindings"] = {category:{graphics:states for graphics,states in source["bindings"][category].items() if 18 <= int(graphics) <= 23} for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        palettes = {
            (18,0): {1,2,3,76,123}, (18,1): set(range(2,14)) | set(range(198,206)),
            (18,2): set(range(2,15)) | {66,122,123,124} | set(range(73,79)) | set(range(198,205)),
            (19,0): {1,2,3}, (19,1): set(range(2,14)) | set(range(199,205)),
            (19,2): set(range(1,14)) | {56,65,66,162,163,179,180,181,195} | set(range(199,205)),
            (20,0): {1,2,3}, (20,1): set(range(2,14)) | {163,181},
            (20,3): {1} | set(range(3,14)) | {56,65,151,152,153,162,163,179,180,181,187,188,189,195} | set(range(232,239)),
            (21,0): set(range(71,78)) | {122,123,124},
            (21,1): set(range(71,79)) | {122,123,124,163} | set(range(178,183)) | set(range(200,205)),
            (21,2): {56,65} | set(range(71,78)) | {122,123,124,162,163,164} | set(range(178,183)) | set(range(200,206)),
            (22,0): set(range(71,78)) | {122,123,124},
            (22,1): set(range(2,13)) | set(range(71,78)) | {122,123,124},
            (22,2): set(range(2,13)) | set(range(71,79)) | {122,123,124} | set(range(199,205)),
            (23,0): {2}, (23,1): {1,2} | set(range(5,16)) | set(range(32,37)),
            (23,2): set(range(5,16)) | set(range(32,37)) | set(range(128,132)),
        }
        cells = {name:{(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)} for name,model in result["models"].items()}
        for graphics,states in result["bindings"]["industries"].items():
            self.assertEqual(set(states),{"0","1","2","3"})
            self.assertEqual(states["1"] if graphics == "20" else states["3"],states["2"])
            for stage,name in states.items():
                canonical = (1 if int(stage) in (1,2) else int(stage)) if graphics == "20" else min(int(stage),2)
                original = palettes[int(graphics),canonical]
                colours = {colour for material in cells[name].values() for colour in result["materials"][material-1]}
                self.assertTrue(colours <= original,(name,sorted(colours-original)))
        for name,occupied in cells.items():
            model = result["models"][name]
            pending = set(occupied)
            while pending:
                points = [pending.pop()]
                for x,y,z in points:
                    for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                        if point in pending:
                            pending.remove(point); points.append(point)
                self.assertTrue(any(z == 0 for x,y,z in points),(name,"Detached pipe, flame, tank or frame",points[:4]))
            self.assertTrue(all(0 <= model["origin"][axis]+point[axis]*model["cell_size"][axis] < 16 for point in occupied for axis in (0,1)),name)
        for name,centre,top in (("refinery_tank_open",(16,16),24),("refinery_fractionator_open",(16,16),58)):
            self.assertTrue(all((*centre,z) not in cells[name] for z in range(1,top)),"Construction vessels must remain genuinely hollow")
        for name in ("refinery_cooler_build","refinery_cooler"):
            self.assertTrue(all((16,18,z) not in cells[name] for z in range(38,55)),"The cooling box lost its original open top")
        for name in ("refinery_process_site","refinery_process_build","refinery_process"):
            self.assertNotIn((16,16,18),cells[name],"Open process framing became a solid block")
        for name in ("refinery_office_site","refinery_office_build","refinery_office"):
            self.assertTrue(all((22,24,z) not in cells[name] for z in range(15)),"The original office's L-shaped footprint was filled")
        for states in result["bindings"]["industry_ground"].values():
            self.assertEqual([states[str(stage)] for stage in range(4)],["mine_ground_site"]*3+["refinery_paved_ground"])
            for name in states.values():
                model = result["models"][name]
                self.assertEqual(len(cells[name]),32*32)
                self.assertEqual(model["origin"][2]+model["cell_size"][2],0)

    def test_forest_growth_keeps_nine_rooted_pines_and_independent_original_litter(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("forest_")}
        source["bindings"] = {category:{graphics:states for graphics,states in source["bindings"][category].items() if int(graphics) in (16,17)} for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        growing = result["bindings"]["industries"]["16"]
        self.assertEqual(set(growing),{"0","1","2","3"})
        self.assertEqual(len(set(growing.values())),4)
        logs = result["bindings"]["industries"]["17"]
        self.assertEqual(set(logs),{"0","1","2","3"})
        self.assertEqual(len(set(logs.values())),1,"Original2076 is identical in all four source-table slots")
        heights = []
        for stage,name in growing.items():
            model = result["models"][name]
            cells = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
            heights.append(max(z for x,y,z in cells))
            original = {2} | set(range(80,87)) | set(range(104,111 if stage == "1" else 112))
            colours = {colour for material in cells.values() for colour in result["materials"][material-1]}
            self.assertTrue(colours <= original,(name,sorted(colours-original)))
            # No growth stage may move the plantation's roots or connect its
            # nine original trunks into a raised solid base.
            roots = {(x,y) for x,y,z in cells if z == 0}
            patches = []
            while roots:
                points = [roots.pop()]
                for x,y in points:
                    for point in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                        if point in roots:
                            roots.remove(point); points.append(point)
                patches.append(tuple(model["origin"][axis]+(min(p[axis] for p in points)+max(p[axis] for p in points)+1)*model["cell_size"][axis]/2 for axis in (0,1)))
            self.assertEqual(set(patches),{(x,y) for x in (3,8,13) for y in (3,8,13)})
        self.assertEqual(heights,sorted(set(heights)),"Every original forest growth stage must increase the crown height")
        for name,model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
            if name == "forest_ground":
                self.assertEqual(len(cells),32*32)
                self.assertEqual(model["origin"],[0,0,-0.25])
                self.assertEqual(model["cell_size"],[0.5,0.5,0.25])
                continue
            pending = set(cells)
            while pending:
                points = [pending.pop()]
                for x,y,z in points:
                    for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                        if point in pending:
                            pending.remove(point); points.append(point)
                self.assertTrue(any(z == 0 for x,y,z in points),(name,"Unsupported crown, log or stump",points[:4]))
        for states in result["bindings"]["industry_ground"].values():
            self.assertEqual(set(states),{"0","1","2","3"})
            self.assertEqual(set(states.values()),{"forest_ground"})

    def test_sawmill_construction_roofs_and_timbers_have_grounded_parts_and_source_palettes(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("sawmill_") or name == "mine_ground_site"}
        source["bindings"] = {category:{graphics:states for graphics,states in source["bindings"][category].items() if 11 <= int(graphics) <= 15} for category in ("industries","industry_ground")}
        result = compile_catalogue(source)
        palettes = {
            (11,0): {1,2,3}, (11,1): set(range(1,7)) | set(range(104,111)), (11,2): set(range(1,13)) | set(range(104,110)),
            (12,0): {1,2,3}, (12,1): {1,2,3,4,6} | set(range(104,110)), (12,2): set(range(1,9)) | {20,38,39,57,58,59,119,121} | set(range(104,111)) | set(range(227,232)),
            (13,0): {1,2,3}, (13,1): {1,2,3} | set(range(104,111)), (13,2): set(range(1,10)) | set(range(104,110)),
            (14,3): {56,57,58,60,61,62,63,64}, (15,3): set(range(55,60)) | set(range(105,111)),
        }
        for graphics,states in result["bindings"]["industries"].items():
            self.assertEqual(set(states),{"3"} if int(graphics) >= 14 else {"0","1","2","3"})
            if int(graphics) < 14:
                self.assertEqual(states["2"],states["3"])
                self.assertNotEqual(states["0"],states["1"])
            for stage,name in states.items():
                model = result["models"][name]
                occupied = {(x+i,y,z):material for x,y,z,length,material in model["runs"] for i in range(length)}
                colours = {colour for material in occupied.values() for colour in result["materials"][material-1]}
                original = palettes[(int(graphics),min(int(stage),2) if int(graphics) < 14 else 3)]
                self.assertTrue(colours <= original,(name,sorted(colours-original)))
                pending = set(occupied)
                while pending:
                    points = [pending.pop()]
                    for x,y,z in points:
                        for point in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                            if point in pending:
                                pending.remove(point); points.append(point)
                    self.assertTrue(any(z == 0 for x,y,z in points),(name,"Detached roof truss, board or machinery",points[:4]))
                self.assertTrue(all(0 <= model["origin"][axis]+point[axis]*model["cell_size"][axis] < 16 for point in occupied for axis in (0,1)),name)
        for family,point in (("northlight",(12,12,5)),("cutting",(8,8,5)),("store",(16,16,8))):
            for stage in ("frame","house"):
                model = result["models"][f"sawmill_{family}_{stage}"]
                cells = {(x+i,y,z) for x,y,z,length,_ in model["runs"] for i in range(length)}
                self.assertNotIn(point,cells,"The sawmill's open interior was filled")
        for states in result["bindings"]["industry_ground"].values():
            self.assertEqual(set(states),{"0","1","2","3"})
            self.assertEqual(set(states.values()),{"mine_ground_site"},"The original3924 substrate must retain independent full-tile ownership")

    def test_shops_offices_keep_one_footprint_with_open_construction_rooms(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("shops_offices")}
        source["bindings"] = {"houses": {"14": source["bindings"]["houses"]["14"]}}
        result = compile_catalogue(source)
        volumes = {}
        for name, model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            origin, scale = model["origin"], model["cell_size"]
            contact = [(origin[0]+x*scale[0],origin[1]+y*scale[1]) for x,y,z in cells
                       if origin[2]+z*scale[2] <= 0 <= origin[2]+(z+1)*scale[2]]
            with self.subTest(model=name):
                self.assertEqual(origin[:2], [1,3])
                self.assertEqual([min(p[i] for p in contact) for i in (0,1)], [2,4])
                self.assertEqual([max(p[i] for p in contact)+scale[i] for i in (0,1)], [14,13])
        self.assertIn((4,18,14), volumes["shops_offices"])
        self.assertNotIn((4,18,14), volumes["shops_offices_shell"])
        # The source construction frame has open bays, not the completed
        # window's horizontal sash left behind after erasing its glass.
        shell = volumes["shops_offices_shell"]
        for floor in range(4):
            for z in range(12+floor*9,19+floor*9):
                for y in (2,3,18,19):
                    self.assertNotIn((5,y,z), shell)
                for x in (2,3,24,25):
                    self.assertNotIn((x,6,z), shell)
        self.assertNotIn((10,10,21), volumes["shops_offices_shell"])
        self.assertNotIn((10,10,50), volumes["shops_offices_shell"])
        self.assertEqual(set(result["bindings"]["houses"]["14"]), set(map(str,range(4))))

    def test_reviewed_office_and_mine_contacts_remain_on_their_ground_tiles(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items()
                            if name.startswith(("red_z_office", "mine_"))}
        source["bindings"] = {}
        models = compile_catalogue(source)["models"]
        for name, model in models.items():
            origin, scale = model["origin"], model["cell_size"]
            contacts = [(x,y,length) for x,y,z,length,material in model["runs"]
                        if origin[2]+z*scale[2] <= 0 <= origin[2]+(z+1)*scale[2]]
            with self.subTest(model=name):
                self.assertTrue(contacts, "A grounded structure has lost contact with the terrain")
                self.assertTrue(all(origin[0]+x*scale[0] >= 0 and origin[0]+(x+length)*scale[0] <= 16 and
                                    origin[1]+y*scale[1] >= 0 and origin[1]+(y+1)*scale[1] <= 16 for x,y,length in contacts),
                                "Ground-contact cells spill beyond the original playable tile")
        self.assertEqual(models["red_z_office"]["origin"], models["red_z_office_frame"]["origin"])
        self.assertEqual(models["red_z_office"]["origin"][:2], models["red_z_office_site"]["origin"][:2])
        self.assertEqual(models["mine_engine_house"]["origin"][:2], models["mine_engine_site"]["origin"][:2])

    def test_road_depot_rotations_keep_two_truck_lanes_and_floor_separate(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("road_depot_")}
        source["bindings"] = {category: {"4": source["bindings"][category]["4"]} for category in ("depots", "depot_floors")}
        result = compile_catalogue(source)
        for state in range(8):
            direction = state%4
            model = result["models"][result["bindings"]["depots"]["4"][str(state)]]
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            def point(x, y, z):
                return ((31-x,31-y,z),(31-y,x,z),(x,y,z),(y,31-x,z))[direction]
            with self.subTest(direction=direction, toyland=state >= 4):
                for lane in (10,22):
                    self.assertTrue(all(point(x,y,z) not in cells for x in range(3,32) for y in range(lane-3,lane+3) for z in range(11)),
                                    "A wall/roof member obstructs a truck lane at the doorway")
                self.assertIn(point(1,16,5), cells)
                self.assertIn(point(16,1,5), cells)
                self.assertTrue(any(z >= 17 for x,y,z in cells), "The folded roof has lost its raised ridges")
        floor = result["models"][result["bindings"]["depot_floors"]["4"]["0"]]
        self.assertEqual(floor["occupied"], 32*32)
        self.assertEqual(floor["origin"][2]+floor["cell_size"][2], 0)

    def test_mine_ground_keeps_playable_tile_coverage_and_matching_coal_contact(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("mine_ground_")}
        source["bindings"] = {"industry_ground": {graphics:states for graphics,states in source["bindings"]["industry_ground"].items()
                                                 if all(name in source["models"] for name in states.values())}}
        result = compile_catalogue(source)
        volumes = {}
        for name, model in result["models"].items():
            cells = {(x+i,y,z): material for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            with self.subTest(model=name):
                self.assertEqual([model["size"][i]*model["cell_size"][i] for i in (0,1)], [16,16])
                self.assertEqual(model["origin"][2]+model["cell_size"][2], 0)
                self.assertTrue(all((x,y,0) in cells for y in range(32) for x in range(32)), "The original ground tile has a hole")
                columns = {}
                for x,y,z in cells:
                    columns.setdefault((x,y),set()).add(z)
                self.assertTrue(all(zs == set(range(max(zs)+1)) for zs in columns.values()), "A coal layer floats above its substrate")
        left = {(y,z): material for (x,y,z),material in volumes["mine_ground_heap_left"].items() if x == 31 and z > 0}
        right = {(y,z): material for (x,y,z),material in volumes["mine_ground_heap_right"].items() if x == 0 and z > 0}
        self.assertTrue(left)
        self.assertEqual(left, right, "Joined stockpile edges disagree in height or palette material")
        for graphics in map(str, range(7)):
            self.assertEqual(set(result["bindings"]["industry_ground"][graphics]), set(map(str, range(4))))

    def test_mound_has_supported_tapering_columns_and_open_corners(self):
        source = self.source([["mound", "wall", 0,0,0,8,6,5]])
        model = compile_catalogue(source)["models"]["house"]
        cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
        self.assertNotIn((0,0,0), cells)
        self.assertIn((3,2,3), cells)
        self.assertNotIn((1,2,3), cells)
        for x,y,z in cells:
            self.assertTrue(all((x,y,below) in cells for below in range(z)), "The pile contains a floating stratum")
            self.assertIn((7-x,5-y,z), cells)

    def test_coal_truck_keeps_empty_tipper_open_and_payload_connected(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("road_balogh_coal_")}
        source["bindings"] = {"vehicles": {"123": source["bindings"]["vehicles"]["123"]}}
        result = compile_catalogue(source)
        states = []
        for state in ("empty", "loaded"):
            model = result["models"][f"road_balogh_coal_{state}"]
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            states.append(cells)
            visited, todo = set(), [next(iter(cells))]
            while todo:
                point = todo.pop()
                if point in visited:
                    continue
                visited.add(point)
                x,y,z = point
                todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
            with self.subTest(state=state):
                self.assertEqual(visited, cells, "A wheel, cab part or coal cluster is detached")
                for x in (7,14,28):
                    self.assertIn((x,0,4), cells)
                    self.assertIn((x,10,4), cells)
        self.assertNotIn((15,5,19), states[0])
        self.assertIn((15,5,19), states[1])
        self.assertLess(states[0], states[1])
        self.assertTrue(all(3 <= x < 21 and 2 <= y < 9 and 17 <= z < 30 for x,y,z in states[1]-states[0]),
                        "The cargo state changed the cab/rim or spilled outside the tipper")

    def test_rail_depot_families_preserve_open_routes_and_all_ground_states(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name:model for name,model in source["models"].items() if name.startswith("rail_depot_")}
        source["bindings"] = {category:{kind:states for kind,states in source["bindings"][category].items() if int(kind)<4}
                              for category in ("depots","depot_floors","depot_wires")}
        result = compile_catalogue(source)
        for kind in map(str,range(4)):
            for state in range(8):
                model = result["models"][result["bindings"]["depots"][kind][str(state)]]
                cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
                def point(x,y,z):
                    return ((31-x,31-y,z),(31-y,x,z),(x,y,z),(y,31-x,z))[state%4]
                with self.subTest(kind=kind,state=state):
                    for x in range(8,32):
                        for y in range(13,20):
                            for z in range(1,12):
                                self.assertNotIn(point(x,y,z),cells,"The train/Cab corridor is blocked")
                    # A head-on Cab view sees the rear wall through the open bay.
                    # Its first centre-line body hit must be that wall, never the
                    # entrance plane or an accidental solid interior partition.
                    for z in (3,6,10):
                        first_hit = next(x for x in range(31,-1,-1) if point(x,16,z) in cells)
                        self.assertEqual(first_hit,4,"A depot exit view hits a wall before reaching the back of the open bay")
                    self.assertTrue(all(0 <= x < 32 and 0 <= y < 32 for x,y,z in cells if z == 0))
            for state in range(4):
                floor = result["models"][result["bindings"]["depot_floors"][kind][str(state)]]
                cells = {(x+i,y,z) for x,y,z,length,material in floor["runs"] for i in range(length)}
                self.assertEqual(cells,{(x,y,0) for x in range(32) for y in range(32)})
                self.assertEqual(floor["origin"][2]+floor["cell_size"][2],0)
        wire = result["models"]["rail_depot_wire"]
        cells = {(x+i,y,z) for x,y,z,length,material in wire["runs"] for i in range(length)}
        self.assertEqual(min(z for x,y,z in cells)*wire["cell_size"][2],10)
        self.assertEqual(set(result["bindings"]["depot_wires"]["1"]),{"0","1","2","3"})

    def test_mine_winding_frames_keep_open_connected_wheels_and_ropes(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("mine_head_")}
        source["bindings"] = {"industries": {graphics: source["bindings"]["industries"][graphics] for graphics in ("0", "1")}}
        result = compile_catalogue(source)
        frames = []
        for name, model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            visited, todo = set(), [next(iter(cells))]
            while todo:
                point = todo.pop()
                if point in visited:
                    continue
                visited.add(point)
                x,y,z = point
                todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
            with self.subTest(model=name):
                self.assertEqual(visited, cells, "A wheel, shaft member or winding rope is detached")
                self.assertNotIn((22,10,23), cells, "The open shaft was filled in")
                if name[-2:].isdigit():
                    frames.append(cells)
                    for x in (18, 26):
                        self.assertIn((x,43,15), cells)
                        self.assertIn((x,6,36), cells)
                        self.assertGreater(sum((x,y,z) not in cells for y in range(3,10) for z in range(28,37)), 8,
                                           "The wheel has lost its open spoke apertures")
        self.assertEqual(len({frozenset(frame) for frame in frames}), 3)

    def test_mine_construction_preserves_open_rooms_windows_and_pier_clearance(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("mine_")}
        source["bindings"] = {"industries": {graphics: source["bindings"]["industries"][graphics] for graphics in ("0", "1", "2", "3")}}
        result = compile_catalogue(source)
        def cells(name):
            return {(x+i,y,z) for x,y,z,length,material in result["models"][name]["runs"] for i in range(length)}
        for graphics in ("2", "3"):
            self.assertEqual(set(result["bindings"]["industries"][graphics]), set(map(str, range(4))))
        engine, frame = cells("mine_engine_house"), cells("mine_engine_frame")
        self.assertNotIn((6,4,4), engine)  # Recessed glass behind the outer wall skin.
        self.assertIn((6,5,4), engine)
        self.assertNotIn((6,5,4), frame)
        self.assertNotIn((10,10,12), frame)
        self.assertIn((8,12,20), frame)  # Connected roof timber above the open room.
        piers, machine, shell = cells("mine_machine_piers"), cells("mine_machine_house"), cells("mine_machine_frame")
        self.assertNotIn((16,16,4), piers)
        self.assertNotIn((16,16,4), machine)
        self.assertIn((16,16,7), machine)
        self.assertIn((10,24,11), machine)
        self.assertNotIn((10,24,11), shell)
        self.assertNotIn((16,16,22), shell)
        self.assertEqual(max(z for x,y,z in piers)+1, min(z for x,y,z in shell-piers))

    def test_cooling_tower_stages_keep_ground_contacts_open_mouths_and_connected_supports(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("power_cooling_")}
        source["bindings"] = {"industries": {"7": source["bindings"]["industries"]["7"]}}
        result = compile_catalogue(source)
        contacts = []
        heights = {}
        for name, model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            contacts.append({(x,y) for x,y,z in cells if z == 0})
            heights[name] = max(z for x,y,z in cells)+1
            with self.subTest(model=name):
                self.assertTrue(all(2 <= x < 30 and 2 <= y < 30 for x,y in contacts[-1]),
                                "Cooling supports crossed the source's (1,1)-(15,15) ground footprint")
                self.assertTrue(all((15,15,z) not in cells for z in range(1,heights[name])), "The open cooling passage was filled")
                visited, todo = set(), [next(iter(cells))]
                while todo:
                    point = todo.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(len(visited), len(cells), "A concrete ring or support pier is detached")
        self.assertTrue(all(contact == contacts[0] for contact in contacts))
        self.assertLess(heights["power_cooling_base"], heights["power_cooling_shell"])
        self.assertLess(heights["power_cooling_shell"], heights["power_cooling_tower"])
        self.assertEqual(result["bindings"]["industries"]["7"]["2"], result["bindings"]["industries"]["7"]["3"])

    def test_power_boiler_has_open_flues_and_preserves_glazed_construction(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("power_boiler_")}
        source["bindings"] = {"industries": {"8": source["bindings"]["industries"]["8"]}}
        result = compile_catalogue(source)
        volumes, contacts = {}, []
        glass = source["materials"]["power_glass"]
        for name, model in result["models"].items():
            cells = {(x+i,y,z): result["materials"][material-1] for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            contact = {(x,y) for x,y,z in cells if z == 0}
            contacts.append(contact)
            with self.subTest(model=name):
                self.assertTrue(all(0 <= x < 32 and 4 <= y < 28 for x,y in contact))
                self.assertTrue(all((25,23,z) not in cells for z in range(30,55)), "The exhaust flue is capped")
                self.assertNotIn((10,10,15), cells)
                self.assertEqual(cells[5,23,10], glass, "Construction lost its original installed glazing")
                visited, todo = set(), [next(iter(cells))]
                while todo:
                    point = todo.pop()
                    if point in visited:
                        continue
                    visited.add(point)
                    x,y,z = point
                    todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
                self.assertEqual(len(visited), len(cells), "A flue collar or building member is detached")
        self.assertEqual(contacts[0], contacts[1])
        self.assertIn((10,10,22), volumes["power_boiler_house"])
        self.assertNotIn((10,10,22), volumes["power_boiler_frame"])
        self.assertIn((1,13,23), volumes["power_boiler_frame"], "Erasing the roof also erased the original masonry gable")
        self.assertEqual(set(result["bindings"]["industries"]["8"]), {"1","2","3"}, "The transparent original stage0 gained a body")

    def test_power_generator_preserves_open_bays_and_grounded_equipment(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("power_generator_")}
        source["bindings"] = {"industries": {"9": source["bindings"]["industries"]["9"]}}
        result = compile_catalogue(source)
        volumes = {}
        for name, model in result["models"].items():
            cells = {(x+i,y,z) for x,y,z,length,material in model["runs"] for i in range(length)}
            volumes[name] = cells
            self.assertTrue(all(2 <= x < 30 and 0 <= y < 30 for x,y,z in cells if z == 0))
            self.assertNotIn((10,5,5), cells, "The equipment hall's room was filled")
        frame, complete = volumes["power_generator_frame"], volumes["power_generator_house"]
        self.assertNotIn((8,11,7), frame)
        self.assertNotIn((13,5,15), frame)
        self.assertIn((13,5,15), complete)
        self.assertIn((18,13,5), frame, "The original early outlet is missing")
        for x in (17,22,27):
            self.assertIn((x,26,0), complete)
            self.assertIn((x,26,10), complete)
        self.assertEqual(set(result["bindings"]["industries"]["9"]), {"1","2","3"})

    def test_power_gantry_is_connected_and_spark_states_keep_original_palette_families(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items()
                            if name == "power_transformer" or name.startswith("power_spark_")}
        source["bindings"] = {"industries": {"10": source["bindings"]["industries"]["10"]},
                              "infrastructure": {str(sprite): source["bindings"]["infrastructure"][str(sprite)] for sprite in range(2055,2061)}}
        result = compile_catalogue(source)
        parent = result["models"]["power_transformer"]
        cells = {(x+i,y,z) for x,y,z,length,material in parent["runs"] for i in range(length)}
        self.assertNotIn((30,40,22), cells, "The open gantry was filled")
        for x,y,z in cells:
            if z == 0:
                self.assertTrue(0 <= parent["origin"][0]+x*0.25 < parent["origin"][0]+(x+1)*0.25 <= 16)
                self.assertTrue(0 <= y*0.25 < (y+1)*0.25 <= 16)
        visited, todo = set(), [next(iter(cells))]
        while todo:
            point = todo.pop()
            if point in visited:
                continue
            visited.add(point)
            x,y,z = point
            todo.extend(p for p in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)) if p in cells and p not in visited)
        self.assertEqual(len(visited), len(cells), "A porcelain support, core or gantry member is detached")
        self.assertEqual(set(result["bindings"]["industries"]["10"]), {"3"})
        origins = []
        for frame in range(1,7):
            model = result["models"][result["bindings"]["infrastructure"][str(2054+frame)]["0"]]
            colours = {colour for x,y,z,length,material in model["runs"] for colour in result["materials"][material-1]}
            self.assertEqual(colours, set(range(210 if frame <= 4 else 211,215)))
            origins.append(tuple(model["origin"]))
        self.assertEqual(len(set(origins)), 6, "Original moving child offsets were lost")

    def test_hotel_tiles_join_at_every_stage_without_closing_construction_rooms(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {name: model for name, model in source["models"].items() if name.startswith("hotel_")}
        source["bindings"] = {"houses": {house: source["bindings"]["houses"][house] for house in ("7", "8")}}
        compiled = compile_catalogue(source)
        seams = []
        for stage in range(4):
            parts = [compiled["models"][compiled["bindings"]["houses"][house][str(stage)]] for house in ("7", "8")]
            self.assertEqual(parts[0]["origin"][1]+parts[0]["size"][1]*parts[0]["cell_size"][1], 16+parts[1]["origin"][1])
            self.assertEqual(parts[0]["origin"][2], parts[1]["origin"][2])
            rows = [{(x+i,z) for x,y,z,length,material in part["runs"] if y == row for i in range(length)}
                    for part,row in zip(parts, (31,0))]
            with self.subTest(stage=stage):
                self.assertTrue(rows[0])
                self.assertEqual(rows[0], rows[1])
            seams.append(rows[0])
        self.assertLess(seams[1], seams[3])
        self.assertEqual(seams[2], seams[3])

    def test_scatter_material_mask_preserves_borders_and_other_details(self):
        source = self.source([["box", "wall", 0,0,0,8,6,1],
                              ["ellipsoid", "window", 1,1,0,7,5,1],
                              ["scatter_paint", "ripple", 2, 17, 0,0,0,8,6,1, "window"]])
        source["materials"]["ripple"] = 245
        result = compile_catalogue(source)
        cells = {(x+i,y,z): material for x,y,z,length,material in result["models"]["house"]["runs"] for i in range(length)}
        self.assertEqual(len(cells), 48)
        self.assertEqual(cells[0,0,0], 1)
        self.assertEqual(cells[1,1,0], 1)
        self.assertIn(2, cells.values())
        self.assertIn(3, cells.values())
        source["models"]["house"]["ops"].pop()
        original = compile_catalogue(source)["models"]["house"]
        walls = {(x+i,y,z) for x,y,z,length,material in original["runs"] if material == 1 for i in range(length)}
        self.assertTrue(all(cells[point] == 1 for point in walls))
        source["models"]["house"]["ops"].append(["scatter_paint", "ripple", 2, 17, 0,0,0,8,6,1, "missing"])
        with self.assertRaises(ValueError):
            compile_catalogue(source)


if __name__ == "__main__":
    unittest.main()

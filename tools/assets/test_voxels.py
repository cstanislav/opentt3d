import json
import math
from pathlib import Path
import unittest
from compile_voxels import compile_catalogue
from compile_vehicles import definitions as vehicle_definitions


class VoxelCompilerTests(unittest.TestCase):
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
                    self.assertTrue(all((x,y,16) in canonical for x in range(32) for y in range(6,26)),"A joined deck lost its constant eight-unit elevation")
                    self.assertFalse(any(8 <= y < 24 and z >= 17 for x,y,z in canonical),"A bollard or lamp blocks the central walkway")
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
                        self.assertTrue(any(z <= 1 for x,y,z in visited),"A pile, rail or lamp floats above land/water")
                        remaining -= visited
                    colours = {colour for material in cells.values() for colour in result["materials"][material-1]}
                    if int(graphics) >= 4:
                        animated = {241,242,243,250,251,252,253,254}
                        self.assertEqual(colours & animated,animated if climate == "0" else set(),"Original lamp/foam climate selection changed")
                    else:
                        self.assertTrue(colours & set(range(198,206)),"Original company-coloured bank railing was lost")
                        for x,y,z in canonical:
                            terrain_step = x//2 if int(graphics) in (0,3) else (31-x)//2
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

    def test_sh_electric_has_connected_running_gear_and_open_pantograph_frames(self):
        source = json.loads((Path(__file__).resolve().parents[2] / "assets/3d/voxels.json").read_text())
        source["models"] = {"rail_sh_electric": source["models"]["rail_sh_electric"]}
        source["bindings"] = {"vehicles": {engine: source["bindings"]["vehicles"][engine] for engine in ("23", "24")}}
        model = compile_catalogue(source)["models"]["rail_sh_electric"]
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
        for x in (12, 28):
            for y in (4, 9):
                self.assertNotIn((x,y,31), cells, "The pantograph diamond was filled in")
                self.assertIn((x,y,38), cells)
        self.assertTrue(any(y == 0 for x,y,z in cells))
        self.assertTrue(any(y == 13 for x,y,z in cells))

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
        source["bindings"] = {"industry_ground": source["bindings"]["industry_ground"]}
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

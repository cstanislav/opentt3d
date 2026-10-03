#!/usr/bin/env python3
"""Preserve original HQ/statue commands and source state in a public-NoAI save.

This does not force HQ score/size, place unavailable landmarks, edit terrain or
invent a scripting API. AIObjectType.BuildObject invokes the original owned-land
command; naturally generated transmitter/lighthouse objects stay intact.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import time


def statue_ground_replacement():
    """Test-only ActionA changes one ground chart, never a body or gameplay property.

    Its deliberately conspicuous diamond tests complete-family source fallback;
    it is not new object artwork or a coverage/quality candidate.
    """
    def pseudo(payload):
        return struct.pack("<HB",len(payload),0xff)+payload
    pixels = bytes((73 if (x//4+y//4)%2 else 199) if abs(x-31.5) < 2*min(y+1,31-y) else 0
                   for y in range(31) for x in range(64))
    compressed = b"".join(bytes([len(pixels[start:start+127])])+pixels[start:start+127] for start in range(0,len(pixels),127))
    header = b"\x08\x08O3OGPartial original object ground fixture\0Source-only concrete-chart replacement; no body or command changes.\0"
    action = b"\x0a\x01\x01"+struct.pack("<H",1420) # Original SPR_CONCRETE_GROUND.
    sprite = struct.pack("<HBBHhh",8+len(compressed),2,31,64,-32,0)+compressed
    return pseudo(struct.pack("<I",3))+pseudo(header)+pseudo(action)+sprite+b"\0\0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--climate",choices=("temperate","arctic","tropic","toyland"),default="temperate")
    parser.add_argument("--timeout",type=int,default=180)
    parser.add_argument("--replace-statue-ground",action="store_true",help="Test-only partial original graphics replacement; body and all gameplay properties stay original")
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build/("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file(): parser.error(f"Missing executable: {executable}")
    if output.exists(): parser.error("Use a new output directory to retain earlier fixture failures")
    graphics = json.loads((Path(__file__).resolve().parents[2]/"opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures")/"objects",output/"ai/object-fixture")
    (output/"scripts").mkdir()
    newgrf_setting = ""
    if args.replace_statue_ground:
        (output/"newgrf").mkdir()
        (output/"newgrf/partial-object-ground-fixture.grf").write_bytes(statue_ground_replacement())
        newgrf_setting = "[newgrf]\npartial-object-ground-fixture.grf =\n"
    (output/"openttd.cfg").write_text(f"""[misc]
language = english.lng
[gui]
autosave_interval = 0
[game_creation]
map_x = 7
map_y = 7
starting_year = 1950
generation_seed = 314159
landscape = {args.climate}
land_generator = 1
custom_sea_level = 12
custom_town_number = 4
amount_of_rivers = 0
[difficulty]
terrain_type = 0
quantity_sea_lakes = 4
number_towns = 4
industry_density = 0
max_loan = 50000000
town_council_tolerance = 0
vehicle_breakdowns = 0
[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
{newgrf_setting}
""")
    (output/"scripts/game_start.scr").write_text('unpause\nstart_ai "OpenTT3D Original Object Fixture"\n')
    (output/"scripts/save_fixture.scr").write_text("pause\nsave object-fixture\n")
    (output/"scripts/save_failed_fixture.scr").write_text("pause\nsave failed-fixture\n")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1",0))
        port = probe.getsockname()[1]
    command = [str(executable),"-D",f"127.0.0.1:{port}","-c",str(output/"openttd.cfg"),"-x","-X",
               "-s","null","-m","null","-I",graphics["name"],"-S","NoSound","-M","NoMusic",
               "-d","script=4,console=1","-G","314159","-t","1950","-g"]
    result = output/"save/object-fixture.sav"
    with (output/"run.log").open("w") as log:
        process = subprocess.Popen(command,cwd=build,env=dict(os.environ,OPENTT3D_RENDERER="0",OPENTT3D_BACKGROUND="1"),
                                   stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
        try:
            deadline = time.monotonic()+args.timeout
            while time.monotonic() < deadline:
                text = (output/"run.log").read_text()
                if process.poll() is not None or "OBJECT_FIXTURE_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Original object fixture failed; inspect {output/'run.log'}")
                ready = re.search(r"OBJECT_FIXTURE_READY (\{[^\n]+\})",text)
                if ready:
                    manifest = json.loads(ready[1])
                    manifest.update(climate=args.climate,source="unmodified public NoAI HQ/town-action/owned-land commands",
                                    headquarters_size="unchanged original company-score selector; not forced",
                                    owned_land="flat and naturally sloped sites through public AIObjectType.BuildObject(3,0,tile)",
                                     final_visual_approvals=0)
                    if args.replace_statue_ground:
                        manifest["partial_source_replacement"] = {"sprite":1420,"role":"original statue concrete ground only",
                            "body":"original and unchanged","gameplay_properties_changed":False,
                            "grf_sha256":hashlib.sha256((output/"newgrf/partial-object-ground-fixture.grf").read_bytes()).hexdigest()}
                    process.stdin.write("exec scripts/save_fixture.scr\n")
                    process.stdin.flush()
                    break
                time.sleep(0.25)
            else:
                raise TimeoutError(f"Original object fixture timed out; inspect {output/'run.log'}")
            deadline = min(deadline,time.monotonic()+15)
            while time.monotonic() < deadline:
                text = (output/"run.log").read_text()
                if "Saving map failed" in text or process.poll() is not None:
                    raise RuntimeError("Original object fixture exited or failed to save")
                if result.is_file() and result.stat().st_size > 100 and "Map successfully saved" in text: break
                time.sleep(0.25)
            else:
                raise TimeoutError("Original object fixture save did not finish")
            (output/"fixture.json").write_text(json.dumps(manifest,indent=2)+"\n")
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.wait(timeout=15)
        except (RuntimeError,TimeoutError):
            if process.poll() is None:
                process.stdin.write("exec scripts/save_failed_fixture.scr\n")
                process.stdin.flush()
                until = time.monotonic()+15
                while time.monotonic() < until and process.poll() is None:
                    if (output/"save/failed-fixture.sav").is_file() and "Map successfully saved" in (output/"run.log").read_text(): break
                    time.sleep(0.25)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print(json.dumps({"savegame":str(result),"fixture":manifest}))


if __name__ == "__main__":
    main()

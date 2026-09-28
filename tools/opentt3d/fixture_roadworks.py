#!/usr/bin/env python3
"""Fund ordinary town roadworks through NoAI, without constructing effect vehicles."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--climate", choices=("temperate","arctic","tropic","toyland"), default="temperate")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    build, output = args.build_dir.resolve(), args.output.resolve()
    executable = build / ("opentt3d.exe" if os.name == "nt" else "opentt3d")
    if not executable.is_file() or output.exists():
        parser.error("Use a built executable and a new output directory")
    root = Path(__file__).resolve().parents[2]
    graphics = json.loads((root / "opentt3d/upstream.json").read_text())["graphics"]
    shutil.copytree(Path(__file__).with_name("fixtures") / "roadworks", output / "ai/roadworks")
    (output / "scripts").mkdir()
    (output / "scripts/game_start.scr").write_text('unpause\nstart_ai "OpenTT3D Roadworks"\n')
    (output / "scripts/save_fixture.scr").write_text("pause\nsave roadworks\n")
    (output / "openttd.cfg").write_text(f"""[misc]
language = english.lng
[gui]
autosave_interval = 0
[game_creation]
map_x = 7
map_y = 7
starting_year = 2050
generation_seed = 314159
landscape = {args.climate}
land_generator = 1
custom_sea_level = 1
custom_town_number = 1
amount_of_rivers = 0
[difficulty]
terrain_type = 0
quantity_sea_lakes = 4
number_towns = 4
industry_density = 0
max_loan = 50000000
town_council_tolerance = 0
[ai]
ai_in_multiplayer = true
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
""")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1",0))
        port = probe.getsockname()[1]
    command = [str(executable),"-D",f"127.0.0.1:{port}","-c",str(output / "openttd.cfg"),"-x","-X",
               "-s","null","-m","null","-I",graphics["name"],"-S","NoSound","-M","NoMusic",
               "-d","script=4,console=1","-G","314159","-t","2050","-g"]
    with (output / "run.log").open("x") as log:
        process = subprocess.Popen(command,cwd=build,env=dict(os.environ,OPENTT3D_RENDERER="0"),
                                   stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
        try:
            deadline = time.monotonic()+args.timeout
            manifest = None
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if process.poll() is not None or "ROADWORKS_FAILED" in text or "script died unexpectedly" in text:
                    raise RuntimeError(f"Roadworks fixture failed; inspect {output / 'run.log'}")
                ready = re.search(r"ROADWORKS_READY (\{[^\n]+\})",text)
                if ready:
                    manifest = json.loads(ready[1])
                    process.stdin.write("exec scripts/save_fixture.scr\n"); process.stdin.flush()
                    break
                time.sleep(0.2)
            if manifest is None:
                raise TimeoutError("Ordinary roadworks funding timed out")
            save = output / "save/roadworks.sav"
            while time.monotonic() < deadline:
                text = (output / "run.log").read_text()
                if "Saving map failed" in text or process.poll() is not None:
                    raise RuntimeError("Roadworks save failed")
                if save.is_file() and save.stat().st_size > 100 and "Map successfully saved" in text:
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError("Roadworks save timed out")
            manifest.update(climate=args.climate,save="save/roadworks.sav",effect_state_modified=False)
            (output / "fixture.json").write_text(json.dumps(manifest,indent=2)+"\n")
            process.stdin.write("quit\n"); process.stdin.flush(); process.wait(timeout=15)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
    print(json.dumps(manifest,sort_keys=True))


if __name__ == "__main__":
    main()

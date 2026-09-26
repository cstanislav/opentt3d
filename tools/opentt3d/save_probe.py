#!/usr/bin/env python3
"""Load and re-save a fixture in an isolated, unmodified game executable."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from fetch_baseset import fetch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--savegame", type=Path, required=True)
    parser.add_argument("--baseset", type=Path, required=True)
    parser.add_argument("--ai-dir", type=Path, help="Stage fixture AI scripts to preserve their identity during the round trip")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    graphics = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())["graphics"]
    executable, savegame, output = args.executable.resolve(), args.savegame.resolve(), args.output.resolve()
    if output.exists():
        parser.error("Choose a new output directory")
    (output / "scripts").mkdir(parents=True)
    (output / "baseset").mkdir()
    resources = executable.parent.parent / "Resources"
    if resources.is_dir():
        shutil.copytree(resources / "baseset", output / "baseset", dirs_exist_ok=True)
        shutil.copytree(resources / "lang", output / "lang")
    fetch(output / "baseset", seed=args.baseset.resolve())
    if args.ai_dir:
        shutil.copytree(args.ai_dir, output / "ai")
    (output / "openttd.cfg").write_text("[misc]\nlanguage = english.lng\n[network]\nserver_advertise = false\n")
    (output / "scripts/game_start.scr").write_text("pause\nsave roundtrip\nquit\n")
    command = [str(executable), "-c", str(output / "openttd.cfg"), "-x", "-X", "-v", "null",
               "-s", "null", "-m", "null", "-I", graphics["name"], "-S", "NoSound", "-M", "NoMusic", "-g", str(savegame)]
    with (output / "run.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=executable.parent, timeout=45, check=True)
    result = output / "save/roundtrip.sav"
    if not result.is_file() or result.stat().st_size < 100:
        raise SystemExit(f"Game did not re-save the fixture; inspect {output / 'run.log'}")
    print(f"Loaded {savegame}\nRe-saved with {executable}\nResult: {result}")


if __name__ == "__main__":
    main()

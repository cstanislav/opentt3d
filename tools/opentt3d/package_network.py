#!/usr/bin/env python3
"""Verify that an extracted release can start its native dedicated network server.

This is deliberately a listener/startup check, not a multiplayer-client replay
test: it never advertises the server, never joins a remote game and never changes
the release bytes.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import time


def executable_for(package: Path) -> Path:
    if package.suffix == ".app":
        return package / "Contents/MacOS/opentt3d"
    if platform.system() == "Windows":
        return package / "opentt3d.exe"
    wrapper = package / "opentt3d.sh"
    return wrapper if wrapper.is_file() else package / "opentt3d"


def resources_for(package: Path) -> Path:
    return package / "Contents/Resources" if package.suffix == ".app" else package


def verify(package: Path, output: Path, timeout: int = 60) -> None:
    package, output = package.resolve(), output.resolve()
    executable = executable_for(package)
    resources = resources_for(package)
    title = resources / "baseset/opntitle.dat"
    if not executable.is_file():
        raise FileNotFoundError(f"Missing package executable: {executable}")
    if not title.is_file():
        raise FileNotFoundError(f"Missing packaged title world: {title}")
    output.mkdir(parents=True, exist_ok=False)
    home = output / "home"
    home.mkdir()
    shutil.copyfile(title, output / "input.sav")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    (output / "openttd.cfg").write_text(f"""[misc]
language = english.lng
[gui]
autosave_interval = 0
[network]
server_advertise = false
min_active_clients = 0
pause_on_join = false
""")
    command = [str(executable), "-D", f"127.0.0.1:{port}",
               "-c", str(output / "openttd.cfg"), "-x",
               *([] if package.suffix == ".app" else ["-X"]),
               "-s", "null", "-m", "null",
               "-I", "OpenGFX2 Classic", "-S", "NoSound", "-M", "NoMusic",
               "-g", str(output / "input.sav")]
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("OPENTT3D_") and key not in ("DYLD_LIBRARY_PATH", "LD_LIBRARY_PATH")}
    env["HOME"] = str(home)
    log_path = output / "run.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=output, env=env, stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + timeout
            listening = False
            while time.monotonic() < deadline:
                text = log_path.read_text(errors="replace")
                if process.poll() is not None:
                    raise RuntimeError(f"Packaged dedicated server exited ({process.returncode}): {log_path}")
                if f"Listening on 127.0.0.1:{port}" in text:
                    listening = True
                    break
                time.sleep(0.1)
            if not listening:
                raise TimeoutError(f"Packaged dedicated server did not listen: {log_path}")
            with socket.create_connection(("127.0.0.1", port), timeout=5):
                pass
            process.stdin.write("quit\n")
            process.stdin.flush()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
            if "Listening on 127.0.0.1:" not in log_path.read_text(errors="replace"):
                raise RuntimeError(f"Dedicated server lost its listener acknowledgement: {log_path}")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    result = {"native_listener": True, "port": port, "package": str(package),
              "executable": str(executable), "command": command}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Packaged native dedicated listener passed: {package}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    verify(args.package, args.output, args.timeout)

#!/usr/bin/env python3
"""Build and audit self-contained CPack releases, plus matching source/checksums."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

from fetch_baseset import fetch, verified

ROOT = Path(__file__).resolve().parents[2]
PIN = json.loads((ROOT / "opentt3d/upstream.json").read_text())


def run(*command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def extract_generated_tar(archive, destination):
    """Extract our own CPack/git archive on Debian 12's original Python 3.11."""
    # Extraction filters were backported after Debian's 3.11.2. Both callers
    # create the archive locally; no downloaded tar is extracted by this helper.
    with tarfile.open(archive) as source:
        source.extractall(destination, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))


def metadata(tag):
    if not re.fullmatch(r"opentt3d-[A-Za-z0-9][A-Za-z0-9._-]*", tag):
        raise ValueError("Release tags must start with opentt3d- and contain only letters, digits, dots, underscores and hyphens")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return {"tag": tag, "commit": commit, "upstream": PIN,
            "source_url": f"https://github.com/cstanislav/opentt3d/tree/{commit}"}


def prepare(build, tag):
    fetch(build / "baseset")
    info = build / "release-info"
    info.mkdir(exist_ok=True)
    (info / "build.json").write_text(json.dumps(metadata(tag), indent=2) + "\n")
    licenses = info / "licenses"
    licenses.mkdir(exist_ok=True)
    for path in build.glob("vcpkg_installed/*/share/*/copyright"):
        shutil.copyfile(path, licenses / f"vcpkg-{path.parent.name}.txt")
    if platform.system() == "Darwin":
        for formula in ("libpng", "lzo", "opusfile", "libogg", "opus"):
            prefix = Path(subprocess.check_output(["brew", "--prefix", formula], text=True).strip())
            for pattern in ("**/COPYING*", "**/LICENSE*", "**/AUTHORS*", "**/copyright*"):
                for path in prefix.glob(pattern):
                    if path.is_file():
                        destination = licenses / formula / path.relative_to(prefix)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(path, destination)
        for path in (build / "vulkan").rglob("LICENSE*"):
            if path.is_file():
                destination = licenses / "MoltenVK" / path.relative_to(build / "vulkan")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
    elif platform.system() == "Linux":
        # Debian copyright files preserve the complete dependency attribution and
        # source locations, including libraries discovered transitively by CPack.
        for path in Path("/usr/share/doc").glob("*/copyright"):
            if path.is_file():
                shutil.copyfile(path, licenses / f"debian-{path.parent.name}.txt")
        if Path("/usr/share/common-licenses").is_dir():
            shutil.copytree("/usr/share/common-licenses", licenses / "common-licenses", dirs_exist_ok=True)


def audit(package):
    package = Path(package).resolve()
    mac = package.suffix == ".app"
    resources = package / "Contents/Resources" if mac else package
    executable = package / "Contents/MacOS/opentt3d" if mac else package / ("opentt3d.exe" if (package / "opentt3d.exe").exists() else "opentt3d")
    required = [executable, resources / "lang/english.lng", resources / "baseset/opntitle.dat",
                resources / "baseset/opentt3d-voxels.json", resources / "PLAYING.md", resources / "COPYING.md",
                resources / "release-info/build.json"]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Incomplete release: {path}")
    graphics = resources / "baseset" / PIN["graphics"]["filename"]
    if not verified(graphics, PIN["graphics"]["sha256"]):
        raise RuntimeError("Package lacks the exact pinned OpenGFX2 Classic graphics")
    if list((resources / "baseset").glob("*.tar")) != [graphics]:
        raise RuntimeError("Package includes unpinned development graphics archives")
    for path in package.rglob("*"):
        if path.is_symlink() and (not path.exists() or not path.resolve().is_relative_to(package)):
            raise RuntimeError(f"Package depends on an external/broken symlink: {path}")
    if mac:
        run("codesign", "--verify", "--deep", "--strict", str(package))
        minimum = plistlib.loads((package / "Contents/Info.plist").read_bytes())["LSMinimumSystemVersion"]
        def version(value):
            return tuple((list(map(int, value.split("."))) + [0, 0])[:3])
        for path in [executable, *package.rglob("*.dylib")]:
            commands = subprocess.check_output(["otool", "-l", str(path)], text=True)
            current_command = ""
            for line in commands.splitlines():
                fields = line.split()
                if len(fields) != 2:
                    continue
                key, value = fields
                if key == "cmd":
                    current_command = value
                if (current_command, key) not in (("LC_BUILD_VERSION", "minos"), ("LC_VERSION_MIN_MACOSX", "version")):
                    continue
                required = value
                if version(required) > version(minimum):
                    raise RuntimeError(f"{path.name} requires macOS {required}, above the app's declared {minimum}")
            dependencies = subprocess.check_output(["otool", "-L", str(path)], text=True).splitlines()[1:]
            for line in dependencies:
                if not line.startswith("\t"):
                    continue  # Universal dylibs repeat an unindented header per architecture.
                name = line.strip().split(" (", 1)[0]
                if name.startswith(("/usr/lib/", "/System/Library/")):
                    continue
                base = executable.parent if name.startswith("@executable_path/") else path.parent
                if not name.startswith(("@executable_path/", "@loader_path/")):
                    raise RuntimeError(f"Unbundled dependency in {path}: {name}")
                resolved = (base / name.split("/", 1)[1]).resolve()
                if not resolved.is_file() or not resolved.is_relative_to(package):
                    raise RuntimeError(f"Missing or external package dependency in {path}: {name}")
    print(f"Package resources, graphics checksum and dependency paths passed: {package}")
    return executable


def package(build, output, tag, target):
    build, output = build.resolve(), output.resolve()
    prepare(build, tag)
    output.mkdir(parents=True, exist_ok=True)
    name = f"{tag}-{target}"
    staging = build / "release-packages"
    generator = "Bundle" if target.startswith("macos-") else "ZIP;NSIS" if target.startswith("windows-") else "TXZ"
    command = ["cpack", "-G", generator, "-B", str(staging), "-D", f"CPACK_PACKAGE_FILE_NAME={name}",
               "-D", f"CPACK_OUTPUT_FILE_PREFIX={staging}"]
    if target.startswith("macos-"):
        command += ["-D", "CPACK_BUNDLE_APPLE_CERT_APP=-", "-D", "CPACK_BUNDLE_APPLE_CODESIGN_PARAMETER=--deep -f"]
    run(*command, cwd=build)
    if target.startswith("macos-"):
        app, = staging.glob("_CPack_Packages/*/Bundle/*/OpenTT3D.app")
        audit(app)
        run("ditto", "-c", "-k", "--keepParent", str(app), str(staging / f"{name}.zip"))
    suffixes = (".dmg", ".zip") if target.startswith("macos-") else (".exe", ".zip") if target.startswith("windows-") else (".tar.xz",)
    for suffix in suffixes:
        artifact = staging / (name + suffix)
        if not artifact.is_file():
            raise RuntimeError(f"CPack did not produce the required download: {artifact}")
        shutil.copyfile(artifact, output / artifact.name)
    archive = output / (name + (".zip" if target.startswith(("macos-", "windows-")) else ".tar.xz"))
    # Verify the actual compressed download after extraction, not the build tree.
    with tempfile.TemporaryDirectory(prefix="opentt3d-package-") as temporary:
        temporary = Path(temporary)
        if target.startswith("macos-"):
            run("ditto", "-x", "-k", str(archive), str(temporary))
            extracted = temporary / "OpenTT3D.app"
        elif archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as source:
                source.extractall(temporary)
            extracted = temporary / name
        else:
            extract_generated_tar(archive, temporary)
            extracted = temporary / name
        audit(extracted)
        from package_smoke import verify
        checks = build / f"package-smoke-{name}"
        if target.startswith(("macos-", "linux-")):
            verify(extracted, checks / "default")
            verify(extracted, checks / "opengl", "cocoa-opengl" if target.startswith("macos-") else "sdl-opengl")
            if target.startswith("linux-"):
                verify(extracted, checks / "fallback", without_vulkan_device=True)
        elif target != "windows-arm64":
            verify(extracted, checks / "headless", headless=True)
        report = {**metadata(tag), "platform": target, "archive_verified": archive.name,
                  "launch_check": "cross-compiled; native execution pending" if target == "windows-arm64" else
                                  "extracted default 3D and OpenGL rendering/save" if not target.startswith("windows-") else
                                  "extracted native title-world load/save"}
        (output / f"{name}.json").write_text(json.dumps(report, indent=2) + "\n")


def source_archive(output, tag):
    info = metadata(tag)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="opentt3d-source-") as temporary:
        temporary = Path(temporary)
        root = temporary / tag
        archive = temporary / "source.tar"
        run("git", "archive", "--format=tar", "--output", str(archive), info["commit"], cwd=ROOT)
        extract_generated_tar(archive, root)
        external = root / "external"
        external.mkdir()
        graphics = PIN["graphics"]
        upstream = external / f"OpenGFX2-{graphics['commit']}.tar.gz"
        request = urllib.request.Request(f"https://codeload.github.com/OpenTTD/OpenGFX2/tar.gz/{graphics['commit']}",
                                         headers={"User-Agent": "OpenTT3D-release"})
        with urllib.request.urlopen(request, timeout=120) as response, upstream.open("wb") as destination:
            shutil.copyfileobj(response, destination)
        info["graphics_source_sha256"] = digest(upstream)
        (root / "release-source.json").write_text(json.dumps(info, indent=2) + "\n")
        with tarfile.open(output / f"{tag}-source.tar.xz", "w:xz") as destination:
            destination.add(root, arcname=tag)


def checksums(output):
    files = sorted(path for path in output.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    if not files:
        raise RuntimeError("No release files to checksum")
    (output / "SHA256SUMS").write_text("".join(f"{digest(path)}  {path.name}\n" for path in files))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("package", "source", "checksums"))
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag")
    parser.add_argument("--platform", choices=("macos-arm64", "macos-x86_64", "windows-x64", "windows-x86", "windows-arm64", "linux-x86_64"))
    args = parser.parse_args()
    if args.action != "checksums" and not args.tag:
        parser.error("--tag is required")
    if args.action == "package":
        if not args.build_dir or not args.platform:
            parser.error("Packaging requires --build-dir and --platform")
        package(args.build_dir, args.output, args.tag, args.platform)
    elif args.action == "source":
        source_archive(args.output, args.tag)
    else:
        checksums(args.output)

#!/usr/bin/env python3
"""Launch the native game with isolated data and capture its own framebuffer.

Uses upstream console scripts and screenshot support. No GUI automation,
screen-recording permission, external Python packages, or host installation.
"""

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import struct
import subprocess
import time
from fetch_baseset import fetch


def completed_png_size(path):
    """Wait for IEND: a giant screenshot may take much longer than one second."""
    try:
        with path.open("rb") as image:
            header = image.read(24)
            if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
                return None
            image.seek(-12, os.SEEK_END)
            if image.read(12) != b"\0\0\0\0IEND\xaeB\x60\x82":
                return None
            return struct.unpack(">II", header[16:24])
    except (FileNotFoundError, OSError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--renderer", choices=("classic", "3d"), default="3d")
    parser.add_argument("--backend", choices=("opengl", "vulkan"), default="opengl")
    parser.add_argument("--readback-presentation", action="store_true", help="Use the original CPU-composited OpenGL path for a controlled comparison")
    parser.add_argument("--vulkan-validation", action="store_true", help="Require Khronos core and synchronization validation")
    parser.add_argument("--rotation", type=int, choices=range(4), default=0)
    parser.add_argument("--orbit-drag", nargs=2, type=int, metavar=("DX", "DY"), help="Exercise clicked-point middle-drag yaw and tilt, then release")
    parser.add_argument("--year", type=int, default=1950)
    parser.add_argument("--map-bits", type=int, choices=range(7,11), default=7, help="New-world map width/height as a power of two")
    parser.add_argument("--town-count", type=int, help="Use the normal custom town count when generating a review world")
    parser.add_argument("--city-size", type=int, choices=range(1,11), help="New review world: make every town a city with this normal initial size multiplier")
    parser.add_argument("--climate", choices=("temperate", "arctic", "tropic", "toyland"))
    parser.add_argument("--savegame", type=Path)
    parser.add_argument("--ai-dir", type=Path, help="Stage a fixture's local AI scripts alongside the isolated save")
    parser.add_argument("--newgrf-dir", type=Path, help="Stage the NewGRF files required by a fixture save")
    parser.add_argument("--executable", type=Path, help="Override game executable, for official upstream interoperability checks")
    parser.add_argument("--graphics-from-config", choices=("OpenGFX2 Classic", "OpenGFX2 High Def"), help="Exercise saved base-set selection/migration without a command-line graphics override")
    parser.add_argument("--reference-model", action="store_true")
    parser.add_argument("--reference-vehicle", type=int, choices=range(256), help="Locate an actual visible vehicle with an authored voxel binding")
    parser.add_argument("--reference-vehicle-binding", type=int, choices=range(8), help="Require an exact climate/cargo binding with --reference-vehicle")
    parser.add_argument("--reference-cargo", choices=("empty", "full"), help="Require the located vehicle's real cargo count to be zero/full in a paused review")
    parser.add_argument("--reference-industry", nargs=2, type=int, metavar=("GRAPHICS", "STAGE"), help="Locate an actual voxel industry tile in its original construction state")
    parser.add_argument("--reference-industry-ground", nargs=2, type=int, metavar=("GRAPHICS", "STAGE"), help="Locate an actual voxel industry ground/stockpile layer in its original construction state")
    parser.add_argument("--reference-tree", nargs=2, type=int, metavar=("BASE_SPRITE", "STAGE"), help="Locate an actual projected or voxel tree in one of its seven original lifecycle stages")
    parser.add_argument("--reference-house-stage", type=int, choices=range(4), help="Find an actual voxel-bound house at this upstream construction stage")
    parser.add_argument("--reference-house-id", type=int, choices=range(110), help="Restrict --reference-house-stage to one house type")
    parser.add_argument("--reference-house-variant", type=int, choices=range(4), help="Select an actual source-art variant of the requested house/stage")
    parser.add_argument("--reference-bridge", action="store_true")
    parser.add_argument("--reference-fence", type=int, choices=range(7))
    parser.add_argument("--reference-foundation", choices=("any", "house", "voxel-house", "rail", "road", "station", "industry"), nargs="?", const="any", help="Find an actual sloped structure with an upstream foundation")
    parser.add_argument("--reference-tunnel", action="store_true")
    parser.add_argument("--reference-station", action="store_true")
    parser.add_argument("--reference-airport", action="store_true")
    parser.add_argument("--reference-airport-tile", type=int, choices=range(74), help="Select one original graphics type for --reference-airport")
    parser.add_argument("--reference-signal", action="store_true")
    parser.add_argument("--reference-catenary", action="store_true")
    parser.add_argument("--reference-depot", action="store_true")
    parser.add_argument("--reference-voxel-depot", type=int, choices=range(6), help="Locate and require actual voxel geometry for one original depot family")
    parser.add_argument("--reference-depot-direction", type=int, choices=range(4), help="Select one actual exit direction with --reference-voxel-depot")
    parser.add_argument("--reference-ship-depot", type=int, choices=range(2), help="Locate and require both voxel parts of one actual ship-depot axis")
    parser.add_argument("--reference-dock", type=int, choices=range(6), help="Locate and require one actual original dock section as voxels")
    parser.add_argument("--reference-buoy", action="store_true", help="Locate and require an actual original voxel buoy")
    parser.add_argument("--reference-crossing", action="store_true")
    parser.add_argument("--reference-road-stop", action="store_true")
    parser.add_argument("--reference-ground-detail", nargs=2, type=int, metavar=("KIND", "VARIANT"))
    parser.add_argument("--export-references", action="store_true")
    parser.add_argument("--gallery-house", type=int, nargs="+", help="Export one or more house/tree model turntables")
    parser.add_argument("--gallery-voxels", action="store_true", help="Export all authored voxel turntables, street and neighbour-context views")
    parser.add_argument("--gallery-voxel-prefix", help="Export only voxel models with this name prefix")
    parser.add_argument("--gallery-industry", type=int, choices=range(175))
    parser.add_argument("--gallery-vehicle", type=int, choices=range(256))
    parser.add_argument("--gallery-bridge", type=int, choices=range(13))
    parser.add_argument("--gallery-fence", type=int, choices=range(7), nargs="+")
    parser.add_argument("--fence-slope", type=int, choices=(*range(15),23,27,29,30,33,98,164,232,59,119,190,253), default=3, help="Vanilla slope, including the eight raised/steep half-tile encodings")
    parser.add_argument("--fence-layout", type=int, choices=range(16), help="Review one upstream railway fence layout; requires --gallery-fence 6")
    parser.add_argument("--gallery-foundation", nargs=2, type=int, action="append", metavar=("SLOPE", "FOUNDATION"))
    parser.add_argument("--gallery-tunnel", nargs=2, type=int, metavar=("KIND", "DIRECTION"))
    parser.add_argument("--gallery-rail", nargs=3, type=int, metavar=("TYPE", "TRACK_BITS", "SLOPE"))
    parser.add_argument("--gallery-station", nargs=2, type=int, metavar=("TYPE", "LAYOUT"))
    parser.add_argument("--gallery-ground-detail", nargs=3, action="append", type=int, metavar=("KIND", "VARIANT", "SLOPE"))
    parser.add_argument("--gallery-signal", nargs=3, type=int, metavar=("TYPE", "VARIANT", "STATE"))
    parser.add_argument("--gallery-catenary", nargs=2, type=int, metavar=("TRACK", "GRADE"))
    parser.add_argument("--gallery-depot", nargs=2, type=int, metavar=("KIND", "DIRECTION"))
    parser.add_argument("--gallery-crossing", nargs=3, type=int, metavar=("KIND", "AXIS", "BARRED"))
    parser.add_argument("--gallery-road-stop", nargs=2, type=int, metavar=("KIND", "LAYOUT"))
    parser.add_argument("--loaded-vehicle", action="store_true")
    parser.add_argument("--export-vehicles", action="store_true")
    parser.add_argument("--export-industries", action="store_true")
    parser.add_argument("--export-bridges", action="store_true")
    parser.add_argument("--export-terrain", action="store_true")
    parser.add_argument("--export-stations", action="store_true")
    parser.add_argument("--export-rail-details", action="store_true")
    parser.add_argument("--export-infrastructure", action="store_true")
    parser.add_argument("--verify-vehicles", action="store_true")
    parser.add_argument("--verify-industries", action="store_true")
    parser.add_argument("--verify-trees", action="store_true")
    parser.add_argument("--tree-verification-scope", choices=("full", "active"), default="full", help="Active scope verifies the selected tree representation; the complete renderer matrix separately retains all diagnostic voxel-tree coverage")
    parser.add_argument("--verify-bridges", action="store_true")
    parser.add_argument("--verify-fences", action="store_true")
    parser.add_argument("--verify-foundations", action="store_true")
    parser.add_argument("--verify-tunnels", action="store_true")
    parser.add_argument("--verify-live-tunnel", action="store_true")
    parser.add_argument("--verify-rails", action="store_true")
    parser.add_argument("--verify-stations", action="store_true")
    parser.add_argument("--verify-ground-details", action="store_true")
    parser.add_argument("--verify-ground-continuity", action="store_true", help="Require low-angle mixed terrain/voxel floors to cover their original footprint without sky gaps")
    parser.add_argument("--verify-rail-details", action="store_true")
    parser.add_argument("--verify-depots", action="store_true")
    parser.add_argument("--verify-depot-traversal", type=int, metavar="VEHICLE", help="Observe an actual road vehicle or ship before, inside and after a captured voxel depot")
    parser.add_argument("--verify-crossings", action="store_true")
    parser.add_argument("--verify-road-stops", action="store_true")
    parser.add_argument("--verify-crossing-transitions", action="store_true", help="Require both actual open/barred states during a running viewport benchmark")
    parser.add_argument("--verify-airport-animation", nargs="+", type=int, choices=range(74), metavar="GFX", help="Observe every actual upstream animation frame of the selected voxel airport tiles")
    parser.add_argument("--verify-industry-animation", nargs="+", type=int, choices=range(175), metavar="GFX", help="Observe every distinct original sprite frame of the selected voxel industry animations")
    parser.add_argument("--verify-plastic-fountain", action="store_true", help="Observe all eight actual plastic-fountain ground/body pairs together on one unchanged industry tile")
    harvest_cycle = parser.add_mutually_exclusive_group()
    harvest_cycle.add_argument("--verify-forest-cycle", action="store_true", help="Observe one unchanged actual timber/cotton forest tile dispatch cargo and pass through its harvested and every original regrowth state")
    harvest_cycle.add_argument("--verify-harvest-cycle", type=int, choices=(16,129,135), metavar="GRAPHICS", help="Explicitly observe original timber16, cotton129 or battery135 on one unchanged harvested/regrowing tile")
    parser.add_argument("--verify-power-sparks", action="store_true", help="Observe all six actual voxel power-station spark children on one unchanged industry tile")
    parser.add_argument("--verify-toy-factory", action="store_true", help="Observe all 50 original toy-factory frames with ordered voxel children and genuine absences on one unchanged tile")
    parser.add_argument("--verify-house-lift", action="store_true", help="Observe at least eight actual positions of one moving voxel office lift")
    parser.add_argument("--verify-radio-beacons", action="store_true", help="Observe both original blinking palette entries on one emitted voxel radio tower")
    parser.add_argument("--verify-buoy-beacon", action="store_true", help="Observe original239/240 beacon and250..254 foam phases on one actually captured voxel buoy")
    parser.add_argument("--verify-voxel-water", type=int, choices=(8,10,11), help="Observe original palette cycling on one captured hotel pool, fountain or park pond")
    house_palette = parser.add_mutually_exclusive_group()
    house_palette.add_argument("--verify-stadium-palette", type=int, choices=(20,32), help="Observe all original crowd and applicable scoreboard palette phases on one actually captured voxel stadium")
    house_palette.add_argument("--verify-house-palette", type=int, choices=(20,31,32,39,104,105), help="Observe original crowd, marquee, scoreboard or Toyland shop palette phases on one actually captured voxel house")
    parser.add_argument("--verify-dock-palette", type=int, choices=(4,5), help="Observe original lamp/foam palette phases on one actually captured non-Toyland dock")
    parser.add_argument("--verify-industry-palette", nargs="+", type=int, choices=(*range(52,58),157,158,159), metavar="GFX", help="Observe seven original fire-palette phases on steel grounds52..57 or all five original bubble phases/materials on fizzy-drink bodies157..159")
    parser.add_argument("--verify-renderer", action="store_true")
    parser.add_argument("--renderer-verification-scope", choices=("full","scene"), default="full", help="Scene scope retains renderer/model checks and delegates complete vehicle pose matrices to separate --verify-voxel-poses runs")
    parser.add_argument("--verify-instance-order", action="store_true", help="Check exact mesh-allocation, child-layer and mixed-opacity colour/picking precedence")
    parser.add_argument("--verify-clipping", action="store_true", help="Compare clipped perspective triangles with independent ray-tested coverage, depth, colour and picking")
    parser.add_argument("--verify-world-atlas", action="store_true", help="Compare complete current-world RGBA/picking before and after atlas repacking")
    parser.add_argument("--verify-voxel-meshes", metavar="PREFIX", help="Run exact voxel cell/CPU/palette/picking checks for a named model family, including its house bindings and joins")
    parser.add_argument("--verify-voxel-poses", type=int, nargs="+", choices=range(256), help="Run the exact company/crash/cargo/heading matrix for selected voxel vehicle engines")
    parser.add_argument("--verify-voxel-vehicle", type=int, choices=range(256), help="Require an actual captured voxel vehicle of the selected vanilla engine type")
    parser.add_argument("--verify-voxel-cargo", type=int, choices=range(256), help="Observe one actual voxel vehicle at both zero cargo and full capacity with the corresponding original bindings")
    parser.add_argument("--verify-helicopter-rotor", type=int, choices=(253,254,255), help="Observe all four original rotor states on an actual moving voxel helicopter")
    parser.add_argument("--verify-aircraft-contact", type=int, choices=range(215,256), help="Observe authored wheels/skids on an actual stopped aircraft meeting the airport ground surface")
    parser.add_argument("--verify-train-collectors", type=int, choices=range(23,27), help="Observe original electric roof collectors following surface, portal and tunnel wires")
    parser.add_argument("--verify-train-support", type=int, choices=range(116), help="Observe one original train on station, flat, ascending, descending, bridge and tunnel running surfaces")
    parser.add_argument("--verify-train-corners", action="store_true", help="Require --verify-train-support to also observe all four actual original corner tracks")
    parser.add_argument("--verify-tile-picking", action="store_true")
    parser.add_argument("--verify-native-input", action="store_true", help="Exercise Cocoa focus, pointer capture and fullscreen recovery")
    parser.add_argument("--macos-bundle", action="store_true", help="Launch through macOS LaunchServices using a linked development app bundle")
    parser.add_argument("--background", action="store_true", help="macOS: render into a hidden Cocoa window without activating the app")
    parser.add_argument("--benchmark-frames", type=int, default=0)
    parser.add_argument("--zoom", type=int, default=1, choices=range(-6, 6))
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--resolution", nargs=2, type=int, default=(1280,800), metavar=("WIDTH", "HEIGHT"), help="Window dimensions; smaller scenes improve software-rendered live-state sampling")
    parser.add_argument("--center", nargs=2, type=int, default=(64, 64), metavar=("TILE_X", "TILE_Y"))
    parser.add_argument("--infinite-water", action="store_true", help="Generate a new world with infinite water borders")
    parser.add_argument("--first-person", metavar="VEHICLE_ID", help="Exercise the vehicle window's Cab button; use 'auto' for the first visible primary vehicle")
    parser.add_argument("--running", action="store_true", help="Keep simulation running while measuring or following a vehicle")
    parser.add_argument("--menu", action="store_true", help="Capture the branded main menu instead of loading/generating a game")
    parser.add_argument("--screenshot-size", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"), help="Exercise tiled large-image rendering at the requested size")
    parser.add_argument("--blitter", choices=("32bpp-optimized", "40bpp-anim"), default="32bpp-optimized")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--memory-limit-mib", type=int, help="Sample game RSS/footprint and abort above this MiB limit (macOS/Linux); retain memory.jsonl")
    parser.add_argument("--keep-open", action="store_true")
    parser.add_argument("--brief", action="store_true", help="Print a short result; retain the complete artifact reports")
    args = parser.parse_args()
    if not (640 <= args.resolution[0] <= 8192 and 480 <= args.resolution[1] <= 8192):
        parser.error("--resolution requires width 640…8192 and height 480…8192")
    if args.background and (platform.system() != "Darwin" or args.verify_native_input or args.fullscreen):
        parser.error("--background requires macOS windowed rendering without --verify-native-input")
    if args.memory_limit_mib is not None and (args.memory_limit_mib <= 0 or args.keep_open):
        parser.error("--memory-limit-mib requires a positive limit and cannot be used with --keep-open")
    if args.verify_voxel_meshes is not None and not re.fullmatch(r"[a-z][a-z0-9_]{0,95}",args.verify_voxel_meshes):
        parser.error("--verify-voxel-meshes requires a nonempty authored-model name prefix")
    if args.macos_bundle and (platform.system() != "Darwin" or args.executable):
        parser.error("--macos-bundle requires the native macOS development build")
    if args.vulkan_validation and args.backend != "vulkan":
        parser.error("--vulkan-validation requires --backend vulkan")
    if args.readback_presentation and (args.backend != "opengl" or args.renderer != "3d" or args.executable or args.macos_bundle):
        parser.error("--readback-presentation requires the direct-launch OpenGL 3D build")
    if args.verify_crossing_transitions and (not args.running or not args.benchmark_frames):
        parser.error("Crossing transitions require --running and --benchmark-frames")
    if args.verify_airport_animation and (not args.running or not args.benchmark_frames):
        parser.error("Airport animation checks require --running and --benchmark-frames")
    if args.verify_industry_animation and (not args.running or not args.benchmark_frames):
        parser.error("Industry animation checks require --running and --benchmark-frames")
    if (args.verify_forest_cycle or args.verify_harvest_cycle is not None) and (not args.running or not args.benchmark_frames):
        parser.error("Forest production/regrowth requires --running and --benchmark-frames")
    if args.verify_power_sparks and (not args.running or not args.benchmark_frames):
        parser.error("Power-station spark checks require --running and --benchmark-frames")
    if args.verify_toy_factory and (not args.running or not args.benchmark_frames):
        parser.error("Toy-factory child checks require --running and --benchmark-frames")
    if args.verify_voxel_cargo is not None and (not args.running or not args.benchmark_frames):
        parser.error("Vehicle cargo checks require --running and --benchmark-frames")
    if args.reference_cargo and (args.reference_vehicle is None or args.running):
        parser.error("--reference-cargo requires --reference-vehicle and a paused review")
    if args.reference_vehicle_binding is not None and args.reference_vehicle is None:
        parser.error("--reference-vehicle-binding requires --reference-vehicle")
    if args.reference_depot_direction is not None and args.reference_voxel_depot is None:
        parser.error("--reference-depot-direction requires --reference-voxel-depot")
    if args.verify_depot_traversal is not None and (not 0 <= args.verify_depot_traversal < 0xffffffff or not args.running or not args.benchmark_frames):
        parser.error("Depot traversal needs a valid vehicle ID, --running and --benchmark-frames")
    if args.verify_house_lift and (not args.running or not args.benchmark_frames):
        parser.error("House lift checks require --running and --benchmark-frames")
    if args.verify_helicopter_rotor is not None and (not args.running or not args.benchmark_frames):
        parser.error("Helicopter rotor checks require --running and --benchmark-frames")
    if (args.verify_train_support is not None or args.verify_train_collectors is not None) and (not args.running or not args.benchmark_frames):
        parser.error("Train support/collector checks require --running and --benchmark-frames")
    if args.verify_train_corners and args.verify_train_support is None:
        parser.error("--verify-train-corners requires --verify-train-support")
    if args.verify_radio_beacons and (not args.running or not args.benchmark_frames):
        parser.error("Radio beacon checks require --running and --benchmark-frames")
    if args.verify_buoy_beacon and (not args.running or not args.benchmark_frames):
        parser.error("Buoy beacon checks require --running and --benchmark-frames")
    if args.verify_voxel_water is not None and (not args.running or not args.benchmark_frames):
        parser.error("Voxel water palette checks require --running and --benchmark-frames")
    if args.verify_stadium_palette is not None and (not args.running or not args.benchmark_frames):
        parser.error("Stadium palette checks require --running and --benchmark-frames")
    if args.verify_house_palette is not None and (not args.running or not args.benchmark_frames):
        parser.error("House palette checks require --running and --benchmark-frames")
    if args.verify_dock_palette is not None and (not args.running or not args.benchmark_frames):
        parser.error("Dock palette checks require --running and --benchmark-frames")
    if args.verify_industry_palette and (not args.running or not args.benchmark_frames):
        parser.error("Industry palette checks require --running and --benchmark-frames")
    if args.reference_airport_tile is not None and not args.reference_airport:
        parser.error("--reference-airport-tile requires --reference-airport")
    if args.reference_tree and (args.reference_tree[0] not in range(1576, 2010, 7) or args.reference_tree[1] not in range(7)):
        parser.error("--reference-tree requires an original seven-sprite family base and a stage in0..6")
    if args.reference_industry and (args.reference_industry[0] not in range(175) or args.reference_industry[1] not in range(4)):
        parser.error("--reference-industry requires original graphics0..174 and construction stage0..3")
    if args.reference_industry_ground and (args.reference_industry_ground[0] not in range(175) or args.reference_industry_ground[1] not in range(4)):
        parser.error("--reference-industry-ground requires original graphics0..174 and construction stage0..3")
    if args.screenshot_size and min(args.screenshot_size) <= 0:
        parser.error("Screenshot dimensions must be positive")
    if not 0 <= args.benchmark_frames <= 36000:
        parser.error("Benchmark frame count must be between 0 and 36000")
    if args.infinite_water and args.savegame:
        parser.error("--infinite-water configures a newly generated world, not a loaded save")
    if args.climate and args.savegame:
        parser.error("--climate configures a newly generated world, not a loaded save")
    if args.town_count is not None and (args.savegame or not 1 <= args.town_count <= 256):
        parser.error("--town-count needs a new world and a count between 1 and 256")
    if args.city_size is not None and args.savegame:
        parser.error("--city-size configures a newly generated world")
    if args.reference_house_id is not None and args.reference_house_stage is None:
        parser.error("--reference-house-id requires --reference-house-stage")
    if args.reference_house_variant is not None and (args.reference_house_id is None or args.reference_house_stage is None):
        parser.error("--reference-house-variant requires a house ID and construction stage")
    if args.fence_layout is not None and args.gallery_fence != [6]:
        parser.error("--fence-layout requires --gallery-fence 6")
    if args.fence_slope >= 32 and args.fence_layout is None:
        parser.error("Half-tile fence galleries require an explicit railway --fence-layout")
    if args.renderer_verification_scope != "full" and not args.verify_renderer:
        parser.error("--renderer-verification-scope requires --verify-renderer")
    if args.menu and (args.savegame or args.first_person or args.infinite_water or args.verify_renderer):
        parser.error("Menu capture cannot be combined with loaded-world options")
    if args.screenshot_size and (args.benchmark_frames or args.fullscreen):
        parser.error("Use a separate run for large world screenshots and viewport benchmarks")
    if args.renderer == "classic" and args.benchmark_frames:
        parser.error("Renderer benchmarking requires the 3D build")
    # A generated world's start script can run before its progress window closes.
    # The capture benchmark's normal 30 warm-up frames let the first viewport/UI
    # finish presenting, while the ordinary paused-world setting remains in force.
    warm_first_capture = args.renderer == "3d" and (args.fullscreen or (not args.menu and not args.savegame and not args.screenshot_size))
    benchmark_frames = args.benchmark_frames or (1 if warm_first_capture else 0)
    build = args.build_dir.resolve()
    graphics = json.loads((Path(__file__).resolve().parents[2] / "opentt3d/upstream.json").read_text())["graphics"]
    output = args.output.resolve()
    executable = args.executable.resolve() if args.executable else build / ("opentt3d.exe" if platform.system() == "Windows" else "opentt3d")
    if not executable.is_file():
        parser.error(f"Missing executable: {executable}")
    if args.savegame and not args.savegame.is_file():
        parser.error(f"Missing savegame: {args.savegame}")
    if args.ai_dir and not args.ai_dir.is_dir():
        parser.error(f"Missing AI directory: {args.ai_dir}")
    if args.newgrf_dir and not args.newgrf_dir.is_dir():
        parser.error(f"Missing NewGRF directory: {args.newgrf_dir}")
    if output.exists():
        parser.error("Use a new output directory to avoid confusing stale screenshots with a successful run")
    output.mkdir(parents=True)
    scripts = output / "scripts"
    scripts.mkdir()
    if args.ai_dir:
        shutil.copytree(args.ai_dir, output / "ai")
    if args.newgrf_dir:
        shutil.copytree(args.newgrf_dir, output / "newgrf")
    if args.executable:
        # Stock binaries have their own bundled fonts/languages. Supply only the
        # pinned OpenGFX pack via this isolated test's data directory.
        (output / "baseset").mkdir()
        resources = executable.parent.parent / "Resources"
        if resources.is_dir():
            shutil.copytree(resources / "baseset", output / "baseset", dirs_exist_ok=True)
            shutil.copytree(resources / "lang", output / "lang")
        fetch(output / "baseset", seed=build / "baseset" / graphics["filename"])
    driver = ({"Darwin": "cocoa-vulkan"}.get(platform.system(), "sdl-vulkan") if args.backend == "vulkan" else
              {"Darwin": "cocoa-opengl", "Windows": "win32-opengl"}.get(platform.system(), "sdl-opengl"))
    (output / "openttd.cfg").write_text(f"""[misc]
language = english.lng
display_opt = SHOW_TOWN_NAMES|SHOW_STATION_NAMES|SHOW_SIGNS|FULL_ANIMATION|FULL_DETAIL|WAYPOINTS
fullscreen = false
resolution = {args.resolution[0]},{args.resolution[1]}
screenshot_format = png

[gui]
autosave_interval = 0
show_finances = false
refresh_rate = 60

[game_creation]
map_x = {args.map_bits}
map_y = {args.map_bits}
starting_year = 1950
generation_seed = 314159

[network]
server_advertise = false
""")
    if args.fullscreen:
        config = output / "openttd.cfg"
        config.write_text(config.read_text().replace("fullscreen = false", "fullscreen = true"))
    if args.town_count is not None:
        config = output / "openttd.cfg"
        config.write_text(config.read_text().replace("[game_creation]", f"[game_creation]\ncustom_town_number = {args.town_count}") + "\n[difficulty]\nnumber_towns = 4\n")
    if args.city_size is not None:
        config = output / "openttd.cfg"
        config.write_text(config.read_text() + f"\n[economy]\nlarger_towns = 1\ninitial_city_size = {args.city_size}\n")
    if args.climate:
        config = output / "openttd.cfg"
        config.write_text(config.read_text().replace("[game_creation]", f"[game_creation]\nlandscape = {args.climate}"))
    if args.infinite_water:
        config = output / "openttd.cfg"
        config.write_text(config.read_text() + "\n[construction]\nfreeform_edges = false\n")
    if args.graphics_from_config:
        config = output / "openttd.cfg"
        config.write_text(config.read_text() + f"\n[graphicsset]\nname = {args.graphics_from_config}\n")
    commands = [] if args.menu else ["unpause" if args.running else "pause", f"scrollto instant {args.center[0]} {args.center[1]}"]
    if args.renderer == "3d":
        commands.append("renderer3d on")
        commands.extend(["renderer3d right"] * args.rotation)
    if args.reference_model:
        commands.append("renderer3d locate")
    if args.reference_house_stage is not None:
        commands.append(f"renderer3d house-stage-locate {args.reference_house_stage}" + (f" {args.reference_house_id}" if args.reference_house_id is not None else "") + (f" {args.reference_house_variant}" if args.reference_house_variant is not None else ""))
    if args.reference_tree:
        commands.append(f"renderer3d tree-locate {args.reference_tree[0]} {args.reference_tree[1]}")
    if args.reference_vehicle is not None:
        commands.append(f"renderer3d vehicle-locate {args.reference_vehicle}")
    if args.reference_industry:
        commands.append(f"renderer3d industry-locate {args.reference_industry[0]} {args.reference_industry[1]}")
    if args.reference_industry_ground:
        commands.append(f"renderer3d industry-ground-locate {args.reference_industry_ground[0]} {args.reference_industry_ground[1]}")
    if args.reference_bridge:
        commands.append("renderer3d bridge-locate")
    if args.reference_fence is not None:
        commands.append(f"renderer3d fence-locate {args.reference_fence}")
    if args.reference_foundation:
        commands.append(f"renderer3d foundation-locate {args.reference_foundation}")
    if args.reference_tunnel:
        commands.append("renderer3d tunnel-locate")
    if args.reference_station:
        commands.append("renderer3d station-locate")
    if args.reference_airport:
        commands.append("renderer3d airport-locate" + (f" {args.reference_airport_tile}" if args.reference_airport_tile is not None else ""))
    if args.reference_signal:
        commands.append("renderer3d signal-locate")
    if args.reference_catenary:
        commands.append("renderer3d catenary-locate")
    if args.reference_depot:
        commands.append("renderer3d depot-locate")
    if args.reference_voxel_depot is not None:
        direction = f" {args.reference_depot_direction}" if args.reference_depot_direction is not None else ""
        commands.append(f"renderer3d voxel-depot-locate {args.reference_voxel_depot}{direction}")
    if args.reference_crossing:
        commands.append("renderer3d crossing-locate")
    if args.reference_road_stop:
        commands.append("renderer3d road-stop-locate")
    if args.reference_ground_detail:
        commands.append("renderer3d ground-detail-locate " + " ".join(map(str, args.reference_ground_detail)))
    if args.reference_ship_depot is not None:
        commands.append(f"renderer3d ship-depot-locate {args.reference_ship_depot}")
    if args.reference_dock is not None:
        commands.append(f"renderer3d dock-locate {args.reference_dock}")
    if args.reference_buoy:
        commands.append("renderer3d buoy-locate")
    if not args.menu:
        commands.append(f"renderer3d zoom {args.zoom}" if args.renderer == "3d" else f"zoomto {max(0, args.zoom)}")
    if args.export_references:
        commands.append("renderer3d references")
    if args.gallery_house is not None:
        commands.extend(f"renderer3d gallery {identifier}" for identifier in args.gallery_house)
    if args.gallery_voxels or args.gallery_voxel_prefix:
        if args.gallery_voxel_prefix and not re.fullmatch(r"[a-z0-9_]+", args.gallery_voxel_prefix):
            parser.error("Voxel review prefixes use lowercase letters, digits and underscores")
        commands.append("renderer3d voxel-gallery" + (" " + args.gallery_voxel_prefix if args.gallery_voxel_prefix else ""))
    if args.gallery_industry is not None:
        commands.append(f"renderer3d industry-gallery {args.gallery_industry}")
    if args.export_vehicles:
        commands.append("renderer3d vehicle-references")
    if args.export_industries:
        commands.append("renderer3d industry-references")
    if args.export_bridges:
        commands.append("renderer3d bridge-references")
    if args.export_terrain:
        commands.append("renderer3d terrain-references")
    if args.export_stations:
        commands.append("renderer3d station-references")
    if args.export_rail_details:
        commands.append("renderer3d rail-detail-references")
    if args.export_infrastructure:
        commands.append("renderer3d infrastructure-references")
    if args.verify_vehicles:
        commands.append("renderer3d verify-vehicles")
    if args.verify_industries:
        commands.append("renderer3d verify-industries")
    if args.verify_trees:
        commands.append("renderer3d verify-active-trees" if args.tree_verification_scope == "active" else "renderer3d verify-trees")
    if args.verify_bridges:
        commands.append("renderer3d verify-bridges")
    if args.gallery_bridge is not None:
        commands.append(f"renderer3d bridge-gallery {args.gallery_bridge}")
    if args.gallery_fence is not None:
        layout = f" {args.fence_layout}" if args.fence_layout is not None else ""
        commands.extend(f"renderer3d fence-gallery {style} {args.fence_slope}{layout}" for style in args.gallery_fence)
    if args.verify_fences:
        commands.append("renderer3d verify-fences")
    if args.gallery_foundation:
        commands.extend(f"renderer3d foundation-gallery {slope} {foundation}" for slope,foundation in args.gallery_foundation)
    if args.verify_foundations:
        commands.append("renderer3d verify-foundations")
    if args.gallery_tunnel:
        commands.append(f"renderer3d tunnel-gallery {args.gallery_tunnel[0]} {args.gallery_tunnel[1]}")
    if args.verify_tunnels:
        commands.append("renderer3d verify-tunnels")
    if args.verify_live_tunnel:
        commands.append("renderer3d verify-live-tunnel")
    if args.gallery_rail:
        commands.append("renderer3d rail-gallery " + " ".join(map(str, args.gallery_rail)))
    if args.verify_rails:
        commands.append("renderer3d verify-rails")
    if args.gallery_station:
        commands.append("renderer3d station-gallery " + " ".join(map(str, args.gallery_station)))
    if args.verify_stations:
        commands.append("renderer3d verify-stations")
    if args.gallery_ground_detail:
        commands.extend("renderer3d ground-detail-gallery " + " ".join(map(str, view)) for view in args.gallery_ground_detail)
    if args.verify_ground_details:
        commands.append("renderer3d verify-ground-details")
    if args.verify_ground_continuity:
        commands.append("renderer3d verify-ground-continuity")
    if args.gallery_signal:
        commands.append("renderer3d signal-gallery " + " ".join(map(str, args.gallery_signal)))
    if args.gallery_catenary:
        commands.append("renderer3d catenary-gallery " + " ".join(map(str, args.gallery_catenary)))
    if args.verify_rail_details:
        commands.append("renderer3d verify-rail-details")
    if args.gallery_depot:
        commands.append("renderer3d depot-gallery " + " ".join(map(str, args.gallery_depot)))
    if args.verify_depots:
        commands.append("renderer3d verify-depots")
    if args.gallery_crossing:
        commands.append("renderer3d crossing-gallery " + " ".join(map(str, args.gallery_crossing)))
    if args.verify_crossings:
        commands.append("renderer3d verify-crossings")
    if args.gallery_road_stop:
        commands.append("renderer3d road-stop-gallery " + " ".join(map(str, args.gallery_road_stop)))
    if args.verify_road_stops:
        commands.append("renderer3d verify-road-stops")
    if args.gallery_vehicle is not None:
        commands.append(f"renderer3d vehicle-gallery {args.gallery_vehicle}" + (" loaded" if args.loaded_vehicle else ""))
    if args.verify_renderer:
        commands.append("renderer3d verify" if args.renderer_verification_scope == "full" else "renderer3d verify-scene")
    if args.verify_instance_order:
        commands.append("renderer3d verify-instance-order")
    if args.verify_clipping:
        commands.append("renderer3d verify-clipping")
    if args.verify_voxel_meshes is not None:
        commands.append(f"renderer3d verify-voxel-meshes {args.verify_voxel_meshes}")
    if args.verify_voxel_poses is not None:
        for engine in dict.fromkeys(args.verify_voxel_poses):
            commands.append(f"renderer3d verify-voxel-poses {engine}")
    if args.verify_helicopter_rotor is not None:
        commands.append(f"renderer3d verify-helicopter-rotor {args.verify_helicopter_rotor}")
    if args.verify_aircraft_contact is not None:
        commands.append(f"renderer3d verify-aircraft-contact {args.verify_aircraft_contact}")
    if args.verify_train_collectors is not None:
        commands.append(f"renderer3d verify-train-collectors {args.verify_train_collectors}")
    if args.verify_train_support is not None:
        commands.append(f"renderer3d verify-train-support {args.verify_train_support}" + (" corners" if args.verify_train_corners else ""))
    if args.verify_tile_picking:
        commands.append("renderer3d verify-tile-picking")
    if args.verify_world_atlas:
        commands.append("renderer3d verify-world-atlas")
    if args.verify_native_input:
        commands.append("renderer3d verify-input")
    if args.verify_airport_animation:
        commands.append("renderer3d verify-airport-animation " + " ".join(map(str,args.verify_airport_animation)))
    if args.verify_industry_animation:
        commands.append("renderer3d verify-industry-animation " + " ".join(map(str,args.verify_industry_animation)))
    if args.verify_plastic_fountain:
        commands.append("renderer3d verify-plastic-fountain")
    if args.verify_forest_cycle:
        commands.append("renderer3d verify-forest-cycle")
    if args.verify_harvest_cycle is not None:
        commands.append(f"renderer3d verify-forest-cycle {args.verify_harvest_cycle}")
    if args.verify_power_sparks:
        commands.append("renderer3d verify-power-sparks")
    if args.verify_toy_factory:
        commands.append("renderer3d verify-toy-factory")
    if args.verify_voxel_cargo is not None:
        commands.append(f"renderer3d verify-vehicle-cargo {args.verify_voxel_cargo}")
    if args.verify_depot_traversal is not None:
        commands.append(f"renderer3d verify-depot-traversal {args.verify_depot_traversal}")
    if args.verify_house_lift:
        commands.append("renderer3d verify-house-lift")
    if args.verify_radio_beacons:
        commands.append("renderer3d verify-radio-beacons")
    if args.verify_buoy_beacon:
        commands.append("renderer3d verify-buoy-beacon")
    if args.verify_voxel_water is not None:
        commands.append(f"renderer3d verify-voxel-water {args.verify_voxel_water}")
    if args.verify_stadium_palette is not None:
        commands.append(f"renderer3d verify-stadium-palette {args.verify_stadium_palette}")
    if args.verify_house_palette is not None:
        commands.append(f"renderer3d verify-house-palette {args.verify_house_palette}")
    if args.verify_dock_palette is not None:
        commands.append(f"renderer3d verify-dock-palette {args.verify_dock_palette}")
    for graphic in args.verify_industry_palette or []:
        commands.append(f"renderer3d verify-industry-palette {graphic}")
    # Both reference focus (notably joined stadiums) and camera diagnostics can
    # choose a temporary distance. Apply the requested review zoom afterwards;
    # the measured-zoom check below remains exact for palette-only runs too.
    if not args.menu and args.renderer == "3d":
        commands.append(f"renderer3d zoom {args.zoom}")
    if args.first_person:
        commands.append(f"renderer3d cab {args.first_person}")
    if args.orbit_drag:
        commands.append(f"renderer3d orbit {args.orbit_drag[0]} {args.orbit_drag[1]}")
    if benchmark_frames:
        commands.append(f"renderer3d benchmark {benchmark_frames} capture" + (" fullscreen" if args.fullscreen else ""))
    if not args.menu:
        commands.append("save smoke-state")
    gpu_presentation = args.backend == "vulkan" or (args.renderer == "3d" and not args.executable and not args.readback_presentation)
    if args.screenshot_size:
        commands.append(f"screenshot normal size {args.screenshot_size[0]} {args.screenshot_size[1]} smoke")
    elif not benchmark_frames:
        commands.append(f"screenshot {'presented' if gpu_presentation else 'viewport'} smoke")
    (scripts / ("autoexec.scr" if args.menu else "game_start.scr")).write_text("\n".join(commands) + "\n")
    command = [str(executable), "-c", str(output / "openttd.cfg"), "-x", "-X",
               "-v", driver, "-b", args.blitter, "-s", "null", "-m", "null",
               *([] if args.graphics_from_config else ["-I", graphics["name"]]), "-S", "NoSound", "-M", "NoMusic", "-r", f"{args.resolution[0]}x{args.resolution[1]}", "-d", "driver=2,console=1", "-G", "314159", "-t", str(args.year), "-g"]
    if args.menu:
        command.pop()  # No -g: use the original title-game/menu startup path.
    if args.savegame:
        savegame = args.savegame.resolve()
        if savegame.suffix.lower() not in (".sav", ".scn"):
            # The upstream -g parser selects a loader by suffix. opntitle.dat
            # contains a regular save, but otherwise silently opens the menu.
            savegame = output / "input.sav"
            shutil.copyfile(args.savegame, savegame)
        command.append(str(savegame))
    env = dict(os.environ, OPENTT3D_RENDERER="1" if args.renderer == "3d" else "0", OPENTT3D_ALLOW_SOFTWARE_GL="1")
    if args.background:
        env["OPENTT3D_BACKGROUND"] = "1"
    if args.backend == "opengl":
        env["OPENTT3D_GL_PRESENTATION"] = "0" if args.readback_presentation else "1"
    if args.vulkan_validation:
        env["OPENTT3D_VULKAN_VALIDATION"] = "1"
    if args.macos_bundle:
        from macos_bundle import assemble
        bundle = assemble(build)
        command = ["/usr/bin/open", "-n", "-W", *(["-g", "-j"] if args.background else []), str(bundle), "--stdout", str(output / "stdout.log"),
                    "--stderr", str(output / "run.log"), "--env", "OPENTT3D_RENDERER=" + env["OPENTT3D_RENDERER"],
                   *(["--env", "OPENTT3D_BACKGROUND=1"] if args.background else []),
                   "--args", *command[1:]]
    screenshot = output / "screenshot" / "smoke.png"
    native_pid = None
    memory = None
    if args.memory_limit_mib is not None:
        from process_memory import MemoryMonitor
        memory = MemoryMonitor(output, args.memory_limit_mib)
    with (output / "run.log").open("w") as log:
        process = subprocess.Popen(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + args.timeout
            rendering_errors = ("OpenTT3D: OpenGL rendering failed", "OpenTT3D: OpenGL presentation failed", "OpenTT3D: Vulkan rendering failed", "OpenTT3D: Vulkan validation error", "OpenTT3D: viewport rendering failed", "OpenTT3D: renderer verification failed", "OpenTT3D: background Cocoa window became visible or active", "Assertion failed", "terminating due to uncaught exception", "terminate called after throwing")
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Game exited with {process.returncode}; see {output / 'run.log'}")
                current_log = (output / "run.log").read_text()
                if "Crash encountered" in current_log:
                    raise RuntimeError(f"Game crashed; see {output / 'run.log'}")
                if any(error in current_log for error in rendering_errors):
                    raise RuntimeError(f"Rendering verification failed; see {output / 'run.log'}")
                if memory is not None:
                    if args.macos_bundle:
                        match = re.search(r"OpenTT3D: Cocoa process (\d+)", current_log)
                        if match:
                            native_pid = int(match[1])
                    if not args.macos_bundle or native_pid is not None:
                        try:
                            memory.sample(native_pid or process.pid)
                        except ProcessLookupError as error:
                            raise RuntimeError(f"Game exited during memory sampling (exit code {process.poll()}); see {output / 'run.log'}") from error
                image_size = completed_png_size(screenshot)
                if image_size and (not benchmark_frames or (output / "benchmark.json").is_file()):
                    break
                time.sleep(0.25)
            else:
                raise TimeoutError(f"No screenshot after {args.timeout}s; see {output / 'run.log'}")
            log.flush()
            text = (output / "run.log").read_text()
            if args.background and "background Cocoa window active=false, key=false, visible=false, policy=2" not in text:
                raise RuntimeError("The Cocoa app did not confirm hidden, nonactivating background rendering")
            if args.macos_bundle:
                match = re.search(r"OpenTT3D: Cocoa process (\d+)", text)
                if not match:
                    raise RuntimeError("The launched native application's PID was not recorded")
                native_pid = int(match[1])
            initialized = "OpenTT3D: Vulkan instanced renderer initialized" if args.backend == "vulkan" else "OpenTT3D: depth-tested mesh renderer initialized"
            if args.renderer == "3d" and initialized not in text:
                raise RuntimeError("3D backend did not initialize; a classic-renderer fallback is not a passing smoke test")
            if any(error in text for error in rendering_errors):
                raise RuntimeError("Rendering error; inspect run.log")
            if args.vulkan_validation and "Vulkan synchronization validation enabled" not in text:
                raise RuntimeError("Vulkan synchronization validation was not enabled")
            if args.verify_renderer and "GPU depth, object picking and transparency verification passed" not in text:
                raise RuntimeError("The GPU scene verification did not complete")
            if args.verify_renderer and "cached mip/padding variants match direct upstream pixels and framing" not in text:
                raise RuntimeError("Exact source-mip cache verification did not complete")
            if args.verify_renderer and f"model materials use {graphics['name']} at native resolution or coarser" not in text:
                raise RuntimeError("Model materials did not use the pinned native-resolution base set")
            if args.verify_renderer and "GPU multi-mesh storage, large uploads and reuse preserve colour and picking" not in text:
                raise RuntimeError("Persistent mesh storage verification did not complete")
            if args.verify_renderer and "authored voxel views match unmerged geometry, CPU instances, palette recolouring and transparent picking; exact palette relocation passed" not in text:
                raise RuntimeError("Authored voxel material/meshing verification did not complete")
            if args.verify_renderer:
                completion = ("voxel vehicle poses preserve all 16 company palettes and the original crash recolour" if args.renderer_verification_scope == "full" else
                              "scene-only voxel verification delegates complete vehicle pose matrices to explicit engine shards")
                if completion not in text:
                    raise RuntimeError("The requested full/scene renderer verification scope did not complete")
            if (args.gallery_voxels or args.gallery_voxel_prefix) and "exported voxel turntables, street-level views and neighbouring-building context" not in text:
                raise RuntimeError("Voxel review export did not complete")
            if args.verify_tile_picking and "roof/wall pixels select their owning tile across four rotations, with independent vehicle picking" not in text:
                raise RuntimeError("Geometry-aware tile picking did not complete")
            if args.verify_native_input and "Cocoa input recovery passed 32 focus/capture cycles" not in text:
                raise RuntimeError("Native input recovery verification did not complete")
            if args.verify_native_input and "Cocoa window-dispatched right/middle presses survive polling and release correctly" not in text:
                raise RuntimeError("Native button-event lifetime verification did not complete")
            if args.verify_renderer and "terrain zoom/drag anchor checks passed across all rotations" not in text:
                raise RuntimeError("The viewport navigation verification did not complete")
            if args.verify_renderer and "clicked-point yaw/tilt, release persistence and tilted screenshots passed" not in text:
                raise RuntimeError("Clicked-point orbit verification did not complete")
            if args.verify_renderer and "fixed FOV, legacy-zoom independence and street-level recovery after orbit passed" not in text:
                raise RuntimeError("Camera range/FOV stability verification did not complete")
            if args.verify_renderer and "loading/income text anchors follow orbit, dolly, Cab and secondary viewports; registry reuse passed" not in text:
                raise RuntimeError("World-anchored text-effect verification did not complete")
            if args.verify_renderer and "unlimited-distance GPU colour/depth/picking and infinite horizon ocean passed" not in text:
                raise RuntimeError("Unlimited-distance GPU verification did not complete")
            if (args.verify_clipping or args.verify_renderer) and "perspective clipping views preserve ray-tested coverage, depth, colour and picking" not in text:
                raise RuntimeError("GPU perspective clipping verification did not complete")
            if (args.verify_renderer or args.verify_instance_order) and "allocation-order views preserve coplanar colour, opacity and picking independently of mesh addresses" not in text:
                raise RuntimeError("Mesh allocation-order verification did not complete")
            if args.verify_instance_order and ("ordered child-layer views preserve coincident priority" not in text or "mixed-opacity shared-mesh batches preserve exact unpartitioned colour order and picking" not in text):
                raise RuntimeError("Child-layer or mixed-opacity ordering verification did not complete")
            if args.verify_instance_order and "GPU multi-mesh storage, large uploads and reuse preserve colour and picking" not in text:
                raise RuntimeError("Instance storage verification did not complete")
            if (args.verify_renderer or args.verify_instance_order) and "8 transient mesh payloads preserve exact instancing and address reuse without persistent cache growth" not in text:
                raise RuntimeError("Transient diagnostic mesh ownership verification did not complete")
            if (args.verify_renderer or args.verify_instance_order) and args.backend == "opengl" and not args.readback_presentation and "OpenGL frame-slot instance uploads retain bounded storage and fresh offsets" not in text:
                raise RuntimeError("Bounded OpenGL frame-slot upload verification did not complete")
            if args.verify_world_atlas and "whole-world atlas relocation preserves" not in text:
                raise RuntimeError("Whole-world atlas relocation verification did not complete")
            if args.orbit_drag and "middle-drag orbit released at yaw" not in text:
                raise RuntimeError("Middle-drag orbit did not complete")
            presentation_name = "Vulkan" if args.backend == "vulkan" else "OpenGL"
            if gpu_presentation and not args.screenshot_size and f"captured {presentation_name} presentation with" not in text:
                raise RuntimeError(f"The actual {presentation_name} presentation was not captured")
            if gpu_presentation and args.renderer == "3d" and not args.screenshot_size and not re.search(rf"captured {presentation_name} presentation with [1-9]\d* GPU viewport regions", text):
                raise RuntimeError("The presentation capture contains no GPU world viewports")
            if args.verify_renderer and args.backend == "opengl" and not args.readback_presentation and "OpenGL resident composition matches" not in text:
                raise RuntimeError("Exact OpenGL viewport/UI composition verification did not complete")
            if args.first_person and "first-person camera following vehicle" not in text:
                raise RuntimeError("The vehicle-window Cab button did not activate first-person following")
            if args.verify_voxel_vehicle is not None and f"live voxel vehicle engine {args.verify_voxel_vehicle} cargo " not in text:
                raise RuntimeError("The requested actual vehicle was not captured through its voxel binding")
            if args.verify_helicopter_rotor is not None and f"voxel helicopter rotor observation passed: engine {args.verify_helicopter_rotor} " not in text:
                raise RuntimeError("Original helicopter rotor animation observation incomplete; inspect run.log")
            if args.verify_aircraft_contact is not None and f"voxel aircraft ground contact passed: engine {args.verify_aircraft_contact} " not in text:
                raise RuntimeError("Actual stopped aircraft ground-contact observation incomplete; inspect run.log")
            if args.verify_voxel_poses is not None and any(f"voxel vehicle engine {engine} pose matrix passed" not in text for engine in args.verify_voxel_poses):
                raise RuntimeError("The requested voxel vehicle's complete pose matrix did not pass")
            if args.verify_voxel_meshes is not None and f"voxel mesh selection '{args.verify_voxel_meshes}' passed exact geometry, palettes and picking" not in text:
                raise RuntimeError("The requested voxel model family did not pass its exact mesh comparisons")
            if args.verify_vehicles and "vehicle direction/cargo poses passed GPU visibility and picking" not in text:
                raise RuntimeError("Vehicle geometry verification did not complete")
            if args.verify_industries and "authored industry views passed GPU visibility and material checks" not in text:
                raise RuntimeError("Industry geometry verification did not complete")
            if args.verify_trees and "lifecycle/LOD views passed materials (one RGBA8 rounding level), culling bounds and exact picking" not in text:
                raise RuntimeError("Tree lifecycle verification did not complete")
            if args.verify_trees and args.tree_verification_scope == "full" and "voxel tree lifecycle/palette/scale views preserve exact bindings" not in text:
                raise RuntimeError("Authored voxel tree state/palette verification did not complete")
            if args.verify_trees and args.tree_verification_scope == "active" and "active tree representation verified" not in text:
                raise RuntimeError("Active tree representation verification did not complete")
            if args.verify_bridges and "bridge assembly views, half-pillar clipping and transparent picking passed" not in text:
                raise RuntimeError("Bridge geometry verification did not complete")
            if args.verify_bridges and "bridge pillar caps remain below the deck with zero overhead picking pixels" not in text:
                raise RuntimeError("Bridge pillar/deck separation verification did not complete")
            if args.verify_fences and "terrain-following fence views passed GPU visibility and picking" not in text:
                raise RuntimeError("Fence geometry verification did not complete")
            if args.verify_foundations and "foundation views passed GPU visibility and picking" not in text:
                raise RuntimeError("Foundation geometry verification did not complete")
            if args.verify_tunnels and "tunnel exterior/interior views passed GPU visibility and picking" not in text:
                raise RuntimeError("Tunnel geometry verification did not complete")
            if args.verify_live_tunnel and "unobstructed lining pixels and unchanged vehicle state passed" not in text:
                raise RuntimeError("Live tunnel integration verification did not complete")
            if args.verify_live_tunnel and "live tunnel scenery culling views preserve exact RGBA and picking" not in text:
                raise RuntimeError("Live tunnel scenery culling comparison did not complete")
            if args.verify_rails and "rail layout/slope views, reservation materials and instancing passed" not in text:
                raise RuntimeError("Rail geometry verification did not complete")
            if args.verify_stations and "station layout views, company materials and transparent picking passed" not in text:
                raise RuntimeError("Station geometry verification did not complete")
            if args.verify_stations and "joined voxel dock views preserve original climate/company palettes" not in text:
                raise RuntimeError("Joined dock palette, slope and transparent-ground verification did not complete")
            if args.verify_ground_details and "raised ground-detail views and component materials passed" not in text:
                raise RuntimeError("Ground-detail geometry verification did not complete")
            if args.verify_rail_details and "catenary views passed, with correct aspects and transparent picking" not in text:
                raise RuntimeError("Rail-detail verification did not complete")
            if args.gallery_signal and f"exported signal {args.gallery_signal[0]} variant {args.gallery_signal[1]} state {args.gallery_signal[2]} model gallery" not in text:
                raise RuntimeError("Signal gallery did not complete")
            if args.gallery_catenary and f"exported catenary track {args.gallery_catenary[0]} grade {args.gallery_catenary[1]} model gallery" not in text:
                raise RuntimeError("Catenary gallery did not complete")
            for kind, variant, slope in args.gallery_ground_detail or []:
                if f"exported ground detail {kind} variant {variant} slope {slope} model gallery" not in text:
                    raise RuntimeError("Ground-detail gallery did not complete")
            if args.gallery_station and f"exported station {args.gallery_station[0]} layout {args.gallery_station[1]} model gallery" not in text:
                raise RuntimeError("Station gallery did not complete")
            if args.gallery_rail and f"exported rail {args.gallery_rail[0]} tracks {args.gallery_rail[1]} slope {args.gallery_rail[2]} model gallery" not in text:
                raise RuntimeError("Rail gallery did not complete")
            if args.gallery_tunnel and f"exported tunnel {args.gallery_tunnel[0]} direction {args.gallery_tunnel[1]} exterior and Cab galleries" not in text:
                raise RuntimeError("Tunnel gallery did not complete")
            for slope,foundation in args.gallery_foundation or []:
                if f"exported foundation {foundation} slope {slope} model gallery" not in text:
                    raise RuntimeError(f"Foundation {foundation} slope {slope} gallery did not complete")
            for style in args.gallery_fence or []:
                layout = f" layout {args.fence_layout}" if args.fence_layout is not None else ""
                if f"exported fence {style} slope {args.fence_slope} model gallery{layout}" not in text:
                    raise RuntimeError(f"Fence gallery {style} did not complete")
            if args.gallery_bridge is not None and f"exported bridge {args.gallery_bridge} model gallery" not in text:
                raise RuntimeError("Bridge gallery did not complete")
            if args.reference_bridge and ("focused live bridge at" not in text or "bridge parts rendered with volumetric geometry" not in text):
                raise RuntimeError("A live volumetric bridge was not captured")
            if args.reference_fence is not None and (f"focused live fence style {args.reference_fence} at" not in text or f"live voxel fence style {args.reference_fence} captured at" not in text):
                raise RuntimeError("The requested live voxel fence family was not captured")
            if args.reference_foundation and (f"focused live {args.reference_foundation} foundation" not in text or "live voxel foundation" not in text):
                raise RuntimeError("The requested actual foundation was not captured as voxels")
            if args.reference_tunnel and ("focused live tunnel at" not in text or "tunnel sections rendered with open portals and continuous interiors" not in text):
                raise RuntimeError("A live volumetric tunnel was not captured")
            if args.reference_station and ("focused live station at" not in text or "station tiles rendered with platforms, buildings and paired halls" not in text):
                raise RuntimeError("A live volumetric station was not captured")
            if args.reference_airport and ("focused voxel airport tile" not in text or "airport tiles rendered with authored voxel buildings" not in text):
                raise RuntimeError("A live authored voxel airport was not captured")
            if args.reference_airport_tile is not None and (f"focused voxel airport tile {args.reference_airport_tile} at" not in text or f"live voxel airport tile {args.reference_airport_tile} captured at" not in text):
                raise RuntimeError("The requested airport graphics type was not captured as voxels")
            if args.reference_tree:
                base, stage = args.reference_tree
                if not any(f"focused {style} tree {base} stage {stage} at" in text and f"live {style} tree {base} stage {stage} captured at" in text for style in ("voxel", "projected")):
                    raise RuntimeError("The requested actual tree lifecycle stage was not located and captured")
            if args.reference_vehicle is not None and (f"focused voxel vehicle engine {args.reference_vehicle} vehicle " not in text or f"live voxel vehicle engine {args.reference_vehicle} cargo " not in text):
                raise RuntimeError("The requested actual voxel vehicle was not located and captured")
            if args.reference_buoy and ("focused voxel buoy at" not in text or "live voxel buoy captured at" not in text):
                raise RuntimeError("An actual original voxel buoy was not located and captured")
            if args.verify_buoy_beacon and "voxel buoy beacon observation passed" not in text:
                raise RuntimeError("The actual voxel buoy did not retain both original beacon phases")
            if args.reference_vehicle_binding is not None:
                selected = rf"voxel vehicle engine {args.reference_vehicle} climate [0-3] binding state {args.reference_vehicle_binding}\b"
                if not re.search("focused "+selected,text) or not re.search("live "+selected,text):
                    raise RuntimeError("The requested actual vehicle climate/cargo binding was not located and captured")
            if args.reference_cargo:
                focus = re.search(rf"focused voxel vehicle engine {args.reference_vehicle} vehicle (\d+) at [^\n]*, load (\d+)/(\d+)", text)
                if not focus:
                    raise RuntimeError("The located voxel vehicle did not report its actual cargo count")
                vehicle, amount, capacity = map(int, focus.groups())
                loaded = int(args.reference_cargo == "full")
                if capacity == 0 or amount != (capacity if loaded else 0) or f"live voxel vehicle engine {args.reference_vehicle} cargo {loaded} captured as vehicle {vehicle}" not in text:
                    raise RuntimeError("The requested actual empty/full cargo state was not located and captured")
            if args.reference_industry:
                graphics, stage = args.reference_industry
                if f"focused voxel industry {graphics} construction stage {stage} at" not in text or f"live voxel industry {graphics} construction stage {stage} captured at" not in text:
                    raise RuntimeError("The requested actual voxel industry construction stage was not located and captured")
            if args.reference_industry_ground:
                graphics, stage = args.reference_industry_ground
                if f"focused voxel industry ground {graphics} construction stage {stage} at" not in text or f"live voxel industry ground {graphics} construction stage {stage} captured at" not in text:
                    raise RuntimeError("The requested actual voxel industry ground layer was not located and captured")
            if args.reference_house_stage is not None:
                focused = re.search(rf"focused voxel house (\d+) construction stage {args.reference_house_stage} at[^\n]*", text)
                layer = "ground " if focused and "ground-only binding" in focused[0] else ""
                if not focused or f"live voxel house {layer}{focused[1]} construction stage {args.reference_house_stage} captured at" not in text:
                    raise RuntimeError("The requested live voxel house construction stage was not captured")
                if args.reference_house_variant is not None and f"live voxel house {layer}{args.reference_house_id} construction stage {args.reference_house_stage} variant {args.reference_house_variant} captured" not in text:
                    raise RuntimeError("The requested source-art house variant was not captured")
            for graphic in args.verify_airport_animation or []:
                if f"airport {graphic} animation verification passed:" not in text:
                    raise RuntimeError(f"Airport {graphic} did not render every upstream animation frame; inspect run.log")
            for graphic in args.verify_industry_animation or []:
                if f"industry {graphic} animation verification passed:" not in text:
                    raise RuntimeError(f"Industry {graphic} did not render every distinct original animation frame; inspect run.log")
            if args.verify_power_sparks and "voxel power-station spark verification passed:" not in text:
                raise RuntimeError("A single actual power-station tile did not render all six original spark children; inspect run.log")
            if args.verify_toy_factory and "voxel toy-factory verification passed:" not in text:
                raise RuntimeError("One unchanged toy-factory tile did not render all 50 original ordered child frames and absences; inspect run.log")
            if args.verify_plastic_fountain and "voxel plastic-fountain verification passed:" not in text:
                raise RuntimeError("One unchanged plastic-fountain tile did not render all eight matching original ground/body pairs; inspect run.log")
            if (args.verify_forest_cycle or args.verify_harvest_cycle is not None) and "voxel forest cycle verification passed:" not in text:
                raise RuntimeError("A single unchanged forest tile did not render its harvested and every original regrowth state; inspect run.log")
            if args.verify_harvest_cycle is not None and f"observing actual mature industry graphics {args.verify_harvest_cycle}, harvested {args.verify_harvest_cycle+1}" not in text:
                raise RuntimeError("The harvest observer did not select the requested original graphics family; inspect run.log")
            if args.verify_voxel_cargo is not None and f"voxel vehicle cargo verification passed: engine {args.verify_voxel_cargo}," not in text:
                raise RuntimeError("A single voxel vehicle did not render both actual empty and full-capacity states; inspect run.log")
            if args.verify_train_collectors is not None and f"voxel train collector observation passed: engine {args.verify_train_collectors} " not in text:
                raise RuntimeError("The electric locomotive did not retain captured surface/portal/tunnel collector contact; inspect run.log")
            if args.verify_train_support is not None and f"voxel train support observation passed: engine {args.verify_train_support} " not in text:
                raise RuntimeError("The train did not retain captured station/flat/ramp/bridge/tunnel running-surface contact; inspect run.log")
            if args.verify_train_corners and f"voxel train corner observation passed: engine {args.verify_train_support} " not in text:
                raise RuntimeError("The train did not retain captured support through all four original corner tracks; inspect run.log")
            if args.verify_ground_continuity and "ground continuity verification passed:" not in text:
                raise RuntimeError("Mixed ground surfaces did not preserve their complete terrain footprint; inspect run.log")
            if args.verify_depot_traversal is not None and f"voxel depot traversal verification passed: vehicle {args.verify_depot_traversal}," not in text:
                raise RuntimeError("The actual vehicle did not complete a captured visible/depot/visible traversal; inspect run.log")
            if args.verify_house_lift and "voxel house lift animation verification passed:" not in text:
                raise RuntimeError("A single actual voxel office lift did not traverse eight positions; inspect run.log")
            if args.verify_radio_beacons and "voxel radio beacon observation passed:" not in text:
                raise RuntimeError("A captured voxel radio tower did not preserve three original beacon palette phases; inspect run.log")
            if args.verify_voxel_water is not None and f"voxel water palette observation passed: house {args.verify_voxel_water} " not in text:
                raise RuntimeError("A captured voxel water model did not retain five original palette phases; inspect run.log")
            if args.verify_stadium_palette is not None and f"voxel stadium palette observation passed: house {args.verify_stadium_palette} " not in text:
                raise RuntimeError("One actual voxel stadium did not retain every original crowd/scoreboard palette phase; inspect run.log")
            if args.verify_house_palette is not None:
                label = "stadium" if args.verify_house_palette in (20,32) else "house"
                if f"voxel {label} palette observation passed: house {args.verify_house_palette} " not in text:
                    raise RuntimeError("One actual voxel house did not retain every required original palette phase; inspect run.log")
            if args.verify_dock_palette is not None and f"voxel dock palette observation passed: graphics {args.verify_dock_palette} " not in text:
                raise RuntimeError("One actual voxel dock did not retain the original lamp/foam palette phases; inspect run.log")
            for graphic in args.verify_industry_palette or []:
                if f"voxel industry palette observation passed: graphics {graphic} " not in text:
                    layer = "steel-mill ground" if graphic < 157 else "fizzy-drink body"
                    phases = "seven original fire-palette phases" if graphic < 157 else "all five original bubble phases and materials"
                    raise RuntimeError(f"Actual {layer} {graphic} did not retain {phases}; inspect run.log")
            if args.reference_signal and ("focused live signal at" not in text or "signals rendered with state-aware lamps and semaphore geometry" not in text):
                raise RuntimeError("A live signal model was not captured")
            if args.reference_catenary and ("focused live catenary at" not in text or "catenary parts rendered with contact wires, droppers and masts" not in text):
                raise RuntimeError("Live catenary geometry was not captured")
            if args.reference_depot and ("focused live depot at" not in text or "depots rendered with open bays and component materials" not in text):
                raise RuntimeError("Live depot geometry was not captured")
            if args.reference_voxel_depot is not None and (f"focused voxel depot {args.reference_voxel_depot} direction " not in text or f"live voxel depot {args.reference_voxel_depot} direction " not in text):
                raise RuntimeError("The requested voxel depot family was not located and captured")
            if args.reference_depot_direction is not None and (f"focused voxel depot {args.reference_voxel_depot} direction {args.reference_depot_direction} at" not in text or f"live voxel depot {args.reference_voxel_depot} direction {args.reference_depot_direction} captured at" not in text):
                raise RuntimeError("The requested actual voxel depot exit direction was not captured")
            if args.reference_ship_depot is not None and (f"focused voxel ship depot axis {args.reference_ship_depot} at" not in text or any(f"live voxel ship depot axis {args.reference_ship_depot} part {part} captured at" not in text for part in range(2))):
                raise RuntimeError("Both parts of the requested actual voxel ship depot were not captured")
            if args.reference_dock is not None and (f"focused voxel dock {args.reference_dock} at" not in text or f"live voxel dock {args.reference_dock} climate state " not in text):
                raise RuntimeError("The requested actual voxel dock section was not located and captured")
            if args.gallery_depot and f"exported depot {args.gallery_depot[0]} direction {args.gallery_depot[1]} model gallery" not in text:
                raise RuntimeError("Depot gallery did not complete")
            if args.verify_depots and "depot direction views, component materials, company colours and transparent walls passed" not in text:
                raise RuntimeError("Depot verification did not complete")
            if args.verify_depots and "joined voxel ship-depot views preserve both axes" not in text:
                raise RuntimeError("Joined ship-depot palette, water ownership and transparency verification did not complete")
            if args.reference_crossing and ("focused live crossing at" not in text or "crossings rendered with state-aware signals and clear roadways" not in text):
                raise RuntimeError("Live crossing geometry was not captured")
            if args.gallery_crossing and f"exported crossing {args.gallery_crossing[0]} axis {args.gallery_crossing[1]} barred" not in text:
                raise RuntimeError("Crossing gallery did not complete")
            if args.verify_crossings and "crossing layout/state views, warning lamps and component materials passed" not in text:
                raise RuntimeError("Crossing verification did not complete")
            if args.reference_road_stop and ("focused live road stop at" not in text or "road stops rendered with volume shelters and loading bays" not in text):
                raise RuntimeError("Live road-stop geometry was not captured")
            if args.gallery_road_stop and f"exported road stop {args.gallery_road_stop[0]} layout {args.gallery_road_stop[1]} model gallery" not in text:
                raise RuntimeError("Road-stop gallery did not complete")
            if args.verify_road_stops and "road-stop layout/tram views, company materials and transparent shelters passed" not in text:
                raise RuntimeError("Road-stop verification did not complete")
            if args.verify_crossing_transitions and not re.search(r"live crossing \d+,\d+ changed from (open to barred|barred to open)", text):
                raise RuntimeError("A live crossing did not change state during capture")
            if args.reference_ground_detail and (f"focused live ground detail {args.reference_ground_detail[0]} variant {args.reference_ground_detail[1]} at" not in text or "ground-detail tiles rendered with raised crops, hay, rocks or turf" not in text):
                raise RuntimeError("Live raised ground detail was not captured")
            if args.gallery_vehicle is not None and f"exported vehicle {args.gallery_vehicle} model gallery" not in text:
                raise RuntimeError("Vehicle gallery did not complete; check the world's climate")
            if args.gallery_industry is not None and f"exported four model-review views for industry {args.gallery_industry}" not in text:
                raise RuntimeError("Industry gallery did not complete")
            if args.screenshot_size and tuple(args.screenshot_size) != image_size:
                raise RuntimeError(f"Screenshot dimensions differ: requested {args.screenshot_size}, got {image_size}")
            result = {"renderer": args.renderer, "rotation": args.rotation, "platform": platform.platform(),
                      "screenshot": str(screenshot), "image_size": image_size, "command": command, "pid": native_pid or process.pid,
                      "background": args.background}
            if benchmark_frames:
                result["benchmark"] = json.loads((output / "benchmark.json").read_text())
                if args.fullscreen and not result["benchmark"]["fullscreen"]:
                    raise RuntimeError("The fullscreen benchmark did not run in fullscreen mode")
                if not args.menu and not args.first_person and abs(result["benchmark"]["effective_zoom"] - args.zoom) > 0.001:
                    raise RuntimeError(f"Requested zoom {args.zoom}, measured {result['benchmark']['effective_zoom']}")
                if args.benchmark_frames and not (args.menu or args.first_person or args.orbit_drag or args.verify_native_input):
                    yaw_error = (result["benchmark"]["rotation"]-args.rotation+2)%4-2
                    pitch = result["benchmark"]["pitch_degrees"]
                    if abs(yaw_error) > 0.001 or abs(pitch-30) > 0.001:
                        raise RuntimeError(f"Fixed-view benchmark camera changed: requested rotation {args.rotation}/pitch 30, measured {result['benchmark']['rotation']}/{pitch}")
            (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            if args.brief:
                summary = {"output": str(output), "image_size": image_size}
                if benchmark_frames:
                    benchmark = result["benchmark"]
                    summary.update({"zoom": benchmark["effective_zoom"], "fps": benchmark["measured_fps"],
                                    "work_p95_ms": benchmark["frame_work_ms"]["p95"], "work_max_ms": benchmark["frame_work_ms"]["max"],
                                    "work_overruns": benchmark["frames_over_16_67_ms"], "intervals_over_20_ms": benchmark["intervals_over_20_ms"]})
                print(json.dumps(summary))
            else:
                print(json.dumps(result, indent=2))
            if args.keep_open:
                return
        finally:
            try:
                if memory is not None:
                    memory.close()
            finally:
                # A full evidence disk must not leave the native game running
                # after the memory sampler or its final report fails to write.
                if not args.keep_open or not screenshot.exists():
                    if args.macos_bundle:
                        match = re.search(r"OpenTT3D: Cocoa process (\d+)", (output / "run.log").read_text())
                        if match:
                            try:
                                os.kill(int(match[1]), signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                    if process.poll() is None:
                        if not args.macos_bundle:
                            process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()


if __name__ == "__main__":
    main()

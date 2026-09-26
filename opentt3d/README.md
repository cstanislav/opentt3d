# OpenTT3D

A renderer-only source port of OpenTTD, based on OpenTTD **15.3**, with
hand-authored 3D artwork referencing **OpenGFX2 Classic 0.8.1**.

Repository: https://github.com/cstanislav/opentt3d

## Development status

Implementation is in progress. [Development source previews](https://github.com/cstanislav/opentt3d/releases)
record tested checkpoints; complete artwork and portable desktop packages remain in development.
See [the implementation status](STATUS.md) for verified capabilities
and outstanding work. The upstream README is retained in `docs/UPSTREAM_README.md`.

## Project contract

- Preserve the upstream simulation, commands, save format, and scripting behavior.
- Preserve the original widgets, fonts, sprites in UI controls, menus and dialogs.
- Use OpenGFX2 Classic for the UI and individually authored 3D models in **all four climates**.
- Use calibrated perspective, clicked-point middle-button yaw/tilt, smooth extended zoom
  and first-person vehicle following; retain quarter-turn hotkeys.
- Keep the native low-resolution pixel grid crisp with nearest sampling. Model
  materials use native or coarser source levels and approximately uniform texel density.
- Render unsupported NewGRF world objects as placeholders while running their
  original gameplay code. The original NewGRFs are still required to load a save.
- Keep renderer state out of savegames and simulation random number generators.
- Ship the same downloadable desktop package types as OpenTTD, through GitHub
  Releases, including complete corresponding source and asset source.
- All graphics production is part of this project; the user supplies no artwork.

## Builds

Linux builds and tests run in Docker:

```sh
docker build -t opentt3d-dev -f docker/Dockerfile .
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/workspace" -w /workspace opentt3d-dev \
  python3 tools/opentt3d/build.py --build-dir build-linux
```

For local macOS development, use existing CMake and Apple's command-line tools:

```sh
python3 tools/opentt3d/fetch_vulkan.py build-macos/vulkan
python3 tools/opentt3d/build.py --build-dir build-macos
python3 tools/opentt3d/fetch_baseset.py build-macos/baseset
```

The build helper does not install host packages. Native release packaging uses
GitHub-hosted macOS and Windows runners; Linux packaging uses a container.

### Try the development renderer

On macOS, from the repository root:

```sh
OPENTT3D_RENDERER=1 build-macos/opentt3d \
  -X -x -c build-macos/opentt3d.cfg \
  -v cocoa-vulkan -b 40bpp-anim -I "OpenGFX2 Classic"
```

On Linux, the Vulkan driver is `sdl-vulkan`. OpenGL fallback drivers are
`cocoa-opengl`, `sdl-opengl` and `win32-opengl`; `-DOPTION_VULKAN=OFF` builds without
Vulkan dependencies. The SDL Vulkan Windows integration still needs native runtime
verification. Use the existing console
(backquote) and `renderer3d on` / `renderer3d off` to switch rendering modes.
`Ctrl+[` and `Ctrl+]` rotate; `Ctrl+\` resets the camera. These shortcuts can be
rebound in the original hotkey configuration. `renderer3d locate` finds one of
the authored building types when present (introduced in 1957 and 1968).

Middle-drag rotates around the terrain point under the initial press, with vertical
motion tilting the view (3°–89°). In Cab mode it looks around the moving eye,
including up/down, without ending follow. The first-person geometry, terrain,
picking and labels have no fixed draw-distance limit. Scene collection is bounded
by the real map and view frustum; the infinite-water exterior reaches the horizon.

Terrain steps render at twice their original height. Object sizes retain their
authored scale, with foundations, bridge ramps and dock supports meeting the taller
landscape. The elevation change is presentation-only. Sloped roof surfaces are
permitted in the artwork pipeline.

Voxel models now use four **automatically generated** distance LODs. Nearby models
keep their full authored mesh; coarse versions use deterministic occupied-cell and
palette aggregation, preserve outer bounds, and share the scene-pinned mesh caches.
Set `OPENTT3D_AUTO_LOD=0` for a full-detail comparison. Trees use the previous
projected-material3D geometry by default after matched voxel-tree LOD tests remained
too slow. `OPENTT3D_TREE_STYLE=voxel` selects the retained voxel trees for diagnostics.

The current artwork is a development subset: **1,247 voxel volumes**, covering
110 house IDs,62 diagnostic tree sprite families and all256 vanilla vehicle definitions,
plus54/175 industry body definitions and21/74 airport definitions. Climate/state
coverage remains incomplete: Arctic farms/forests and several non-temperate industry
grounds retain supplied source artwork pending independent volumes. No model has
final visual approval. Remaining industry and
infrastructure objects use reference sprite planes counted as missing geometry.
See [status](STATUS.md) and [verified results](VERIFICATION.md).

Run the GPU and loaded-world navigation checks with an isolated fixture:

```sh
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --output build-macos/verified-view --savegame media/baseset/opntitle.dat \
  --background --backend vulkan --rotation 1 --verify-renderer \
  --memory-limit-mib 6144 --timeout 7200
python3 tools/assets/inventory.py --require-complete
```

The inventory command intentionally fails until complete geometry, states and
visual review are available. `renderer3d references` exports resolved house/tree
artwork; `renderer3d gallery <house-id-or-tree-sprite>` exports four model views.
The authoritative voxel artwork is `assets/3d/voxels.json`. The tree profile pack
provides the active projected-material3D trees; the older house/industry profiles
and `models.json`/glTF prototype remain reference/fallback paths. Profile-pack
presence does not establish voxel coverage.

The full renderer check includes every voxel vehicle climate/cargo/livery/heading
comparison and can exceed two hours on software Vulkan. CI runs the scene checks
with `--verify-renderer --renderer-verification-scope scene` and requires four
separate `--verify-voxel-poses` runs covering engines0…63,64…127,128…191 and192…255.
Each shard retains all original comparisons and its own7200-second/6GiB bounds.
`renderer3d verify-scene` is the corresponding console command; ordinary
`renderer3d verify` and `--verify-renderer` still run the complete matrix.

`OPENTT3D_TUNNEL_SCENERY_CULL=1` enables an experimental conservative tree-visibility
filter while the Cab is inside an original tunnel. Both mouth cones remain infinite,
and intersecting tree bounds are retained. `--verify-live-tunnel` compares it with
full capture in20 views using exact RGBA and picking. The option is disabled by
default; native dense-Cab results improve but still miss60fps.

On macOS, use `--background` for automated reviews while using the computer. It keeps
the Cocoa window hidden and prohibits app activation while retaining normal GPU
rendering and framebuffer captures. The harness checks the native hidden-window
diagnostic; event polling also rejects accidental visibility or activation. It supports
OpenGL, Vulkan and `--macos-bundle`, and is incompatible with fullscreen/native-input
checks. Direct launches can set `OPENTT3D_BACKGROUND=1`. These captures validate rendered
output; foreground interaction still requires a separate input review.

Vehicle review commands are `renderer3d vehicle-references`,
`renderer3d vehicle-gallery <engine> [loaded]` and `renderer3d verify-vehicles`.
Use a world in the engine's climate: unavailable sprite slots may contain another
climate's artwork. `renderer3d industry-references` exports the 175 default
industry tile definitions and four stages, including special-procedure metadata.
`renderer3d industry-gallery <graphics-id>` renders a modelled industry tile.
There are initial profiles for 40 mine/power-station/refinery/offshore/farm/factory/steelworks/sawmill tile definitions;
remaining industry geometry and individual state/material review are unfinished.
`renderer3d verify-industries` checks all current profiles in four GPU-rendered views.

Both backends retain interactive world colour/picking targets on the GPU. OpenGL
composes clipped viewports with the original driver's UI/animation shaders, uses
on-demand one-pixel picking, and limits queued work to two frames. Cocoa shares only
the completed presentation texture with its layer context, synchronized by GPU fences.
`OPENTT3D_GL_PRESENTATION=0` selects the original readback path for controlled review;
the smoke harness exposes it as `--readback-presentation`.

`screenshot presented <name>` captures the Vulkan swapchain, including UI/cursor,
or OpenGL's completed viewport/UI texture before its hardware cursor. Both 3D smoke
paths use GPU composition captures; regular viewport and giant screenshots retain
their existing readback/streaming paths. The container includes
Khronos validation layers: add `--vulkan-validation` to a Vulkan smoke run to
require core and synchronization validation and reject reported errors.

## Upstream tracking

`opentt3d/upstream.json` pins both upstream projects by tag and full commit.
The upstream git remote is `https://github.com/OpenTTD/OpenTTD.git`. Rendering
implementation lives in `src/renderer3d/`; integration changes are reviewed
separately from upstream's engine. Development builds keep their own revision
identity until interoperability has been tested.

```sh
python3 tools/opentt3d/upstream.py check
# When a newer stable tag is available:
python3 tools/opentt3d/upstream.py prepare 16.0
```

`prepare` fetches the tag, creates `update/openttd-<version>`, starts a normal
upstream merge and updates the pin after a clean merge. It leaves the result
for review and testing. If the merge needs resolution, resolve it and run
`upstream.py record <version>` before the compatibility checks. The weekly
GitHub workflow reports newly available stable versions.

## Licensing

OpenTTD, OpenGFX and OpenGFX2 are GPL-2.0. OpenTT3D code and derivative artwork use GPL-2.0.
See the original [license](../COPYING.md), [credits](../CREDITS.md), and asset
attribution files. Model sources are distributed with exported assets.

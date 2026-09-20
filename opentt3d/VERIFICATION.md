# Initial implementation verification

## Environments

- Native macOS 26.6.2, Apple M3 Pro, Apple OpenGL 4.1.
- Docker Desktop Linux ARM64, Debian bookworm, Mesa llvmpipe OpenGL 4.5.
- OpenTTD baseline: 15.3 (`14ec60f248547d4d062a1160f0fc26d742319888`).
- OpenGFX: 8.0, downloaded with the published SHA-256 verified.

All generated configs, saves, downloads and screenshots are under ignored build
directories. Interactive smoke tests use `-X -c <isolated-config> -x` to avoid
the user's installed content and configuration.

## Automated tests

```sh
python3 tools/opentt3d/build.py --build-dir build-macos
python3 -m unittest discover -s tools/assets -p 'test_*.py'
python3 tools/opentt3d/check_boundary.py
```

Results: 99 native CTest cases, 100 container CTest cases (the Linux build adds
an ICU test), and four asset compiler tests passed. These include the original
AI regression fixtures. Renderer tests check upstream projection agreement,
projection/unprojection at every rotation and zoom, immutable model instancing,
outward normals, non-degenerate triangles and glTF geometry preservation.

The file-boundary guard is a review aid, not a proof of simulation equivalence.

## Native rendering

```sh
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --output build-macos/smoke-example --rotation 1
```

The harness uses existing OpenTTD console scripts and its own screenshot API.
It fails if the 3D backend did not initialize or reported a rendering error.
Both `32bpp-optimized` and `40bpp-anim` were exercised locally.

The initial new-game script can capture the final world-generation progress
dialog. For a settled UI comparison, load the saved fixture in a second run:

```sh
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --output build-macos/smoke-loaded \
  --savegame build-macos/smoke-example/save/smoke-state.sav
```

For Linux rendering in Docker, use `--init` so Xvfb's startup signal is handled:

```sh
docker run --init --rm -v "$PWD:/workspace" -w /workspace opentt3d-dev \
  xvfb-run -a python3 tools/opentt3d/smoke.py \
  --build-dir build-linux --output build-linux/smoke-example --rotation 1
```

## Official-binary save interoperability

`fetch_reference.py` downloads the official universal Mac 15.3 zip and verifies
SHA-256 `c2ac22ab3ac9ac1e82a8d9029b7e4ab069e425904420076605d860e64460f579`.
The original app signature was also verified with `codesign --verify --deep --strict`.

```sh
python3 tools/opentt3d/fetch_reference.py build-stock
python3 tools/opentt3d/save_probe.py \
  --executable build-stock/OpenTTD.app/Contents/MacOS/openttd \
  --savegame build-macos/smoke-example/save/smoke-state.sav \
  --baseset build-macos/baseset/opengfx-8.0.tar \
  --output build-macos/roundtrip-stock
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --savegame build-macos/roundtrip-stock/save/roundtrip.sav \
  --output build-macos/roundtrip-back
```

One generated, paused vanilla 128×128 fixture passed this round trip. This does
not establish complete save coverage, gameplay equivalence or multiplayer
compatibility; those remain separate gates.

## UI pixels

Official OpenTTD and OpenTT3D loaded the same paused fixture, with OpenGFX 8.0,
the same resolution, language and UI settings. At the native 2560×1600 backing
resolution, these rectangles were compared:

- Toolbar: `164,0,2232,70` — 156,240 pixels.
- Status bar: `164,1556,2232,44` — 98,208 pixels.

Both the 32bpp and 40bpp OpenTT3D captures matched official OpenTTD exactly in
both regions. Window dialogs, other UI scales and languages require additional
fixtures. Rectangle coordinates must be adjusted to the actual backing resolution.

```sh
python3 tools/opentt3d/compare_ui.py reference.png actual.png \
  --rect 164,0,2232,70 --rect 164,1556,2232,44
```

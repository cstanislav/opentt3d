# OpenTT3D

A renderer-only source port of OpenTTD, based on OpenTTD **15.3**, with
hand-authored 3D artwork referencing **OpenGFX 8.0**.

Repository: https://github.com/cstanislav/opentt3d

## Development status

Implementation is in progress. This is not a completed 3D edition or a released
product. See [the implementation status](STATUS.md) for verified capabilities
and outstanding work. Upstream documentation is retained at the repository root.

## Project contract

- Preserve the upstream simulation, commands, save format, and scripting behavior.
- Preserve the original widgets, fonts, sprites in UI controls, menus and dialogs.
- Match OpenGFX with individually authored 3D models for **all four climates**.
- Provide the familiar orthographic projection plus optional quarter-turn rotation.
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
docker run --rm -v "$PWD:/workspace" -w /workspace opentt3d-dev \
  python3 tools/opentt3d/build.py --build-dir build-linux
```

For local macOS development, use existing CMake and Apple's command-line tools:

```sh
python3 tools/opentt3d/build.py --build-dir build-macos
python3 tools/opentt3d/fetch_baseset.py build-macos/baseset
```

The build helper does not install host packages. Native release packaging uses
GitHub-hosted macOS and Windows runners; Linux packaging uses a container.

## Upstream tracking

`opentt3d/upstream.json` pins both upstream projects by tag and full commit.
The upstream git remote is `https://github.com/OpenTTD/OpenTTD.git`. Rendering
implementation lives in `src/renderer3d/`; integration changes are reviewed
separately from upstream's engine. Development builds keep their own revision
identity until interoperability has been tested.

## Licensing

OpenTTD and OpenGFX are GPL-2.0. OpenTT3D code and derivative artwork use GPL-2.0.
See the original [license](../COPYING.md), [credits](../CREDITS.md), and asset
attribution files. Model sources are distributed with exported assets.

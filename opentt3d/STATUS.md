# Implementation status

This file records implemented and verified work, not promises of completeness.

## Baseline

- [x] Public fork with original history: `cstanislav/opentt3d`.
- [x] OpenTTD 15.3 and OpenGFX 8.0 pinned by full commit.
- [x] Container build and upstream tests verified (97 tests, Linux ARM64).
- [x] Native macOS baseline built; 96 upstream tests passed.
- [x] Native macOS mesh-renderer launch and framebuffer captures verified on Apple M3 Pro.
- [x] Current tests: macOS 99/99, Linux ARM64 100/100, asset compiler 4/4.
- [x] Linux Mesa/llvmpipe mesh-renderer smoke test inside Docker/Xvfb.

## Renderer

- [x] Depth-tested viewport mesh rendering and offscreen framebuffer composition.
- [x] Native toolbar/status-bar pixel comparison with official 15.3: 254,448 identical pixels (32bpp and 40bpp).
- [ ] Original UI clipping, overlapping windows, and palette handling.
- [x] Default projection agreement with upstream and quarter-turn camera mathematics.
- [x] Quarter-turn controls and camera-aware town/station/sign placement.
- [ ] Camera-aware terrain, vehicle, and sign selection.
- [ ] All secondary viewports, construction tools, overlays, and screenshots.
- [ ] Performance and lifetime checks.

## Artwork

- [x] Four authored reference-model sources, a distinct development placeholder, and glTF export.
- [ ] Complete material-detail and reference-model visual review.
- [ ] Terrain, foundations, water, and vegetation in all climates.
- [ ] All vanilla infrastructure.
- [ ] All vanilla buildings, industries, and animation states.
- [ ] All vanilla vehicles, liveries, cargo states, and effects.
- [ ] NewGRF provenance and placeholders.
- [ ] Complete, validated asset coverage manifest.

## Release gates

- [ ] Matching-version save round trips in both directions.
- [x] One paused vanilla fixture: OpenTT3D -> official OpenTTD 15.3 -> OpenTT3D, including native reload/render.
- [ ] Command replay / simulation-state equivalence.
- [ ] Stock-client / stock-server multiplayer interoperability.
- [ ] UI comparisons and rotated construction interaction checks.
- [ ] Linux x86-64, macOS universal, Windows x86/x64/ARM64 packages.
- [ ] Source and documentation archives, checksums, asset sources and attribution.
- [ ] Native Mac play-through of the packaged release.
- [ ] First complete release published.

## Current development limitations

The 3D renderer is opt-in. It currently renders tile terrain, prototype road/rail
surfaces, one reference tree, two reference buildings and the Kirby Paul engine.
Most vanilla world objects use **magenta development placeholders**. Tree
species, growth/death appearances, company livery variants, construction stages,
snow, and the other climates require their authored models/materials.

Rotation, label positioning, mouse/keyboard panning and basic picking are present,
but rotated construction previews, exact object picking, cargo overlays, elevated
vehicle-follow camera behavior, transparency and foundation/bridge geometry still
need completion and interaction tests. The original view supports the upstream
selection overlay pass. Frame-level scene caching is implemented; chunk caches,
instancing and LOD work remain. Very large world screenshots need tiled GPU rendering.

The current CI definition covers Linux x86-64, macOS arm64 and Windows x86/x64/ARM64
builds. ARM64 Windows is a cross-compilation check, not a native runtime test.
Release packaging, universal Mac binaries, network compatibility metadata and
multiplayer/replay verification remain release work. Development builds retain
their own network revision identity.

These limitations are **not** the agreed first-release scope. A complete vanilla
asset pack and the compatibility gates above are still required before that release.

See [verification notes](VERIFICATION.md) for commands and the exact extent of testing.

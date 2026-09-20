# Implementation status

This file records implemented and verified work, not promises of completeness.

## Baseline

- [x] Public fork with original history: `cstanislav/opentt3d`.
- [x] OpenTTD 15.3 and OpenGFX 8.0 pinned by full commit.
- [ ] Container build and upstream tests verified.
- [ ] Native macOS build and launch verified.

## Renderer

- [ ] Depth-tested viewport mesh rendering.
- [ ] Original UI clipping, overlapping windows, and palette handling.
- [ ] Exact default projection and quarter-turn camera.
- [ ] Camera-aware terrain, vehicle, and sign selection.
- [ ] All secondary viewports, construction tools, overlays, and screenshots.
- [ ] Performance and lifetime checks.

## Artwork

- [ ] Hand-authored reference models and review renders.
- [ ] Terrain, foundations, water, and vegetation in all climates.
- [ ] All vanilla infrastructure.
- [ ] All vanilla buildings, industries, and animation states.
- [ ] All vanilla vehicles, liveries, cargo states, and effects.
- [ ] NewGRF provenance and placeholders.
- [ ] Complete, validated asset coverage manifest.

## Release gates

- [ ] Matching-version save round trips in both directions.
- [ ] Command replay / simulation-state equivalence.
- [ ] Stock-client / stock-server multiplayer interoperability.
- [ ] UI comparisons and rotated construction interaction checks.
- [ ] Linux x86-64, macOS universal, Windows x86/x64/ARM64 packages.
- [ ] Source and documentation archives, checksums, asset sources and attribution.
- [ ] Native Mac play-through of the packaged release.
- [ ] First complete release published.

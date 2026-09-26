# OpenTT3D development preview — September 26, 2026

This source checkpoint publishes the accumulated voxel catalogue and renderer work.
Download the source archive below and follow `opentt3d/README.md` to build. Portable
desktop packages and the complete visual recreation remain in development.

## Included

- 1,002 explicitly authored voxel volumes with source palettes and state bindings.
- Body/ground coverage for all 110 house definitions, including construction,
  source-permitted variants and joined structures.
- All 62 original tree families with 434 lifecycle volumes, including snowy and
  Toyland states.
- 129 vehicle definitions: all 88 road vehicles, all 11 ships and a partial rail
  catalogue. Additional airport, industry, depot, dock and track work is included.
- GPU-resident Vulkan/OpenGL world and UI composition, geometry-aware picking,
  fixed-lens orbit and street/Cab cameras, bounded frame submission and memory tooling.
- Hidden macOS review mode: `smoke.py --background` renders without activating or
  displaying the app, including through the development app bundle.

## Verification

- 186 native tests, 97 asset/compiler tests and 8 harness tests pass.
- Hidden GL/Vulkan checks pass exact model, ordering/storage and world-atlas checks.
- 56 same-backend model views preserve 22,937,600 exact RGBA pixels between the
  earlier visible and new hidden review paths.
- Detailed, fixture-scoped evidence and retained failures are recorded in
  `opentt3d/VERIFICATION.md` and `opentt3d/PERFORMANCE.md`.

## Remaining work

Catalogue-wide basic coverage is unfinished. Missing vehicles, most industries and
airports, other infrastructure, terrain, objects and effects remain queued. Existing
models require further source-proportion, material, state, footprint, clearance and
all-angle review; **zero models have final visual approval**.

The complete 1,002-volume renderer verifier still exceeds its 6 GiB guard. Smooth
60 fps, arbitrary-map/all-day memory bounds, current Linux/Windows validation and
portable packaging remain open. These source previews record development progress;
the complete objective and all later fidelity passes remain active.

OpenTT3D is based on OpenTTD 15.3 and OpenGFX2 Classic 0.8.1. Code, asset source,
attribution and licensing are included in the source archive.

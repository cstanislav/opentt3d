# 2026-10-18 asset consistency, branding and nightly repair

This pass targeted the three reported visual inconsistencies, the branding, the
nightly pipeline, the upstream check and the public documentation. It is a
progress record, not a claim that every model has reached 9/10.

## Visual changes

- **Drive-through bus and truck stops:** the lane substrate now samples the
  adjoining paved road ground sprite (`SPR_ROAD_X/Y - 19`) instead of the station
  ground sprite. The drive lane therefore uses the same asphalt texture and
  markings as the road at its border. Bay stops use an adjacent road tile's actual road bits, so their lane
  matches that road without guessing a station orientation.
- **Canal dikes:** all twelve original ground-owned dike volumes were raised from
  a two-unit strip to a six-world-unit stepped stone quay. The original ten-world-
  unit navigable channel remains clear. The quay has three stepped masonry
  courses, a solid coping and two-course stone grain. Water, ships, adjacency,
  animation and picking remain at their original level and ownership; the water
  surface was deliberately **not** lowered after the first attempt showed ships
  floating above it.
- **Banks:** the Arctic/tropical `bank2` golden cupola was moved from cell 31 to
  cell 32, the exact seam of the 64-cell joined body. The north and south owners
  still partition the same volume without duplicate cells. The temperate bank's
  existing cupola remains at cell 32.

## Branding

The icon is now an isometric orange cube with a white dollar sign on its front
face and the classic green **OPEN** / **TT3D** ribbons. It replaces the
locomotive icon and the flat orange-diamond reading while preserving the original
logo's strongest cues. `tools/assets/build_branding.py` emits the polygon-only
SVG and calls the existing reproducible icon compiler for PNG, ICO, ICNS,
installer assets and the SDL icon header.

## Documentation

- Replaced the top-level README with a current 3D overview, download table,
  camera controls, modelling scope, nightly/upstream status and eight fresh
  screenshots.
- Removed hand-crafting language from public docs and source comments. Historical
  sealed review evidence is not rewritten; those files are audit records, not
  current project descriptions.
- Recorded the upstream check: pinned **15.3**, latest stable **15.3**, newest
  prerelease **16.0-beta4**. No merge or pin change was made.

## Nightly repair

`CI - Nightly` run 39092709178 failed for two independent reasons:

1. MinGW checkout could not create retained review paths above Windows
   `MAX_PATH`.
2. The macOS job forced `MACOSX_DEPLOYMENT_TARGET=10.13`, while the current
   libc++ headers require 10.15 for `std::filesystem`.

The workflows now enable `core.longpaths` before Windows checkout and set the
macOS target to 10.15. Four regression tests assert ordering, the target and the
absence of sparse/excluding workarounds. The failed run is retained; no green
nightly run is claimed until GitHub completes one.

## Full-catalogue visual sweep

Twenty labelled contact sheets in `overview-sheets/` cover all1,915 compiled
models (100 per sheet). They were individually viewed. Most entries are true
multi-layer volumes. The single/two-layer entries are ground, runway, lawn,
construction-site, paving or effect surfaces; no ordinary runtime object is a
sprite billboard. The sweep also exposed the remaining priorities: flat airport
ground slabs, intentionally flat site plates, thin effect shells, the84 unbound
larger-HQ studies (not rendered by the runtime overview) and the lock/river
fallback states. See`coverage-audit.json`. The sweep is not a 9/10 approval.

## Verification

- 276 asset tests pass, including the updated twelve-dike and bank-seam tests.
- 118 harness tests pass, including four checkout/nightly regression tests.
- 219 native tests pass.
- `tools/opentt3d/check_boundary.py` passes.
- The screenshots in `captures.json` are newly captured with the current build.
- No model is promoted to 9/10 or 8/10 by this pass; the next quality pass must
  still review each model individually and retain source/orbit/street/world/state
  evidence.

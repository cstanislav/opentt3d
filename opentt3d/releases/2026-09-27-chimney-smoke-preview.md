# Voxel power-plant chimney smoke

Power-plant chimneys now render all eight original plume frames as wind-bent voxel
volumes, with continuous lower wisps and detached upper eddies. The catalogue reaches
**1,715 models**, preserving all earlier models and bindings.

## Changes

- Added eight manually authored chimney frames with explicit bindings in every climate.
- Preserved original stationary anchors, local altitude, countdown, spawning, deletion,
  industry availability and simulation RNG.
- Kept smoke absent under original industry transparency/invisibility and before the
  chimney's construction is complete.
- Added a read-only cycle audit that checks all 64 original sprite/countdown phases,
  ordered wraparound, fixed placement and unclickable ownership.

## Verification

Public packages independently reconcile 19 attachments, 18 checksums, 2,089 source files
and six identical 1,715-model catalogues at commit `a02a304fd`. All eight packaging jobs
pass, together with three downloaded Mac render/save controls, seven hosted graphical
clipping controls, Windows x64/x86 native load/save and Linux's 900-frame journey.

Eighteen prototype and fourteen integrated controls pass, plus two missing-frame/climate
fallback controls. Six live controls—including native app launches—capture 21,855 samples
and complete ordered cycles. All 832 integration images match staging, 648 original
source-image comparisons remain exact, and 64 actual sprite bindings match their models.
The native suite passes 206 checks, the asset suite 143 and the harness suite 22.

Seven native source bounds match exactly; the remaining frame has a one-pixel right-edge
excess. Plume contours, breakup and finer painting remain provisional.

## Play

The [verified `.28` desktop release](https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20260927.28)
is available for Windows, macOS and Linux, with required graphics bundled.
Use the [installation guide](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md)
for the current independently verified download and platform instructions.

## Still in progress

The other 68 presentable effect sprites still need voxel artwork. Larger-aircraft airport
clearances, remaining catalogue coverage, catalogue-wide fidelity, sustained smooth 60fps
and long-duration memory acceptance remain open. Final visual approvals remain zero.

# First voxel roadworks effects

The roadworks bulldozer now uses a small tracked voxel model in each of its four original
displayed directions. This brings the catalogue to **1,707 models**, with all earlier
models and bindings preserved.

## Changes

- Added tracks and rollers, a supported recessed cab with operator, exhaust, open
  underbody and a curved blade with separate front/back colours.
- Bound all four original bulldozer sprites explicitly in every climate. Original
  sprite selection preserves reversing without an invented heading change.
- Added an ordinary NoAI roadworks fixture, read-only effect traces and an independent
  movement audit. Original spawning, ticks, deletion, saves and simulation RNG remain
  authoritative.
- Added missing-frame/climate controls and rejected bindings for the unpresented bubble
  transition. The other 76 presentable effect sources still need voxel artwork.

## Verification

Twelve prototype and ten integrated controls pass, plus three fallback/rejection
controls. The native suite passes 206 checks, the asset suite 143 and the harness suite
19. All 448 integration images match staging; 648 original source-image comparisons
remain exact. Six live controls capture 28 complete original 116-waypoint paths,
including reverse movement and unclickable ownership.

## Play

Desktop packages appear after the exact tagged commit passes every packaging job.
Use the [installation guide](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md)
for the current independently verified download and platform instructions.

## Still in progress

Source registration, cab/hood proportions, blade contour and finer paint remain
provisional. Larger-aircraft airport clearances, remaining catalogue coverage,
catalogue-wide fidelity, sustained smooth 60fps and long-duration memory acceptance
remain open. Final visual approvals remain zero.

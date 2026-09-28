# Six-stage voxel diesel exhaust

Diesel trains now emit source-specific brown voxel puffs that expand into open billows
and disperse into small fragments. The catalogue reaches **1,726 models**, preserving
all earlier models and bindings.

## Changes

- Added six original diesel-exhaust frames with 24 explicit climate bindings.
- Preserved original spawning, upward motion, timing, smoke settings and simulation RNG.
- Added a read-only lifetime audit that checks the brief first frame within one complete
  lower-ID puff, plus ordinary reduced/disabled-smoke and departure-save fixtures.
- Corrected the isolated mesh-check camera's small-object cutoff while retaining its
  coverage threshold and all existing gallery images.

## Verification

Twelve prototype, twenty integrated and two fallback controls pass. The native suite
passes 206 checks, the asset suite 143 and the harness suite 28. All 672 integration
images match staging; 648 original exports and 148 earlier steam views remain exact.
All six source bounds match, and native OpenGL/Vulkan views agree.

Eight live controls record 150 complete presented lifetimes across 10,004 observations,
including 18 ordered six-frame lifetimes. Original reduced/disabled-smoke settings and
both paused trace-on/off comparisons pass. Failed studies and fixture controls remain
preserved alongside the corrections.

## Play

Desktop packages appear after the exact tagged commit passes every packaging job.
Use the [installation guide](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md)
for the current independently verified download and platform instructions.

## Still in progress

Exhaust contour, density, directional paint and all-angle breakup remain provisional.
Another 57 presentable effect sources need voxel artwork. Larger-aircraft airport
clearances, remaining catalogue coverage and sustained smooth 60fps remain open.
No model has final visual approval.

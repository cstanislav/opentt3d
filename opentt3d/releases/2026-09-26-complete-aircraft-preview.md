# OpenTT3D development source preview — 1,031 voxel volumes

This incomplete development source prerelease adds body bindings for **all41 original
aircraft**, including separate Toyland artwork, three helicopters and four independently
selected rotor states. The catalogue now contains **1,031 authored voxel volumes** and
**169/256 vehicle definitions**. It is not a verified portable desktop package.

## Verified progress

- Five Toyland planes and three helicopter bodies preserve distinct original families.
  Shared normal aircraft sources match1,120 Arctic/tropical-versus-temperate views;
  reused Toyland sprite numbers do not alias the different normal artwork.
- Rotor volumes follow the four original stopped/moving source states, remain attached
  to the body's smoothed position and preserve original unclickable ownership. The
  Cab camera hides its own rotor. Native and street galleries include joined parts.
- Normal public NoAI fixtures observe every aircraft reaching destination service.
  Held-service fixtures verify all three helicopters' four rotor states and later
  stopped-to-running transitions through ordinary full-load orders and release.
- Actual airport-ground checks expose and repair the original sprite anchor's one-unit
  hover gap. Helicopter wheels/skids now meet the real airport surface. A stricter
  connectivity audit also repairs detached aircraft nose struts and skid supports.
- Both native backends pass **44,608 body poses,384 joined rotor poses,720 model views**
  and exact world-atlas colour/picking checks. Vulkan normal/Toyland runs peak3.40/3.26GiB,
  and the complete OpenGL fleet matrix peaks3.61GiB, under the sampled6GiB guard.
- Native186/186, asset/compiler101/101 and harness8/8 tests pass. Windows x64/x86/arm64
  compilation passes after the prior macro repair. In-progress CI jobs are now preserved
  across frequent publication pushes; current Linux verification remains pending.
- macOS app checks remain hidden and inactive, without bringing windows forward.

## Still incomplete

**Final visual approvals remain zero.** Aircraft wing/fin/body proportions, helicopter
cabin/skid depth, source-anchor alignment, painted shading, glazing, small windows and
distant blade sampling still differ from source artwork. Complete airport/Cab/flight/
crash clearance is not established. Remaining trains, industries, airports, infrastructure,
terrain, objects and effects still require breadth coverage and the later fidelity passes.

Close airport tests average60fps, but wide-world smooth60fps, arbitrary-map/multi-viewport/
all-day memory, current Linux/core/synchronization, Windows runtime, foreground input,
cross-backend raster agreement, replay/network and portable packaging remain unfinished.
Failed and interrupted evidence remains recorded in the development ledgers.

See `opentt3d/VERIFICATION.md`, `opentt3d/VOXEL_PASSES.md`, `opentt3d/VOXEL_REVIEW.md`
and `opentt3d/PERFORMANCE.md` for the evidence and remaining requirements.

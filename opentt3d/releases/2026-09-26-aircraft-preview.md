# OpenTT3D development source preview — 1,019 voxel volumes

This is an incomplete development source prerelease. It adds ordinary fixed-wing
aircraft coverage and fixes diagnostic memory retention. It is not a production
release or a verified portable desktop package.

## Progress

- The catalogue contains **1,019 manually authored voxel volumes** and bindings for
  **161/256 original vehicle definitions**, including all33 ordinary fixed-wing
  aircraft. Seventeen new bodies preserve propeller, delta, high-wing, twin/four-
  engine and multi-body layouts, with aliases only where original source art permits.
- Public NoAI fixtures build ordinary airports/aircraft and observe each aircraft
  moving and servicing its destination before saving the world for review.
- Both native macOS OpenGL and Vulkan pass **432 aircraft mesh views,35,904 exact
  company/crash/cargo/heading poses** and4,096,000 world-atlas colour/picking pixels.
- The prior full1,002-volume verifier now completes on both backends below its6GiB
  sampled guard (4.52GiB OpenGL,4.38GiB Vulkan). Call-scoped diagnostic reference
  meshes no longer accumulate in immutable CPU/GPU caches. Address-reuse checks
  preserve exact colour/picking and reject persistent-cache growth.
- Quiet macOS review keeps the native window hidden and inactive. Renderer checks
  run without activating/flashing a window.
- Source regressions pass100 asset/compiler tests and eight harness tests; native
  tests pass186 cases. Windows macro-collision and full Linux smoke timeout repairs
  are included, with follow-up CI still required.

## Incomplete work

**No asset has final visual approval.** Aircraft wing/fin/body proportions, source-
painted shading, windows and diagonal silhouettes remain under review. Complete
actual-flight/airport/Cab clearance is not established. Toyland aircraft, helicopters,
rotors, remaining trains, industries, airports, infrastructure, terrain and effects
still need catalogue-wide coverage and the later fidelity/state/climate passes.

The bounded verifier results are workload-specific. Sustained smooth60fps,
arbitrary-map/multi-viewport/all-day memory, current Linux/core/synchronization,
Windows runtime, foreground input, replay/network and portable packaging gates remain
unfinished. Earlier failed evidence is retained in the development ledgers.

Build instructions and detailed status: `opentt3d/VERIFICATION.md`,
`opentt3d/VOXEL_PASSES.md`, `opentt3d/VOXEL_REVIEW.md`, `opentt3d/PERFORMANCE.md`.

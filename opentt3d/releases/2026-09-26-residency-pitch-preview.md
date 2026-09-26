# OpenTT3D development preview: bounded residency and pitched train contact

This source prerelease retains the published **1,180-volume** artwork catalogue
and improves renderer memory ownership and train running-surface contact. It remains
an incomplete development checkpoint with **zero final visual approvals**.

## Included progress

- Lossless retained voxel-cell runs and a shared palette replace per-model dense
  source grids. Dense data is reconstructed only when needed for meshing/diagnostics.
- A scene-pinned CPU surface cache releases cold allocations while retaining stable
  mesh identities. Scene copies and asynchronous visibility workers preserve leases
  until their last read. Its default soft budget is1GiB.
- OpenGL retires cold immutable mesh buffers; Vulkan retires completed, unused shared
  pages and invalidates every slice on those pages. The default GPU soft budget is
  512MiB. Active/in-flight geometry may exceed either budget.
- Train bodies pitch in physical world proportions about their wheel-support plane.
  Captured station/track/bridge/tunnel surfaces retain the half-unit running datum,
  including descending quarter-cell boundaries and grade transitions. Roof collectors
  retain their mounts while independently fitting the original contact wire.
- Joined-industry exports include ground-only construction states; original-art
  provenance guards keep supplied replacements across shared multi-tile structures.
- Presentation benchmarks now record draw-deadline lateness. Public construction
  fixtures support legal snowy/desert sites and town-only water towers.

## Verification

- **196 native tests** and **nine harness tests** pass.
- Matched, frozen1,169-volume expanded OpenGL/Vulkan controls pass the complete
  model/vehicle/tree/infrastructure matrices under the unchanged **6GiB guard**.
  Sampled peaks: **5,779,248,360bytesGL /5,359,801,360bytesVulkan**.
- Each backend passes28,056 authored views,322,048 vehicle poses across592 declared
  climate/cargo bindings, pitched support/collector matrices, exact retirement/
  rebuild checks and4,096,000-pixel world-atlas/picking comparisons.
- Sixteen live loaded locomotive/wagon support observations pass across all four
  temperate rail types and both backends. Further Toyland/corner-route checks remain
  active. The later provisional artwork candidates are reviewed separately.
- Preceding release`.8` completes macOS arm64, Windows x86/x64/arm64 and LinuxGL CI.
  Its LinuxVulkan job fails the memory guard and predates this residency repair.

## Work still active

The matched dense Cab samples average only **12.714fpsGL /14.058fpsVulkan**; all30
measured intervals exceed20ms. The bounded memory result does not establish smooth
60fps, arbitrary-world/all-day/multiple-viewport residency or current Linux success.
Catalogue-wide artwork/state coverage, source-painted fidelity, street/Cab clearance,
native input and portable packaging remain open. Failed evidence is retained.

The renewed work window remains active through **2026-09-26 19:00:00 UTC**.

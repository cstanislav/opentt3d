# OpenTT3D development source preview — train clearance and sawmill

This incomplete development source prerelease contains **1,144 authored voxel
volumes**, with body bindings for **all256 original vehicle definitions**. It adds
the complete original locomotive body catalogue, independently moving electric roof
collectors, train loading-gauge repairs and eleven sawmill construction/storage
volumes. Final visual approvals remain zero.

## Verified progress

- All35 locomotive definitions retain their inspected climate-specific bodies.
  All55 locomotive/climate/railtype fixtures complete service, return and holding;
  all55 hiddenOpenGL live-selection captures pass. Twelve further public-NoAI
  climate/railtype consists traverse real bridges, ramps and tunnels.
- Train Z-grid repairs preserve XY footprints and the running-rail support plane.
  Every bound empty/loaded train body clears the actual faceted tunnel lining and
  inward ribs. Separate collector parts keep fixed roof mounts while following
  their own contact-wire heights, lowering to7.55units inside tunnels.
- Full1,133-volume OpenGL/Vulkan matrices each pass **27,192 model views**,
  **322,048 vehicle poses**, **10,880 joined collector poses**,384 joined rotor
  poses and the exact4,096,000-pixel world-atlas/picking comparison. All four
  electric engines pass live surface/portal/tunnel collector observations on both
  backends. Reference diagonals at silhouette edges fix the observed AsiaStar
  one-pixel merged/reference mismatch; the failed evidence is retained.
- Sawmill11…15 keeps its foundations, open timber construction, northlight roofs,
  cutting machinery, monitor-roof store, logs and separated boards. The six original
  empty early log/board bodies remain absent, and full ground layers retain independent
  ownership. Both backends pass264 new model views/840 industry body-ground views;
  all20 actual construction-state selections pass.
- A tree-root obstruction found by LinuxVulkan CI reproduces locally and is repaired.
  Both native backends now pass243,635 unobstructed tunnel-lining pixels in the
  preserved saved world. Linux revalidation remains pending.
- Native **190/190**, asset/compiler **106/106** and harness **8/8** tests pass.
  Full native renderer matrices remain below the6GiB sampled-memory guard. Review
  windows remain hidden/inactive; simulation commands, saves and RNG retain upstream
  ownership.

## Continuing work

Industry coverage is13/175 body definitions with16 independent grounds; airports,
infrastructure, terrain, objects and effects retain substantial missing coverage.
Source-painted shading and fine proportions remain work across the whole catalogue.
Slope/curve wheel contact and complete station/depot/bridge/Cab clearances remain
under review. Close-view60fps averages retain presentation outliers; sustained smooth
arbitrary-world60fps is still unmet. Linux full-matrix completion, Windows runtime,
foreground input, all-day memory, replay/network and portable packaging remain open.

Matched1,130-control/1,133-repair checks add approximately352…365MiB sampled memory;
the wider silhouette-safe triangle stream keeps exact pixels but retains the existing
wide-view bottleneck (approximately37…39fps,0.6…0.7% below the control).

See `opentt3d/VERIFICATION.md`, `VOXEL_PASSES.md`, `VOXEL_REVIEW.md` and
`PERFORMANCE.md` for retained evidence and remaining scope.

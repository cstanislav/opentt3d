# OpenTT3D development preview: joined oil-rig construction and helicopter service

This source prerelease expands the authored catalogue to **1,180 voxel volumes**.
It is an incomplete development checkpoint with **zero final visual approvals**.

## Included progress

- Eleven explicitly authored oil-rig volumes cover four initial pilings and paired
  braces, intermediate platforms/buildings, the completed derrick and flare, and
  independent water across the complete six-tile layout.
- Original empty construction bodies and repeated source-state aliases are retained.
  The completed rig's neutral airport keeps its authored water ground and the
  original **54-unit helicopter landing deck**.
- Native joined exports include complete projected bounds and tile-origin metadata,
  enabling registered source comparisons of all construction stages.
- Public-NoAI fixtures construct real rigs and operate helicopters from a helidepot.
  Additional freight fixtures traverse four connecting curves, a bridge and a tunnel
  both loaded and empty.
- Smoke-process cleanup runs even when a disk-full error prevents the final memory
  report from being written; a real-child regression exercises that failure.

## Verification

- All **20 actual oil-rig construction selections** pass.
- OpenGL and Vulkan each pass **264 new mesh views**, **1,616 industry-state views**
  and exact **4,096,000-pixel world-atlas/picking comparisons** under the6GiB guard.
- Both backends observe helicopter253's **40 landing-support corners** on captured
  deck triangles, all four rotor states and stopped-to-running transition.
- Compiler/schema checks and all **nine** downloader/screenshot/memory harness tests
  pass. Quiet LaunchServices checks of the preceding verified app report a hidden,
  inactive window and preserve the exact rendered/picking comparisons.

## Work still active

Catalogue-wide industry, airport, infrastructure and effect coverage remains open.
Source-painted proportions/detail, all-angle and Cab clearance, complete state/
climate review, and sustained smooth60fps remain required. Linux Vulkan's expanded
workload still exceeds6GiB; a matched mesh-residency repair and train-pitch/contact
candidate are undergoing their complete matrices. Failed and interrupted evidence
is retained. See `opentt3d/VERIFICATION.md`, `PERFORMANCE.md` and `VOXEL_REVIEW.md`.

The renewed work window remains active through **2026-09-26 19:00:00 UTC**.

# OpenTT3D development preview: airport catalogue breadth

This source preview adds **32 airport tile definitions**, bringing provisional
coverage to **53 of 74 definitions** and the artwork catalogue to **1,274 volumes**.
The full catalogue and source-fidelity goal remains in progress.

## Added artwork and integration

- Full-tile aprons and parking stands, runway centre sections and threshold bars,
  independently owned perimeter fences, circular helipads and plain-H helipads.
- The three small-airport timber terminals, including the raised control cabin,
  antennae, blue water tank and open supporting frame.
- Original ground/body ownership: small terminals33/34 are entirely ground-owned;
  terminal35 has an independent office/paving layer and cabin/tank body. The renderer,
  diagnostics and coverage inventory now handle original ground-only airport tiles.
- A climate-source audit catches older Toyland terminal/hangar artwork that differs
  despite sharing sprite IDs. Those supplied layers are retained until independently
  authored Toyland versions exist.
- Registered source sheets correctly interpret original screen-relative child
  fences. Source comparisons corrected terminal door/roof orientation and oversized
  control-cabin/tank heights.

## Verification

- **200 native tests, 120 asset/compiler/schema tests and nine harness tests pass.**
- Both backends pass the new surface/small-terminal exact mesh, palette, transparent
  picking and independent ground/body checks. The four focused runs preserve
  **16,384,000 exact world-atlas RGBA/picking pixels**.
- Six Arctic/tropical/Toyland backend matrices pass; each checks1,728 authored views
  and840 ground/body visibility views. Toyland correctly rejects all12 unsupported
  older body bindings.
- All58 new source-bound layers use only colours present in their original layer.
  The broader828-pair climate audit identifies137 differing original layers;
  the newly added families match across all four climates.
- All18 live selections for nine representative ground-only, terminal, runway and
  helipad definitions pass across both backends. Peak final/live memory is
  **2,802,306,168bytes**. Registered source, four-sided street and joined-world images
  were inspected; source/artwork/executable hashes match the tested freeze.
- Native reviews run in background mode under the6GiB memory guard. Original images,
  failed attempts and earlier candidates are retained.

The earlier release`.11`CI has now completed successfully, including LinuxOpenGL,
the Vulkan scene/electric-journey controls and all256 engines across322,048 sharded
poses, plus macOS and Windows jobs. Its renderer peak is4,537,843,712bytes. Newer
terrain/current-checkpoint CI remains separate and pending.

## Remaining work

These are provisional coverage bindings, with **zero final visual approvals**.
Timber/roof shading, paving, lamp and helipad detail still need source-painted
refinement. Remaining airport grounds, climate variants, heliport44 and wider
aircraft/layout clearances remain open, alongside missing industries, tram-depot
artwork and all later catalogue-wide fidelity passes. Sustained smooth60fps and
long-duration production review are not yet achieved.

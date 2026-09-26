# OpenTT3D development preview: industry states and low airport terminals

This source prerelease expands the catalogue from **1,180 to1,247 authored voxel
volumes**. It remains provisional, with **zero final visual approvals**.

## Included progress

- Oil-well pumps, joined farm buildings/silos, paper processing, banana/rubber
  plantations, food processing, tropical waterworks and the joined temperate bank.
- Original empty construction bodies, repeated source-identical artwork and
  independent full-tile grounds remain explicit. The bank retains its completed
  body through every construction slot while its ground changes on completion.
- Low airport terminal63/64/69 adds its L-plan courtyard, recessed glazing/entry,
  supported roof and original fence variants over a separately opaque apron.
- Airport source registration includes complete projected bounds and tile-origin
  sidecars. Source replacements keep their supplied ground/body/animation family.
- Public fixtures support town-sized bank sites, helistations and helidepots through
  normal NoAI commands, including non-hangar station-service destinations.

## Verification

- **196 native,117 asset/compiler/schema and9 harness tests** pass.
- **88 actual industry-state runs** pass on OpenGL/Vulkan:288 required ground
  selections,242 body selections and46 original empty states. Both farm and food
  climates are included; peak sampled process memory is **2,704,411,720bytes**.
- Focused source-registered/all-angle/street galleries cover the new families.
  Corrected airport checks include96 authored views and72 independent ground/body
  visibility cases on each backend, plus exact world-atlas/picking comparisons.
- All27 airport source-layer climate pairs match exactly. Visual review caught and
  repaired a facade paint brush that covered perpendicular side windows.
- Eight9,000-frame electric-locomotive runs verify all four actually traversed
  corner-track types, station/grade/bridge/tunnel support and collector contact.
- Preceding release`.9` passes Linux OpenGL, macOS and Windows x86/x64/arm64 CI.
  Linux Vulkan stays below4.15GB but reaches its7200-second renderer-matrix limit;
  its incomplete result is retained as a failure.

## Remaining work

Industry coverage is **54/175 body definitions plus58 grounds**; airports are
**21/74 body definitions plus3 grounds**. Catalogue completion, source-painted
fidelity, all-angle/street/Cab clearance and full platform review remain open.
Cross-backend gallery differences remain recorded. The prior matched dense Cab
controls still average only **12.714fpsGL /14.058fpsVulkan**; smooth60fps and arbitrary-
world/all-day/multiple-viewport memory behavior remain unproven.

The renewed work window remains active through **2026-09-26 19:00:00 UTC**.

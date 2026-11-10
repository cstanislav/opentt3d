# OpenTT3D development .46 — runtime catalogue closure

This is a development prerelease. The authored runtime ledger has **2,887
entries, all at 9/10**; 183 retained non-runtime references remain separately at
3/10. The reviewed title world reports zero unmodelled reference sprites.
[Immutable `.42`](https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20261003.42)
remains the recommended playable checkpoint until the independent matrix passes.

## Included work
- Authored 3D disaster body/shadow volumes close the final original runtime
  sprite family; all fifteen subtypes and all 23 source sprites are bound.
- Road slopes and road-waypoint signs now use world-space 3D geometry.
- Locks use the complete map-owned 3D wall family, including independent source
  face culling.
- The Toyland factory 144 completed state now has a 3D finished-factory body.
- Branding, road-stop asphalt, stepped canal quays, centred bank cupolas,
  nightly CI repairs, README/screenshots and pinned OpenGFX2 work are retained.

## Independent checks completed
- 8/8 packaging jobs passed; 19 hosted assets and 49,507 source blobs match the
  immutable tag; the packaged 2,035-model catalogue compiles exactly.
- macOS ARM64 and x86_64 packages passed Vulkan/OpenGL package controls and
  title-world saves (x86_64 under Rosetta).
- Independent native release runs `42565973306`, `42571096954` and `42573903535`
  passed on Windows x64/x86/native-ARM64 and Linux x86_64. Linux passed default
  Vulkan/OpenGL presentation, tile picking, a synchronous console save and a
  dedicated loopback listener. Every Windows architecture loaded/saved its
  packaged title world and accepted a dedicated loopback client.
- Four title-world rotations (0–3) retain 64 picking samples, acknowledged
  commands and synchronous saves.
- A real GPL-2.0 custom river NewGRF retains 1,156 natural selectors, all twelve
  flat bank offsets and custom rivermouth/rapids sources.
- The expanded ship fixture verifies all seven ships through two loading docks,
  four dock orientations, the actual buoy, the dry harbour island and the depot,
  and captures all seven 3D hulls in the saved world.
- A catalogue-wide geometry audit verifies all **2,035 authored volumes** at
  automatic LOD factors2/4/8/16 (**8,140 views**); source-owner bounds and
  occupancy stay exact, ordinary growth is at most one coarse cell.

## Limit retained
Natural company-score HQ selection is verified at stage4 from score870. Custom
river animation phases and explicit zero-feature absence, full ship
bridge/swept clearance, Windows windowed/pointer/replay checks, full multiplayer
client play and sustained 60fps/memory remain open. A hosted Windows
windowed/Mesa probe produced an empty frame log and is retained as rejected
environment evidence. The measured `.46` title control is **39.37 fps**,
retained without masking. This development prerelease is not recommended; `.42` remains the recommended checkpoint.



Published through the reviewed publication workflow; the 19 audited assets and manifest were unchanged.



## Final CI and rendering checks
The current source revision completed all ten CI jobs successfully in
[`42591061848`](https://github.com/cstanislav/opentt3d/actions/runs/42591061848):
Linux OpenGL full no-scope, Vulkan scene and four vehicle-pose shards, macOS
ARM64 and Windows x64/x86/ARM64. The OpenGL full job passed the complete
renderer/picking/bridge control in about 95 minutes. The scene matrix includes
24,528 tree lifecycle views, 20,832 distant-tree views, 8,688 industry views and
64 four-rotation picking samples. The catalogue LOD geometry audit covers 2,035
volumes at factors 2/4/8/16 (8,140 views).

This does not alter the release assets, which remain the independently audited
bytes. `.42` remains the recommended checkpoint.

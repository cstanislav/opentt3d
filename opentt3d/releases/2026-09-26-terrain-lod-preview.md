# OpenTT3D development preview: doubled terrain and automatic detail

Terrain steps now render at **twice their original height**. Buildings and vehicles
retain their authored dimensions, with taller foundations, bridge ramps/pillars and
dock supports meeting the new landscape. Simulation coordinates and save data retain
their original scale.

## Rendering changes

- Four model LOD levels are **generated automatically** from authored voxel volumes.
  Nearby geometry stays detailed; deterministic cell/material aggregation, original
  outer bounds and scene-pinned caches provide reduced meshes for distant models.
- The previous **projected-material 3D trees are the default again**. Matched controls
  show that voxel-tree LODs alone remain too slow. Existing voxel trees are retained
  for diagnostics with `OPENTT3D_TREE_STYLE=voxel`; `OPENTT3D_AUTO_LOD=0` disables
  automatic model reduction for comparisons.
- Terrain UVs retain their source-art registration. Camera movement, Cab placement,
  navigation, labels and picking use the taller terrain while preserving the fixed
  interactive lens and unlimited draw distance.
- Tree roots follow their individual ground positions. Tunnel retaining walls and
  earth meet the taller bank, including above monorail hoods, while bores keep their
  original loading gauge.
- Dock decks rise to sixteen units with longer piles, preserving slab, railing,
  bollard and lamp dimensions, water-level foam and shore/water ownership.
- Sloped roof surfaces are permitted in continued artwork refinement. Existing roofs
  have not all been converted.

## Verification

- **199 native tests** and **117 asset/compiler/schema checks** pass.
- OpenGL and Vulkan pass the bridge, foundation, rail, fence, tunnel, station, dock,
  ground-continuity and exact world-atlas/picking matrices below the 6 GiB guard.
- Both scene checks pass fixed-lens navigation, Cab, orbit/tilt, vehicle following,
  unlimited-distance labels/picking, and **62 projected-tree families across 5,544
  lifecycle/LOD views** per backend.
- Both **9,000-frame moving electric-train routes** pass doubled-grade wheel support,
  all four corner tracks and independent surface/portal/tunnel collector contact.
  The initial old-grade-limit failure is preserved alongside the corrected checks.
- Electric engines23–26 pass the steeper body/collector pose matrices on both backends.
  Helicopter254 retains all120 checked support corners on the original54-unit oil-rig
  deck, all rotor states and restart in both1,800-frame controls.
- Structural orbit/street images were inspected. Original and failed evidence is
  preserved; generated-image compaction is gated by explicit successful checks.
- Final portal and actual projected/voxel tree controls pass, including6,144,000 exact
  world-atlas/picking pixels. All final source/artwork/executable hashes match.

## Performance and remaining work

The final matched doubled-terrain 300-frame tunnel-Cab controls measure:

| Mode | OpenGL | Vulkan |
| --- | ---: | ---: |
| Full voxel models and trees | 10.211 fps | 10.842 fps |
| Automatic voxel LODs | 21.738 fps | 28.698 fps |
| Automatic LODs and projected 3D trees | 49.477 fps | 60.000 fps |

The projected-tree samples have154/0 intervals over20ms on OpenGL/Vulkan. These
results explain the tree fallback; they do not establish sustained smooth60fps
across arbitrary worlds. Catalogue/state coverage, fine source fidelity,
cross-backend differences and complete current Linux Vulkan verification remain
unfinished. This is a **1,247-volume development source prerelease with zero final
visual approvals**.

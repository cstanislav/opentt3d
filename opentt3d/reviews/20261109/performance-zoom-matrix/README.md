# `.46` performance by camera zoom

Native Apple M3 Pro, Vulkan, title world `(200,160)`, rotation1, 1280×720,
`--running`, 120 measured frames unless noted. The title world is the same
2,035-model catalogue.

| zoom | fps | mean vertices | capture mean | p95 work |
|---:|---:|---:|---:|---:|
| 1 | **60.01** | 40.1M | 3.35 ms | 8.22 ms |
| 2 | 44.54 | 79.0M | 13.65 ms | 31.92 ms |
| 3 | **7.30** (300 frames) | 112.7M | 146.96 ms | 409.73 ms |
| 4 | 42.03 | 114.7M | 16.72 ms | 34.23 ms |
| 5 | 38.59 (300 frames) | 105.4M | 18.49 ms | 34.27 ms |

**Zoom3 is a real cache-thrashing defect**, not a rendering-quality tradeoff:
with the default 1 GiB CPU voxel cache, capture is ~147 ms while zoom4 with a
similar vertex count captures in ~17 ms. Setting
`OPENTT3D_CPU_VOXEL_CACHE_MIB=1536` for the same zoom3 view retains
**46.95 fps**, capture **10.69 ms**, p95 **29.94 ms**, peak footprint
**4.470 GiB** (under the 6 GiB limit). The same setting leaves zoom5 at
**37.42 fps**, so it is a retained cache pathology, not a 60 fps solution.

## Default cache change

Because the zoom3 collapse is repeatable and severe, the renderer's default CPU
voxel cache was raised from 1 GiB to **1.5 GiB** (`OPENTT3D_CPU_VOXEL_CACHE_MIB`
still overrides it). A 300-frame retest with the new default gives:

| zoom | fps | capture mean | p95 work | peak footprint |
|---:|---:|---:|---:|---:|
| 3 | **46.89** | 10.60 ms | 28.67 ms | 4.374 GiB |
| 5 | **38.53** | 19.05 ms | 34.49 ms | 3.897 GiB |

The zoom3 cache collapse is fixed; the wide-view performance remains a failure
(38.53 fps versus the prior 39.37 fps control). The memory peak remains under
the 6 GiB limit. This is a real cache-budget repair, not a resolution/detail
reduction or a 60 fps claim.

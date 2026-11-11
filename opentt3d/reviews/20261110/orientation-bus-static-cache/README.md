# Orientation controls, road-vehicle grade pitch, and cached scene capture

## Scope

This review covers three related changes:

- Rail and road toolbars expose only Autorail/Autoroad for line construction.
  The four fixed rail directions and two fixed road/tram directions were removed,
  including their number hotkeys.
- Depot, ship-depot, rail-station and bus/tram-stop pickers now show one preview.
  Clicking the preview rotates the selected orientation. The drive-through-only
  and tram restrictions still select only valid orientations.
- Road vehicles pitch with the road surface sampled ahead and behind their
  longitudinal axis. The voxel vehicle path now applies that grade to road
  vehicles as well as trains.
- GPU world presentation caches static scene geometry and the vehicle layer for
  an unchanged simulation tick. Static scenery is refreshed at a bounded cadence
  while map revisions keep changing (animations), and at a slow maximum age for
  UI/presentation changes that do not mark a tile dirty.

## Orientation and bus evidence

The source changes are in `src/rail_gui.cpp`, `src/road_gui.cpp`,
`src/dock_gui.cpp`, `src/renderer3d/world_capture.cpp` and
`src/renderer3d/voxel_models.cpp`.

A temporary runtime observation on the four-rotation title world captured
actual road vehicles on both grades, including changing grades while moving
(`bus-grade-observation.txt`). Example:

```text
OpenTT3D: road vehicle 76 grade -1 tile 202,62
OpenTT3D: road vehicle 407 grade 1 tile 143,125
OpenTT3D: road vehicle 765 grade 0.75 tile 84,112
```

The diagnostic was removed after verification. The implementation remains in
the normal capture path and uses `GetSlopePixelZ(..., true)` so bridge ramps are
included. No simulation, command, save-format or RNG behavior is changed.

## Performance measurements

The test world is the retained title save at 1280x720, zoom 5, running, Vulkan,
with the full map in view. The current full-capture and cached binaries were built from the same source
tree; only the viewport capture path differs. The published baseline is retained
as the earlier release control.

| Run | FPS | mean capture | mean GPU frame | mean window draw | vertices |
|---|---:|---:|---:|---:|---:|
| published full-capture baseline | 40.45 | 18.14 ms | 18.85 ms | 23.74 ms | 93,279,534 |
| current full capture control | 60.03 | 8.65 ms | 9.31 ms | 10.43 ms | 46,724,791 |
| static + vehicle capture cache | 60.00 | 6.10 ms | 9.33 ms | 8.16 ms | 46,724,147 |
| road-catalogue fixture, cached | 59.98 | 0.67 ms | 4.87 ms | 4.06 ms | 4,088,422 |

The wide title view reaches 60.00 fps in this 300-frame control. The remaining
bound is the GPU/composition interval, not the CPU world capture. Compared with
the published baseline, the current presentation raises the title rate by 48.3%;
the static road fixture reaches 60 fps. Render distance, map extent and vehicle
coverage are unchanged. This is a bounded 300-frame control, not a sustained
long-duration or multi-viewport acceptance.

Raw benchmark JSON is retained beside this file:

- `wide-baseline.json`
- `wide-full-current.json`
- `wide-static-cache.json`
- `road-static-cache.json`

## Verification

- Native C++ suite: 219/219.
- Harness: 126/126 (run separately).
- Presentation boundary: 147 files (run separately; the three GUI pickers and
  read-only viewport revision API were added to the reviewed boundary).
- `--reference-vehicle 116 --verify-voxel-vehicle 116 --verify-road-stops` and
  `--verify-renderer --renderer-verification-scope scene` pass on the road fixture.
- A broad verifier run combining every live family exceeded its 240-second
  review timeout; it is retained as a limitation rather than reported as a pass.
  The focused vehicle/road-stop verifier passes.

## Cache behavior

The static layer refreshes whenever the map revision, camera, texture generation
or tile-selection state changes. Vehicles and effects are captured once per
simulation tick and reused for presentation frames in that tick. Construction and
camera changes therefore appear immediately; animated map tiles also refresh on
their next draw. `OPENTT3D_STATIC_CACHE=0` selects the original one-pass capture
for a controlled A/B measurement.

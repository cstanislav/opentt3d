# `.46` catalogue-wide automatic LOD geometry audit

The current renderer was loaded with the title world and exercised with the new
`renderer3d verify-catalogue-lods` path. It expanded every authored catalogue
source and reduced it at automatic factors **2, 4, 8 and 16**:

- **2,035 authored volumes**;
- **8,140 LOD views** (four factors per volume);
- every reduced mesh is non-empty, finite, within the source bounds plus at
  most one coarse cell, and retains a valid palette owner;
- **64 ordinary views** expand a bounding box by at most one coarse cell;
- every independent source-owner family (HQ/object, river relief/bank,
  lock walls and disaster bodies) retains exact bounds, occupied cells and
  exposed faces at every factor.

The run also completed a synchronous save with acknowledged console commands.
The exact log, save and world screenshot are retained. This is a catalogue-wide
geometry/LOD audit; full per-model assembled pixel/picking comparisons remain
covered by the renderer/tile-picking suites and the four-rotation world matrix.

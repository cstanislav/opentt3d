# `.46` four-rotation picking and save matrix

The independently downloaded macOS ARM64 `.46` package was loaded with its
packaged title world at `(200,160)`, zoom5, Vulkan, 800×600, for rotations
`0, 1, 2, 3`. Each run used `--verify-tile-picking`, a synchronous save and the
recorded console path. Every rotation reported:

- 64 roof/wall picking samples owning their tile, including independent
  vehicle picking;
- a synchronous `smoke-state.sav` and a successful console save;
- eight (rotation0), nine (1), ten (2) or eleven (3) acknowledged commands;
- no unmodelled-reference report.

The four screenshots and logs are retained beside the actual saves. These are
world-facing rotation/picking controls, not a proof that every authored model
and every vehicle heading is correct at every angle; the catalogue-wide pose and
LOD matrix remains separate.

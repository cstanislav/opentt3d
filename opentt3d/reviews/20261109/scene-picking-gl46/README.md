# OpenGL scene/picking verification

Current build, OpenGL, title world, 800×600, scene verification scope with tile
picking. The run completed:

- 24,528 tree lifecycle/palette/scale views;
- 20,832 distant-tree views;
- 8,688 industry construction/animation views;
- GPU depth/object picking and transparency;
- 64 roof/wall pixels owning their tile across four rotations with independent
  vehicle picking;
- an actual synchronous save.

This complements the Vulkan scene-scope control. The separate all-engine
vehicle-pose shards and catalogue LOD audit are retained independently.

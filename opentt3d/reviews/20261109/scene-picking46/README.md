# `.46` scene/picking verification

The current build was loaded with the title world and run through the full
scene-scope renderer verification with tile picking, Vulkan, rotation1, 800×600.

The retained log reports, among the complete scene matrix:

- 24,528 voxel tree lifecycle/palette/scale views;
- 20,832 distant tree views;
- 8,688 industry construction/animation views;
- 48 power-station spark poses;
- 2,035-volume catalogue LOD audit (8,140 views; 64 ordinary bounds growths);
- GPU depth/object picking, transparency, large-world subpixel, atlas,
  unlimited-distance and first-person paths;
- 64 roof/wall pixels owning their tile across four rotations with independent
  vehicle picking.

The run wrote an actual synchronous save. Scene scope delegates the complete
vehicle pose matrices to the separate engine shards; those are not claimed by
this file. The full no-scope renderer run was attempted separately but did not
finish and is retained under `../full-picking-incomplete/`.

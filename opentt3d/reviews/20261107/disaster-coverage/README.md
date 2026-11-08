# Disaster vehicle 3D coverage

This review replaces the final original 2D runtime geometry gap: the fifteen
disaster subtypes and their twenty-three source sprites (3901..3923). The
production catalogue now binds fifteen authored 3D volumes:

- Nine body volumes: Zeppelin, small UFO, large UFO, F-15, AH-64, Skyranger,
  small submarine, large submarine and the four-frame helicopter rotor state.
- Six separate flattened 3D shadow volumes for the air vehicles.
- Twenty-three original body sprite IDs select their body model; the six air
  shadow IDs select state1 shadow models. Rotor sprites 3901..3904 retain their
  original four animation frames while sharing the authored rotor volume.

The bodies retain the source palette directions, grey/dark hulls, UFO domes and
rim lamps, wing/tail registrations, submarine deck/tower/periscope silhouettes,
helicopter rotor separation and the original game-scale proportions. They are
actual occupied voxel volumes, not camera-facing sprites. Source PNG/PAM pairs
and the individual eight-view gallery exports are retained beside the evidence.

## Native evidence

One actual Vulkan saved world contains all fifteen subtypes: seven airborne
bodies, six air shadows, one rotor and both submarines on water. The temporary
fixture command was used only to place the original subtypes in a stable review
world; it was removed after the save was produced. The retained run has:

- fifteen live `DrawVoxelDisaster` captures, including `sprite3905 shadow true`;
- an actual `smoke-state.sav` accepted by the normal synchronous save path;
- world atlas and tile-picking verification;
- nine recorded original console acknowledgements and the saved success text.

`native-vulkan/disaster-world.png` is the actual world view. The gallery images
are eight-view native exports from the same compiled catalogue. Source evidence
is under `source-sprites/`; the exact body/shadow source definitions are in
`body-models.json` and `shadow-models.json`.

## Review

All fifteen models are accepted at 9/10. The source silhouettes/palettes,
separate shadow state, body/rotor separation, both water-borne submarines and all
fifteen subtypes were observed in the saved world. The four original rotor
frames are not collapsed into one visually static source state even though the
rotor volume is shared; their frame identity remains the original sprite state.

Remaining non-disaster gates are tracked separately: natural HQ score-stage
selection, natural custom river source selection/absence/phase, LOD/picking and
ship clearance, sustained performance, and the independent release matrix.

# Unmodelled reference sprite closure

The title-world Vulkan capture now reports **zero unmodelled reference sprites**
in the reviewed view. The remaining sources were closed with real 3D geometry:

- `1406/1407` road overlays now use the same sloped terrain-surface mesh as
  other ground layers instead of a vertical reference plane.
- `6141–6144` road waypoints now select a 3D post/sign model at the waypoint
  tile, once per tile.
- Locks use the complete map-owned 3D wall family for both faces, including
  cases where upstream culling omits one source face callback.
- Toyland industry `144` completed state now selects the 3D blue finished
  factory model (`toy_factory_144_completed`), retaining stage 1/2 construction.

The final run loaded the actual title save in Vulkan, completed a synchronous
save, recorded eight original console acknowledgements and rendered with no
unmodelled-reference report. `world.png`, `run.log`, `result.json`,
`console-review.log` and the actual save are retained. `gallery.png`,
`source-1.png`/`source-2.png` and the factory review are under
`opentt3d/reviews/20261108/toy-factory-144/`.

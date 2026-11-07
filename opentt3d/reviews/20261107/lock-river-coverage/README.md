# Lock and river 3D coverage recovery

This review binds two recovered authored families and accepts the corrected lock
family at 9/10:

- 48 original lock-wall volumes, covering all three parts, four directions, two
  faces, two elevations and four climates (192 owner states). All 48 models and
  192 owner instances are accepted at 9/10.
- 8 river-relief volumes, covering four original slope bits and four climates
  (16 owner states). The 8 models and 192 conditional sloped-bank instances
  remain at 5/10.

The source is the previously retained, source-derived lock/river study set. No
geometry was inferred from pixels or sorting extents. The catalogue now contains
1971 models.

## Native evidence

Vulkan and OpenGL ran the original lock fixture in all four climates in the
background with `--record-console` and `--synchronous-save`. Each retained an
actual `smoke-state.sav`, ten ordered console acknowledgements and the exact
`Map successfully saved to 'smoke-state.sav'.` line. Across the eight runs the
live log observes all 48 original wall-ordinal owners, and the screenshots show
the corrected 3D walls in each climate. The corrected eight-view contact sheets
are in `lock-contact-sheets/`.

The river gallery exports all eight relief models (80 reference images) and
retains an acknowledged synchronous save. The fixture has no live custom
`CF_RIVER_SLOPE` selection, so this proves model loading, not active world
substitution.

The 112 original water surfaces and 13 native object ground surfaces are accepted
at 9/10 as intentional native surfaces, not as missing volumes. Their original
source bytes, ownership, anchors and climate restrictions are retained; the
all-climate lock and object views show them in place. No structural wall, dike or
relief score is inferred from this surface acceptance.

## Remaining limits

- River relief remains at 5/10 until individual source/orbit/street/world/state/
  consistency, picking, LOD, doubled-terrain support and ship-clearance reviews
  pass.
- 48 flat river banks, 20 river-ground selectors and 84 larger-HQ object rows
  remain explicit 1/10 fallback rows.
- Active custom river relief, complete original ownership/paint, all heights and
  neighbourhoods, custom families and sustained performance remain open.

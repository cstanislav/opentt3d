# OpenTT3D development preview: tropical lumbermill

The four tropical lumbermill tiles now have **12 provisional voxel volumes**, covering
every construction stage. The catalogue reaches **1,286 volumes**, with **58 industry
body definitions and62 independently owned grounds**.

## Artwork and source ownership

- Separate excavated sites, roofless construction shells and completed workshops.
- A continuous open loading canopy, two open chimney flues, inset workshop glazing
  and individual supported timber stacks.
- Original independent bare-soil ownership and only source-permitted middle-stage
  aliases. Source registration corrected the workshop footprint, roof direction and
  a construction operation that accidentally repainted its dark interior floor.
- A shared bare-soil palette correction removes three colours inherited from a
  different source sprite, benefiting existing industry bindings as well.

## Verification

- **200 native tests and121 asset/compiler/schema tests pass**; the unchanged
  nine-test harness retains its passing result.
- Both backends pass288 focused mesh/palette/picking views,2,424 industry state views
  and4,096,000 exact world-atlas RGBA/picking pixels each.
- Eight actual construction reviews verify all64 tile/stage/ground/body selections.
- A public-command wood truck loads20units, delivers to a tropical factory and returns;
  full/empty captures and the selected-engine pose matrix pass on both backends.
- All101 audited source-layer palettes match their originals. The64 compared normal-
  climate source pairs are identical. All14 final native runs pass, with a peak
  sampled footprint of **2,396,392,328bytes**.

Source-aligned, street-level and ordinary-world images were inspected. This remains
a breadth checkpoint with **zero final visual approvals**. Complete catalogue
coverage, detailed source-painted refinement, remaining climate artwork, sustained
smooth60fps and long-duration production verification remain unfinished.

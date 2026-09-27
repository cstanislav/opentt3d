# Toyland airports and boarding-pier repairs

Twelve provisional Toyland airport bodies bring the catalogue to **1,701 models**.
Terminals, towers, hangars and boarding piers now select their own climate-specific
paint while aprons retain independent ownership.

## Play

The **[verified `.23` desktop release](https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20260927.23)**
is available for Windows, macOS and Linux. This airport preview's packages appear
after its exact-commit workflow passes. Required graphics are bundled; see the
[installation guide](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md).

## Artwork and behavior

- Independent spatial painting covers original airport tiles 19–28, 43 and 47,
  including the rounded terminal's four separate teeth.
- Shared boarding structures receive corrected branch orientations, a mirrored
  elbow, a full-length raised link and supported clearance repairs.
- Both hangars retain open entrances with a recessed corner for the reviewed
  small-aircraft approach.
- Original aircraft availability, orders, animation, company colours, saves and
  simulation remain authoritative. Historical small-airport service uses 1958.

## Verification

The initial integration passes 60 background controls and seven missing/invalid-state
checks across OpenGL and Vulkan. It exercises all twelve live Toyland body selections,
independent grounds, original radar/flag animation, aircraft contact, Cab views,
rotated layouts, clipping, picking and application bundles. The native suite passes
206 tests; the repaired artwork passes 142 asset tests.

Clearance repairs pass 42 engine-248 terminal/exterior-approach placements, and all
five Toyland fixed-wing aircraft clear the revised pier-26 support at its original
stand. All 28 targeted integrated repair rechecks pass. Four additional 3,600-frame
Cab replays directly verify the original saved service's delayed release on both
renderers. All prior bindings and 1,683 preceding model hashes remain unchanged.

## Still in progress

Final visual approvals remain **zero**. Source-pixel fidelity, all-angle detail and
full moving-aircraft clearance remain unfinished. Wider static probes retain
large-aircraft hangar/fence intersections and an engine-251 terminal overlap. These
are open defects. Sustained arbitrary-world smooth 60fps and long-duration memory
acceptance also remain open.

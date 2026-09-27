# Asset review

Current reference: **OpenGFX2 Classic 0.8.1**, pinned in `upstream.json`, for UI and
every model category. The September 21 follow-up replaces the earlier HighDef
baseline; older review captures retain their original provenance.

## Cotton-candy129/130: four roots and original harvest state (September27)

- Source2072…2075 contains four growing pink crowns on cyan stems.2076 depicts four
  bare standing sticks in all four130 slots.2077 is independent blue/grey checker soil.
  Every one of48 non-native-climate/layer comparisons differs despite identical sprite
  numbers; the new cotton guard is owner-specific and precedes temperate acceptance.
- Six provisional volumes preserve those roots, all16 palettes and18 original aliases.
  The first all-state matrix passes but joined review catches nearly uniform pale crowns.
  Narrower painted highlights improve head separation without changing any occupied cell;
  mature pale168/169 coverage is54.5% versus48.6% in the source. Exact shoulders/tips,
  coral placement, grain and one-pixel registration remain open. Final approvals stay0.
- Both fresh9,000-frame backend observations capture the unchanged industry tile's
  mature129→harvested130→129 stages0/1/2/3. Real cargo loading, accepted delivery, empty
  return, construction and climate checks pass. Both joined layouts and street views are
  reviewed. Two of24 native captures differ by one pixel across backends; the full168-image
  comparison retains84 differing images/4,908 pixels. All original failures remain.
- Sweet-factory131…134 is the next gallery prototype: original gift wrapping and folded
  bow, partial unwrapping, round swirled roof, separate striped poles and recessed bays.
  The four131 bodies are intentionally empty. Distinct Toyland2022 ground has beige grain
  and red/purple/yellow patches; it cannot alias temperate soil. Battery135/136 and256
  additional Toyland procedural-child frames are separately inventoried.

## Diamond mine91…99: source cuts and upright hoist (September27)

- The3×3 mine retains21 empty body slots,10 distinct body volumes and16 new grounds.
  Ground2270/2279 is byte-identical; stages1/2 and the shared2022 soil aliases are
  preserved. Native Toyland soil2022 differs and retains its existing source guard.
- Original91 owns the upper hoist above the shelter drawn entirely in95's ground.
  A source sprite cut describes projected ownership rather than a vertical world
  column. The first column-clipped attempt leaned severely in street view; the
  corrected upright frame and backstays span the original owners without overlaps
  or detached cells. Both the incorrect revision and all preceding audit failures
  remain available in `build-macos/breadth-diamond-*`.
- All four native joined construction stages and four street views are reviewed.
  The26 new volumes are provisional: rock faceting/grain and per-cut height, office
  and raised-platform detail, rail height and exact registration need later passes.
  Original joined192×95 bounds compare with192×97 initial/192×99 later models.
  The359-image backend audit retains88 differing images/9,796 pixels, including one
  tile92 paint pixel in an otherwise matching55-view native registration set.
  Final visual approvals remain zero.
- The next cotton-candy129/130 source uses four growing pink crowns on cyan stems,
  four bare standing sticks after harvest and a separate blue/grey checker ground.
  Its2072…2077 IDs share numbers with the temperate forest but all48 cross-climate
  layer comparisons differ. The prepared ordinary cargo route succeeds in732 ticks.

## Shopping-mall source ownership and joined review (September25)

- Houses40…43 use original4406…4417; source-identical0/1 and2/3 states are preserved.
  Ground43 owns its entire pavilion, and early41/42 have no body sprite. The twelve
  authored volumes follow those original layers rather than inventing a body.
- `pass1-mall-first-review` exposes disconnected pyramids and broken footing joins.
  `pass1-mall-source-shading` has connected L-shaped wings, separate front pavilion,
  recessed entrances, full32×32-world footprint and source blue/gold/brick/flower
  colours. Cross-tile/contact and native/Linux rendering checks pass their scopes.
  Registered source widths/intersections, roof/glazing/paint and one/two-pixel framing
  differences remain WIP. These findings are not final approval.
- Next source sheets44…47 in `pass1-stadium-indexed-source/renderer3d-reference`
  show two-storey ochre flats and one-storey red houses, source-identical construction
  pairs, genuine open rafters and separate completed snow bodies/grounds. Preserve
  actual era/climate availability and state2 versus stage3 ground differences.

## Historical source breakdown: cable-supported offices36 (now voxel-bound)

- `pass1-stadium-indexed-source/renderer3d-reference/house-036-all-states-layers.png`
  and its16 original manifest records show a distinctive suspended glass cylinder
  between two tall yellow masts, with real braces/cables and clearance beneath it.
  A generic solid office tower would lose the defining structure.
- The first body is genuinely absent. Stages1/2 share1563's two bare masts;
  stage3 uses1565's glazed cylinder and connecting members while retaining the masts.
  Ground selection is independent:3924 soil,1562 early concrete and1564 final concrete/
  base detail. The full16×16 tile and original source placement remain the contract.
- All four variants use the same sprite/palette pairs. The12 nonempty body exports
  agree across temperate, Arctic and tropical sources,58,608 native RGBA pixels per
  comparison. Both later concrete grounds also agree,3,968 pixels per comparison.
  Reports are `house36-climate-comparison.json` and
  `house36-ground-climate-comparison.json` in
  `pass1-city-house-tropic-sources` and `pass1-next-house-arctic-sources`. The latter
  reloads the actual Arctic fleet and checks food156's real climate binding2.
  Matching sprite IDs alone are not used as proof of climate equality.
- The decoded body canvas is37×132 native pixels, with original(-18,-108) native
  offset; manifest dimensions/offsets are in the upstream4× coordinate convention.
  Contact-sheet panels fit tall and empty states independently, so apparent panel
  scale must not be used to infer a changed footprint.
- `src/table/town_land.h` makes this house available from2000 in temperate, tropical
  and below-snow Arctic town-centre/inner-suburb zones. An ordinary2000+ world is
  needed for construction/live review. Next families37/38 are below/above-snow Arctic
  houses available only through1960;39 is the temperate cinema from1945;40…43 form a
  joined2×2 temperate shopping mall from1983. Preserve these distinct era, climate,
  source-layer and joined-footprint requirements when continuing basic coverage.

## Classic material and geometry corrections

- Normal-resolution source pixels are the highest world-material detail level;
  the atlas excludes duplicated upscaled levels. Native source exports were refreshed
  in `build-macos/classic-world-first/renderer3d-reference`.
- Clear turf/rough ground maps one complete clean substrate tile, replacing the
  small crop repeated 8×8 times. Bark, foliage and raised surface details target
  approximately two native texels per physical world unit, including growth/LOD.
- Inspected Classic grass/rough/diagonal-rail and bridge turntables, overhead and
  underpass views, and actual bus Cab captures. Bridge slabs are 0.5 height units;
  pillar caps stop inside them. A stretched underside strip was found during review
  and replaced with a clean edge-material sample.
- Every rail system now uses straight diagonal chords. Mitered end sections preserve
  the gauge across tile boundaries; sleepers retain approximately uniform spacing.
- Passing Classic checks include all four climates, all tree lifecycle/LOD/palette
  views, vehicles, industries, raised ground, rails and bridges. These establish
  this material/geometry correction; broader individual-model approval remains open.

The newer active objective requires **all world assets to be voxel-based**, including
tracks, airports and existing models. This supersedes the earlier hybrid-authoring
recommendation. The first authored cell-volume pipeline and three mature house
bindings now exist; see `VOXEL_REVIEW.md` for their findings and the complete-scope
queue. No voxel model has final visual approval.

## Current sources and evidence

- `assets/3d/houses.json`: initial profiles covering 110 house IDs, including aliases.
- `assets/3d/trees.json`: 62 component-backed sprite families, including snow aliases;
  separate authored wood/foliage, bark charts, lifecycle materials and three LODs.
- `assets/3d/vehicles.json`: initial volume assemblies and explicit bindings for
  all 256 vanilla vehicle definitions; inheritance shares actual component geometry.
- `assets/3d/industries.json`: initial mature profiles for 40 mine, power-station,
  refinery, offshore, farm, factory, steelworks and sawmill tile definitions.
- `tools/assets/inventory.py`: 256 vehicle definitions/bindings, 110 house definitions,
  62 tree families and 175 industry tile definitions (40 with initial profiles).
- `renderer3d references`: exports the sprites actually resolved by the game,
  including house variants/construction stages and tree palettes/stages.
- `renderer3d gallery <id>`: renders an authored house or tree from four rotations.
- `renderer3d vehicle-references` / `vehicle-gallery <engine> [loaded]`: source
  references and four-view vehicle galleries. Use a world in the engine's climate;
  sprite slots for unavailable vehicles can be repurposed by the base set.
- `renderer3d industry-references`: exports all 700 default industry tile/stage
  records, with sprite, palette, placement and special-animation procedure metadata.
- `src/renderer3d/bridge_geometry.hpp`: explicitly constructed decks, posts,
  trusses, cables, arches and sloped/flat heads for the 13 vanilla bridge types.
- `renderer3d bridge-references` / `bridge-gallery <type>`: upstream-resolved
  sprite/palette/offset/size records and four-angle assembly galleries.
- `renderer3d bridge-locate`: frames an existing live bridge without altering the map.
- `src/renderer3d/terrain_geometry.hpp`: terrain-following fence volumes and complete
  exposed foundation walls, with component-local and repeating wall material charts.
- `renderer3d terrain-references`, `fence-gallery <style> <slope>` and
  `foundation-gallery <slope> <foundation>` provide resolved references and turntables.
- `tools/assets/contact_sheet.py`: review sheets, model galleries and image previews.
- `src/renderer3d/tunnel_geometry.hpp`: authored portals and continuous interiors for
  rail, electric rail, monorail, maglev, road and tram. `tunnel-gallery <kind> <direction>`
  exports exterior turntables plus approaching/interior/exiting Cab views.
- `src/renderer3d/rail_geometry.hpp`: authored six-route rails, sleepers, monorail beams
  and maglev channels. `rail-gallery <type> <track-bits> <slope>` uses upstream legal
  foundation choices, including split-level layouts. Surface/tunnel tracks share meshes.
- `src/renderer3d/station_geometry.hpp`: explicit platform/furniture/building/paired-roof
  components for all eight default train-station layouts. `station-references`,
  `station-gallery <railtype> <layout>` and `station-locate` support review.
- `src/renderer3d/ground_detail_geometry.hpp`: nine farmland states, two rock materials,
  bound bale stacks and snow caps. `ground-detail-gallery <kind> <variant> <slope>`
  and `ground-detail-locate <kind> <variant>` cover fields (0), rocks (1), snowy rocks (2).
- `src/renderer3d/rail_detail_geometry.hpp`: six signal types, light/semaphore states,
  contact/messenger wires, droppers and masts. `rail-detail-references` exports 228
  sources; `signal-gallery <type> <variant> <state>` and `catenary-gallery <track> <grade>`
  export turntables. All twelve signal families and six wire routes received an
  initial manual gallery pass. Rounded housings, physical lenses, mechanism/plate
  proportions, auxiliary lamp states and station roof hangers were refined afterward.
- `tools/opentt3d/fixtures/rail/`: public-NoAI construction and observed train journey
  for live bridge/tunnel/station/depot/crossing/road-stop and vegetation review.
- `src/renderer3d/depot_geometry.hpp`: six authored maintenance-shed families,
  separate roof/wall/trim charts, open bays and internal track ends. All first
  family galleries were inspected, followed by material/structural refinements.
  Road roof crop (50…54,74…78) excludes frame paint; tram roof uses the actual dark
  fallback texel (50,118), retaining nearest sampling rather than stretching braces.
- `src/renderer3d/crossing_geometry.hpp`: four railway crossing systems, real warning
  lamps and maglev gate state, optional tram inlays and recessed running profiles.
  Open/barred family galleries and live traffic views were inspected; asphalt grain
  was reduced from oversized repeating blocks to a finer authored scale.
- `infrastructure-references`, `depot-gallery <kind> <direction>`,
  `crossing-gallery <kind> <axis> <barred>`, and the matching `*-locate` commands
  support repeat review. These initial passes do not approve all climate/material details.
- `src/renderer3d/road_stop_geometry.hpp`: bus/truck bay and drive-through shelters,
  seating, signage, curbs, offices/loading bays, fences and tram inlays. All 44 source
  components and four primary family turntables were inspected, followed by actual
  Cab review. `road-stop-gallery <kind> <layout>`, `road-stop-locate` and
  `verify-road-stops` support later passes. Kind 0 is bus, 1 is truck; layouts 0…3
  are bay directions and 4/5 are drive-through X/Y.
- Generated `model-*.pam` review captures may be compacted with
  `tools/assets/compact_reviews.py` in the art container with explicit completed-run
  evidence, for example `build-macos --validation-manifest
  build-macos/pass1-industry-climate-scoped-validation.json --apply`. Only runs with
  integer `exit_code: 0` qualify; failures override conflicting success records,
  incomplete records are rejected, and linked/outside review paths are excluded.
  Without manifests the preview selects no images. Each PNG retains the exact
  pixels and PAM header; source references remain PAM. `contact_sheet.py --gallery`
  supports both formats and prefers a newly exported PAM over an older PNG.
- `clear_surface_geometry.hpp` adds natural turf blades/pebbles, rough-ground
  hummocks and Toyland pips. Grass density and the five upstream rough layouts are
  retained; clean, toned source grain replaces the painted raised detail beneath
  them. New gallery kinds are 3 (grass density 0…3) and 4 (rough layout 0…4), with
  additional near-ground views. Snow/desert and shoreline microdetail remain work.

The sources remain marked `work-in-progress`. The inventory reports **zero
visually approved tree families**; profile presence is not approval of all states.
Vehicle bindings are likewise **not visually approved**. Native GPU checks cover
7,520 direction/cargo poses across the four climates, establishing visibility and
picking rather than finished visual fidelity.

## Corrections made during renderer integration

- Individually reviewed every mature tree family and selected growing/dying/dead
  frames. Replaced projected trunk/crown artwork with repeating leaf patches and
  separately charted tapered branches. Bark follows branch bends; snowy aliases
  use the snow source. Toyland components preserve upstream recolouring.
- Restored authored proportions independently of stray sprite pixels. Corrected
  birch stages 1…5 and the green Alpine crop after actual enlarged-source inspection.
  Replaced pinched cylindrical foliage mapping with physical-unit component charts.
- Palm fronds have solid midribs/leaflets, agaves have folded blades/undersides,
  cactus arms have joined tube frames, and Toyland ribs/bands/spots have independent
  materials. Review found white rib paint on parasol fabric and green pixels in blue
  gores; clean source crops and independent mushroom spots correct those artifacts.
- Register curved models using their actual projected vertices, not the projected
  corners of an axis-aligned box. A crown does not reach those box corners.
- Use the selected state geometry's bounds when registering bare branches.
- Exclude isolated edge texels from registration bounds and padding seeds. The
  grown birch sprite (`1600`) has a detached pixel at `(0,0)` above its real crown;
  treating it as part of the crown stretched the model and spread its colour over
  the padding. Original source pixels and genuine one-pixel sprites are retained.
- Keep visible reference-facing curved facets unmirrored; only back-facing
  surfaces receive rear-facade UV transforms.
- Transform normals correctly under separate horizontal/vertical scaling.
- Keep opaque-texture edge handling distinct from company-colour material flags.
- Preserve the source alpha gaps of dying tree canopies; opaque texture dilation
  previously filled the deliberately missing leaves with solid colour.
- Preserve alpha gaps in construction-stage house materials instead of filling
  scaffolding and incomplete walls with neighbouring texels.
- Replace supported vanilla vehicle body planes with directional volume geometry;
  preserve live resolved sprites, company/crash palettes, cargo state and rear-head
  orientation. Smooth renderer-only positions/headings once per draw frame.
- Draw aircraft shadows/rotors horizontally and effects camera-facing. Shadow
  materials darken the scene and do not intercept picking.
- Register vehicle UVs with a consistent horizontal projection rather than
  independently stretching both image axes. Sprite-local integer atlas sampling
  fixes relocation-dependent nearest-texel rounding found by the Mesa checks.

## Outstanding fidelity work

- Industry tiles **8,33,39,43,49** have first individual component passes: separate
  masonry/roof charts, independent glazing and flues, and corrected missing stacks.
  Source photos and turntables were inspected. Repetition, window/frame detail,
  accurate proportions, multi-tile joins, construction and subsequent close-up
  passes remain. `material_review` notes identify selected crops; they are not
  approval flags. The other industry/house/tree/vehicle models still need the same
  individual treatment. The reproduced power-station roof-chimney duplication is
  removed in `power-station-pitched-opengl`; farmhouse gable contamination is
  corrected in `farmhouse-clean-roofs`.
- Farmland/rocks: every field source and first family gallery was inspected.
  Mature density, canopy source charts, furrow contrast and fallback-rock soil
  contamination were corrected. Hay and rock paint is no longer underneath the
  new models. Row regularity, straw/leaf shape and density, repeated small charts,
  rock silhouette variety, snow-cap shape, LOD transitions and all climate/growth
  states need further passes. Ordinary grass and rough tiles still contain small
  painted stones/blades, especially in Arctic references; those remain work.
- Stations: all three architecture families have building/hall turntables and a
  live station review. A second pass corrected stretched roof patches, added brick
  arches and gave the clock gable actual depth. Pavement/brick repetition, ornate
  source details, monorail office shape, maglev framing, hall end caps and entrances,
  transparent ordering, climate materials and longer train-Cab passes still need
  refinement. The 128 GPU views and company-paint checks are technical evidence.
- Tunnels: all six family galleries and actual Cab passage have been inspected.
  Separate asphalt and lane-paint charts removed outdoor grass strips inside road/tram
  bores. The small repeated patch is still visibly periodic; refine it, masonry,
  portal joins, lamps and lining detail. Test all climates and moving entry/exit cases.
- Rails: normal/electric, monorail and maglev sections plus steep two-level layouts
  have first-pass galleries. Crossing guide walls were found blocking maglev running
  routes and are now cut back. Ordinary rail frogs, switch blades, sleeper overlaps,
  monorail ballast colour, material detail and all station/depot/bridge/road-crossing
  joins remain. The 8,208 GPU views establish coverage, not final visual approval.
- Far fence variants retain volume posts/rails and reduce unresolved diamond-wire
  and crown detail. Review transition visibility during actual orbit/zoom motion;
  close models remain unchanged.
- Fences: all seven families have been inspected in four-angle galleries. The first
  pass exposed gate paint on hedge end-caps and inconsistent rail-post colours;
  separate materials correct those. Foliage silhouette/detail, individual capstones,
  tile-boundary joins, railway half-tile fences and close-view wire LOD need later passes.
- Foundations: leveled, internal half-tile and two-level galleries have been inspected.
  Retaining walls are now geometry in every exposed direction. Review real building,
  station, bridge and road joins, water-facing boundaries, material seams and every climate.
- Natural clear/tree ground now has independently modeled turf/pebbles over a clean
  substrate; all five rough layouts and all climate source sets received review.
  Refine density, small-rock outlines, subtle hummock transitions and substrate
  periodicity. Other ground artwork, including snow/desert and shoreline borders,
  still contains directional painted microdetail and needs the same treatment.

- Trees now have a first individual material/gallery pass across all 62 families.
  Refine regular crown lobes, foliage periodicity, sparse-state topology, palm density,
  tiny twig/root proportions, snow coverage and moving LOD transitions. Some withering
  crops still need tighter separation from painted twigs. Growing trees use authored
  scale sequences rather than fully separate juvenile topology. The 5,544 GPU views
  prove technical state/material coverage, not these remaining visual requirements.
- Toyland umbrella undersides/interior framing, smooth profile transitions, source
  lighting balance and later close-up passes remain. The current gores are solid
  component volumes; they are not yet complete thin-shell umbrella construction.
- Review every house variant and construction stage. Thin foundation boxes and
  rescaled mature topology are insufficient for scaffolding and partially built
  structures. Check multi-tile placement and rear surfaces separately.
- Refine each vehicle silhouette and component UV layout. Current galleries still
  show stretched/overlapping paint on ship decks, superstructures and aircraft
  surfaces. Wheels, running gear, rail-system variants, aircraft-specific shapes
  and full animation/crash review remain. Shared basic assemblies are not final approval.
- Complete industry/infrastructure geometry and the infrastructure/effect
  catalogues, then replace the remaining temporary vanilla reference planes.
- The cooling-tower diagonal seam was corrected with artist-selected source crops
  and continuous circumference mapping, separating wall, rim and interior.
  `build-macos/cooling-tower-authored-materials/` contains the corrected gallery.
  Its support spacing, texture density and construction stages still need review.
  Mine headframes need pulley/beam detail and component-specific materials;
  `industry-mine-head/` remains a work-in-progress gallery.
- All 160 current industry four-angle views pass GPU visibility/material checks.
  This is technical coverage, not approval of geometry detail, special animation
  procedures, foundations, construction states or multi-tile joins.
- Bridge technical checks cover 832 assembly views across rail, road, monorail,
  maglev, both axes and flat/sloped heads. Half-pillar crops select complete
  physical columns instead of cutting their rear surfaces with a 2D rectangle.
  These checks are not visual approval. Component proportions, stretched edge
  materials, coincident internal joins, tubular mesh detail, aqueduct fixtures,
  catenary and custom-layout handling remain unfinished.
- Validate palette/company colours, snow, animation, transparency and mod
  provenance against representative fixtures before setting review flags.

Current review artifacts are under ignored build directories, including
`build-macos/highdef-rounded-models/renderer3d-reference/gallery.png` and
`build-macos/highdef-birch-corrected/renderer3d-reference/gallery.png`, plus
`build-macos/highdef-tree-references/renderer3d-reference/trees-000-s{0,3,6}.png`.

# Voxel recreation ledger

The full objective and minimum work window are in `ACTIVE_GOAL.md`. Every world
asset must ultimately be voxel-based, including existing models, every rail system,
airports, effects and all relevant states. **No voxel model is visually approved.**
Technical visibility and meshing checks are necessary but do not establish faithful,
production-quality recreation.

Earlier `voxel-final-depot-cab-{vulkan,opengl}-6000` sky-coloured ground lines were
reproduced and corrected for the reviewed contacts: base heights and raster edge
samples now agree. Later `voxel-extension-final-cab-{vulkan,opengl}-6000` screenshots
and24 flat/ramp/large-origin coverage views were reviewed. Original failures remain;
full terrain/source-raster fidelity and final approval remain separate.

## Authoring and rendering

- **Expanded industry climate audit:**323 layer pairs across623,286 original RGBA
  pixels find153 differences:15 coal-ground,16 power-ground,16 forest body/ground,
  36 refinery-ground,30 oil-well-ground and40 farm pairs. All107 compared coal/
  power/refinery/oil-well body pairs match exactly, as do all32 Arctic/tropical
  food pairs. Arctic forest16/17 replaces every body/ground slot with snowy artwork;
  soil3924 and oil-well2173 also change across climates. Current matching volumes
  for these differing layers are temperate-only. Runtime retains supplied climate
  ground while keeping an unchanged voxel body independently; forest/farm body
  replacements retain supplied artwork as well. Missing variants remain catalogue
  work. Evidence: `pass1-industry-cross-climate-source-audit.json` and
  `pass1-industry-climate-differences-source-sheet.png`.
- **Arctic farm source-selection repair:**40/44 farm33…38 source layers differ from
  temperate (78,129 compared pixels). The Arctic farmhouse is structurally distinct,
  and its roof/door/shelter colours also differ. Current volumes remain temperate-
  only. Source artwork is retained for unauthored climates, including both ground
  and body; the old legacy profiles cannot silently substitute either. The eight
  prior Arctic selection runs exposed the invalid alias and are retained as failed
  fidelity evidence. Author independent Arctic structures/grounds before restoring
  their voxel bindings. Evidence: `pass1-farm-climate-source-comparison.json` and
  `pass1-farm-climate-source-review.png`.
- **Reviewed industry breadth:** oil-well29…32, farm33…38, paper64…71 and
  plantations116/117 have focused hiddenGL/Vulkan mesh/selection/atlas checks and
  source-registered/street sheets. Public grain/livestock, wood-to-paper, fruit and
  rubber routes complete actual loading/delivery/return. The registered review
  corrects oil-well origins, farm gable/roof axes, paper chimney/shelter placement
  and plantation root/crown spacing. Refreshed paper/plantationGL/Vulkan renders now
  pass and their registered whole-layout/street sheets are inspected. Fine shape/
  paint differences remain open; no final approvals.
- Ten provisional waterworks volumes cover118…120 with independent full tropical
  desert4550 ground, open/braced steel stands, raised blue tanks/white pipe loops,
  low grey vessels, tilted solar panels and the town water tower's real open
  construction cylinder. Identical stages1/2 share only source-identical artwork.
  The water-tower roof closes only on completion. Tropical source imagery and
  palettes were exported in an actual tropical graphics set; the shared4550 number
  does not alias Arctic snow. Ground/contact/palette/state tests and both backend
  gallery/industry/atlas matrices pass; source and street sheets are inspected.
  All waterworks actual construction slots pass in the two-backend sweep.
- Twelve food-processing volumes preserve60…63's initial, open intermediate and
  completed states, independent2022 grounds and open silo with inset grain. Source
  exports prove Arctic/tropical body/ground layers identical across76,416 RGBA pixels.
  Both backend galleries and registered joined/street review pass technical checks.
  Four bank volumes add58/59's finished bodies in every construction slot, independent
  initial2022 grounds and completed2182/2183 paving. Cupola/roof/colonnade ownership is
  partitioned across the two original tiles and the entry is physically open.
- Later-pass findings from refreshed sheets: paper roof/brick grain and chimney
  colour bands, banana frond silhouette/branch openness, rubber crown asymmetry,
  waterworks brace thickness/tank curvature/pipe fittings, food hall rib and window
  spacing plus yard grain, pump head/beam profiles, and bank cupola drum/windows,
  arched detail/roof heights and masonry/glass shading need source-painted refinement.
  Native bounds remain recorded in each source-registration sidecar; they are not
  dimensional or visual approvals.
- The waterworks support cages have real open cells, but four coarse cross-braced
  faces overlap into a nearly solid silhouette from some source/street angles.
  The tower's leg/tank proportions and narrow lattice apertures need a finer
  explicitly authored support grid; generic occupied-cell speckling is not a
  substitute for open structure. Source and street sheets retain this finding.
- The next provisional airport family recreates the low2095 L-plan terminal on
  tiles63/64/69, with original2663/2664 fence ownership and separate complete2634
  apron. Source-native placement was inspected manually; no geometry is generated
  from imagery. Its1,247-volume freeze passes117 asset/196 native tests and both
  rendered source/context/ground-transparency reviews. All27 climate-source layer
  pairs match. The first render exposed side windows overwritten by perpendicular
  pier brushes; the corrected brushes pass refreshedGL/Vulkan and street review.
  Roof-gravel grain, glazing/piers, plinth brightness and ground raster remain later
  source-fidelity findings. Actual63/64/69 selections pass on both backends.
- Exact paired-backend review retains23/102 differing bank images (1,942 pixels)
  and14/83 differing corrected-airport images (1,605 pixels). Both families pass
  their own backend's CPU/reference comparisons; cross-backend equality remains
  unproven. Detailed evidence is `pass1-bank-airport-backend-summary.json` and its
  complete per-image reports.

- **Oil-rig published candidate, not visually approved:** graphics24 remains body-empty and
  25 stays empty until its completed flare. Four initial pilings/paired braces are
  followed by the joined deck, three-storey accommodation and service block; only
  the completed state erects the derrick and flare. A full six-tile native export
  and tile-origin sidecars now support registered joined-source comparisons. The
  reviewed264 mesh/1,616 industry-state views pass onGL andVulkan; all20 actual
  construction selections and converted-neutral-station water ownership pass.
  The source's54-unit helipad datum is retained:40 actual helicopter253 support
  corners lie on captured deck triangles, and all four original rotor states plus
  restart are observed on both backends. Helicopter254 now also passes120 actual
  support corners, every rotor state and restart onGL/Vulkan. Broader swept rotor
  clearance and water/light animation observations remain open.
- Oil-rig later-pass findings: the service block's plan/proportions, intermediate
  platform heights and stepped walkway/well joins, cylinder ribs/paint, cabin window
  framing/recesses, derrick section widths, roof grain, rail-post spacing and the
  flame's narrow side silhouette need source-painted fidelity review. The first
  draft's premature construction frames and blue flare girder were corrected as
  source/state defects. Source sprite cuts are not treated as physical tile walls;
  shared authored components retain exclusive body ownership across the joined rig.

- Editable source: `assets/3d/voxels.json`; compiler: `tools/assets/compile_voxels.py`.
- Explicit cell operations: boxes, occupied-cell paint, erasure, repeated authored
  components, bounded ellipsoids, stepped gables/hips, hollow barrel roofs/end fills, reusable named parts,
  baked Z rotations, inheritance, material replacement, deterministic occupied-cell
  speckling, explicit hollow radial profiles/inward-face painting, authored transverse
  hull sections/deck-face coating and XY transposition. No geometry
  is inferred from images.
- Common grid: **0.5 × 0.5 ground units × 1 height unit**. Palette materials specify
  the six face colours in `-X,+X,-Y,+Y,-Z,+Z` order using actual Classic/DOS indices.
  Thin running tracks use a **0.25 × 0.25 × 0.125** transport subgrid; ballast colour
  cells retain half-unit spacing. This needs continued cross-category scale review.
  Radar lattice arrays use a **0.25 × 0.25 × 1** detail grid so their thin bars and
  apertures survive every turn. Rotations bake back into axis-aligned cells, using
  positive-area cell intersections and deterministic nearest-source material choice.
  Per-model cell size is explicit and inherited; changing it silently is rejected.
- Hidden occupied-to-occupied faces are removed, including between different
  materials. Coplanar equal-colour regions merge. Shared edge cuts prevent raster
  T-junctions; actual colour/crease edges retain every unit vertex for stable subpixel
   coverage. Thin rectangles and unit strips beside colour borders and silhouette edges
  keep cell-reference diagonals; larger interiors still merge. Convex ear clipping
  retains the remaining boundary points without centre fans.
  Independently requested material partitions keep their unit boundary topology.
  The reference contact substrate retains its earlier triangulation. Material
  partitions query the complete volume, with face scans limited to occupied bounds.
- Palette indices are flat face data, never interpolated colour/UV indices. Original
  palette recolouring/animation remains available through a relocatable palette strip.
  Voxel faces use authored palette shading and outward-face culling.
- `renderer3d voxel-gallery` / `smoke.py --gallery-voxels` exports individual
  four orbit and four actual six-unit-eye street views, mixed context and paginated
  per-category neighbour scenes. Taller groups are framed without changing the lens.
  Use `contact_sheet.py <directory> --gallery --voxel-model <name> --street` for the
  street sheet, or `--voxel-model context-airport_tiles-0` for an airport context page.
  Actual live review also uses `--reference-model`, `--reference-airport` and gameplay captures.
- `tools/assets/palette_reference.py` and source preview colour listings support
  deliberate palette selection. The first window palette was wrong and was corrected
  against the actual source colours (indices 128…133).

## Current checkpoint: September26, 1,169-volume candidate

All110 house definitions have body or ground bindings (109 body/88 ground definitions),
and all62 original tree families have434 lifecycle volumes. Vehicles now cover256/256,
industry bodies21/175, industry grounds24, airports18/74 and depot families5/6. Exact
counts are in `build-macos/pass1-1169-final-inventory.json`.
All volumes remain work-in-progress and final approvals remain zero.

Thirty-eight new locomotive volumes bind the remaining33 definitions. Native source
and street comparisons preserve steam cab openings, spoked wheels/coupling rods,
banded boilers, stepped diesel hoods, passenger windows, radiator banks, open roof
collectors and distinct monorail/maglev noses. Seven Arctic/tropical engine pairs
have independent geometry; Toyland eyes/red lamps remain separate. Shape/paint
differences include flat uniform surfaces, weak boiler shadows, short passenger
window bands, simplified nose/roof contours and inconsistent side/end heights.

**Repaired structural finding:** the existing tunnel vault is below one8-unit
terrain level, while several old/new train bodies reach9…10.75units. The saved
analytic audit finds91 empty engine/climate cases /64 unique models exceeding the
arch. Selected train Z grids now preserve running support and XY footprints while
clearing the actual faceted arch plus inward ribs. The three independent collector
volumes keep their roof mounts fixed and follow individual wire samples, lowering to
7.55units before the tunnel arch. All train empty/loaded bindings and joined collector
poses pass both native backends. Eight live collector runs observe real surface,
portal and tunnel transitions. Slope/curve wheel contact and complete contextual
clearance remain active. A preserved1,130 control retains pre-correction source/runtime.

The Linux title-world tunnel check additionally found a tree's below-ground root
covering640 lining pixels. That exact failure reproduces natively. Tree instances
now use finite bore subtraction with their own tile-relative offset, preserving the
above-ground crown and roots outside the current segment. Both native backends pass
the original saved-world Cab review with243,635 unobstructed lining pixels. Linux
Vulkan CI36228046438 now passes243,629 unobstructed lining pixels and unchanged vehicle
state; its later full catalogue matrix still exceeds the6GiB guard.

Eleven sawmill volumes add original11…15: separate low foundations, open timber
frames, three northlight/cutting-shed roofs, a monitor-roof store, cutting table and
worker, round log piles and individually supported board stacks. Original14/15
stages0…2 remain empty, and original3924 soil is independently bound in all states.
The source/street review corrected the northlight/store axes, entry sides, foundation
width, log direction, board-stack height and dark interior substrate. Tests require
every disconnected physical part to reach ground and every state to use its source
palette. Both native backends pass264 mesh views/840 industry views; all20 actual
state selections pass. Corrugation shading, timber grain, pile profile/end-grain and
small saw/worker details remain queued for the later catalogue-wide fidelity pass.

Six forest volumes add four nine-pine growth states, original2076 logs/stumps and
independent litter. Rooted-geometry checks, source palettes and both native mesh/industry
matrices pass. The log profiles are octagonal with painted end cores and retained bark
rims. Real wood service loads20units in engine144, delivers to a sawmill and returns.
Both9,000-frame native backend observations follow one unchanged tile53,35 /industry0
through mature16→completed17→16 stages0/1/2/3. The earlier6,000-frame attempts end before
maturity and remain failed evidence. Construction17/stage0 was an incorrect observer
assumption; the source simulation leaves17 completed at stage3.

Nineteen refinery volumes add18…23 with all24 actual construction body/ground selections.
Reviewed source registrations and street galleries preserve hollow steel cylinders,
separate blue bands/pipes, grounded open frames, three flare platforms, cooler and
L-shaped office. A fixed80-pixel native-export top crop hid the flame; adaptive crops
and explicit tile-origin sidecars now retain its full108-pixel silhouette against the
109-pixel source. No geometry is inferred from these images.

The source/street pass records remaining refinements: tank hatch/ladder placement,
foundation/post heights, cylinder radial shading and curved-top grain, fractionator
band/hatch detail, process pipe widths/brace offsets, cooler pipe arrangement, office
rear-wall material and fine window/roof detail. The flare has a solid narrow extruded
flame whose side profile needs broader volumetric shaping. Forest crown tiers, bark
grain and log-end shading need further fidelity work. These are not final approvals.

The61 new wagon volumes bind the remaining54 wagon definitions, completing81/81
bindings. Manual source inspection distinguishes Arctic brown coal tubs, tropical
grain lower bands, timber stake counts/log colours, paper canopies, copper hoppers,
water fillers, fruit and liquid latex. Separate Toyland states6/7 preserve eight
families, including open bubble outlines and cola tank frames, three upright solid
batteries/drink cans/plastic masses, and independent sugar/candyfloss/toffee cargo.
Toyland rail aliases match256 original directional/cargo views /67,780 RGBA pixels.
Regressions require one face-connected body/load, support at the running-rail plane,
genuinely empty beds, steel through-bores and source-permitted cargo/rail aliases.

Forty ordinary and sixteen Toyland eight-direction comparison sheets show recognizable
families but still differ in diagonal lengths, front/rear heights, overly uniform/
bright wall and cargo paint, rib width, log end-grain, filler/canopy shapes and coil
shading. Street sheets retain raised-canopy gaps, actual coil holes and open tank/
bubble structures, while their finer source proportions remain WIP. Twelve saved
consists capture all69 new engine/climate combinations; real coal loading/delivery
and full/empty saved renderer checks pass. Complete slope/curve/depot/platform/Cab
clearance, other cargo services and final source-pixel fidelity remain unproven.

Seventeen new aircraft volumes cover the33 ordinary fixed-wing definitions215…247
together with the existing Dinger100. Original eight-direction/cargo signatures
justify aliases within this climate. Each body is face-connected to its landing
gear. Public NoAI fixtures observe all24 early and nine late aircraft moving and
servicing the destination airport; their ordinary save files reload for renderer
review. NativeGL andVulkan each pass432 all-model views and35,904 vehicle poses plus
exact world-atlas checks, below6GiB. All33 live-engine captures pass, peaking at
3,729,510,072bytes under the6GiB guard.

Native comparisons show remaining broad/triangular late wings, excessive nose/rear
perspective heights, overly bright white tops, uniform side shading, absent small
windows and oversized Dinger1000 diagonals. Source-led corrections already narrow
the propeller wings, replace stair-step early fins with authored voxel prisms and
shorten the Haugan delta's aft spread. Street sheets preserve the K6's real wing
gap and Dinger200's dorsal arch opening. These are breadth-stage models, not source-
pixel or all-airport-clearance acceptance. Toyland replaces the graphics behind
overlapping sprite IDs; five additional plane bodies and three helicopter bodies
now preserve those independent source families. Four separate rotor volumes follow
the original3901..3904 state selection, with identical source RGBA across normal and
Toyland exports. Normal aircraft also match1,477,364 original RGBA pixels across
the Arctic/tropical versus temperate directional/cargo exports.

The stricter single-component aircraft test caught detached nose-wheel struts on
AirTaxi34/Kelling7, plus two new-family support gaps; all are repaired. Kelling6 and
the separately detailed Juggerplane have explicit swept crescent wings and connected
interplane struts. The airport simulation's anchor sits one height unit above its
landing surface; world capture now subtracts that offset from body and rotor together.
All three helicopters pass actual ground-contact and four-state stopped-to-running
observations in held-service NoAI saves, plus128 joined rotor poses per engine.

Eight-direction body and joined-rotor registration sheets retain oversized front/rear
silhouettes, triangular wing chords, tall T-tails, flat helicopter cabins, short skid
clearance, broad glass/nose patches, source-anchor discrepancies and sparse small-window
painting. Forty-eight joined street views show distinct rotor poses and open skids,
but require later proportion/paint refinement. Stopped blades still alias in distant
native captures. Final visual approvals remain zero.

The315 new tree states include105 temperate,112 Arctic/snow and98 tropical states.
Connected-root and snow-occupancy/face regressions pass. Native source review identifies
wide young fir crowns, insufficient bare-branch spread, over-regular crown tiers,
overly solid palm fans and stage-specific palette/shading discrepancies. Those still
need source-led corrections before Pass1 acceptance, alongside the complete actual-state
and street/Cab/climate review. The snow-facing error, detached branches, incorrect dead
succulent brown ramp and clipped tall comparison sheets are corrected.

The complete1926…1932 peach-palm sheet subsequently exposes a reversed bent-stem
axis: its root is drawn left of the crown instead of the source's right. All seven
states now transposeXY so the foot extends along positiveY. A root-axis regression
and fresh exact/live/native comparison cover this immediate placement correction.

All19 corrected Toyland house registration sheets have been regenerated. Reviewed
boot/teapot/teddy sheets retain their original ground/body ownership, empty states and
full footprints; bow mass, wrapping folds, joined boot scale, teapot shading/spout/lid,
teddy face/body proportions and pixel painting still differ visibly from source.
The joined boot must be judged with both original tile parts, not the isolated half.
Corrected96-case live coverage is technical evidence, not visual approval.

Current runtime catalogue statistics:8,397,312 occupied cells,6,302,456 exposed faces,
1,424,375 conforming rectangles and8,906,806 triangles. Full1,002 nativeVulkan/GL
verification completes at4.38/4.52GiB after retiring diagnostic CPU/GPU references;
the earlier6GiB failure remains preserved. A600-frame generated-world wideGL run remains30.764fps. Full-quality
wide-view performance and arbitrary-map/all-day memory remain unresolved.

## Historical614 checkpoint: first and later findings

House IDs **0…83** now have source-aware variant/state selection: **1176 nonempty
bindings**. Houses0…8 and13…19 bind all four stages; statue9/fountain10 preserve the original
empty stages0/1 and bind stages2/3; parks11/12 bind stages1/2/3 and retain blank stage0.
House24 has four distinct completed bodies in every stage;25's first body stays empty.
House43 remains ground-only. That catalogue contained **614 volumes**, including21 late
Arctic office/tower and17 tropical house/hut/flats/church volumes, sixteen
small-house/corner-shop/joined-hotel volumes, twelve
cabin and ten shop/church volumes,21
cottage/glass-office/ribbed/setback tower volumes, ten
Arctic flat/house/ground volumes and twelve
shopping-mall construction/roof/ground volumes and two source-resolved navigation
buoy climates, cinema/pavement, twelve suspended-office/Arctic house and ground volumes,
63 Toyland tree states, seven olive-column tree states,
32 closed-wagon volumes, twelve
city-house volumes and sixteen Toyland open-cargo volumes,
thirty-three Arctic/tropical road
volumes and twenty-eight open-road cargo states,
eighteen suburban/flat construction
volumes and five old-house/cottage bodies,
twelve ordinary/Toyland dock volumes,
four ship-depot sections, six ship families, eight stadium stand/eight permanent
pitch volumes and fifteen new commercial-house volumes,
four bus bodies, eighteen closed
road-cargo bodies, twelve rail-depot bodies/four weather floors/one wire,
twenty-eight cactus/palm lifecycle volumes, eight power-station building/construction volumes
and six spark poses,
three shops/office construction volumes,
eleven coal-mine construction/animation volumes, five mine ground/stockpile volumes,
eight road-depot climate/direction bodies and a separate floor, empty/loaded coal trucks,
the independently moving office lift, aircraft/electric-locomotive bodies, twenty-one lime/silver/spruce-tree stages and eighteen airport definitions. Static airport
IDs **19…28/32/43/47** use state0; radar tiles **31/51/52** have all twelve frames and
flag tiles **39/73** all four. Identical original families share geometry. House stages
2/3 share original sprites and completed models. Four running-rail systems, seven
fence families and13 foundation forms use separate C++ voxel paths; the inventory
counts them separately. Other existing non-voxel presentation is not voxel coverage.
Current totals: **3,955,929 occupied cells,3,131,126 exposed faces,584,025 conforming
rectangles /4,635,778 triangles**. Full597 Linux/core/sync passes14,328 model views and
the renderer matrix; later78…83 have focused native/Linux checks and actual captures.
Full614 native is active; actual late-Arctic family/state captures pass, with two cases
using their source-identical variant1 rather than the unavailable exactvariant0.
256 joined ship-depot and512 joined dock views per selected climate,916 independent house-ground
state checks,568 industry construction/animation/ground views,
48 combined spark poses,16,968 current tree lifecycle views,165,376 vehicle pose views/304 declared
climate-cargo bindings,256 joined-house views and
zero final visual approvals.

The depot concern from `pass1-416-final-{electric,maglev}-cab-6000` is resolved in its
scope: `pass1-depot-exit-face-context` shows the real open entrance; centre-line rays
through every family/direction first hit the rear wall, not the entrance. Full train/
depot traversal and all-context clearance remain separate. The non-voxel forest is
plainly visible. `pass1-stable-order-theatre-palette-live` observes four actual marquee
phases in a mixed city after the ordering correction; source art/ground registration
and all-family visual approval remain open.

| Binding | Source evidence | Implemented passes | Still required |
| --- | --- | --- | --- |
| Tropical78…83 |4588…4604; original distinct grey/red-roof houses, striped thatch, four hut/palm variants, flats and terracotta church; all gardens/paving body-owned over3924 soil |17 volumes, shared1/2 frames, genuinely absent81/83 first bodies, real openings/joists, connected palms/shrub, late upper storey and stepped arcades; all36 actual cases, native/Linux checks, source room/roof/site-wall/floor corrections | Fine roof/wall/window/hut/foliage/arch/finial proportions and source paint; above-soil half-cell surface slabs fix flicker but exact source/ground pixels and final approval remain |
| Offices70…77 |4477…4492/4577/4585…4587; brick/company remaps, low72/73 frames at1/2, joined2×1 X gold office and permanent gardens |21 volumes, real balcony recesses/stepped pink fascias, low rings/colonnade, open long glass slots/roof well and late roof plant; all48 actual cases,70 tropical capture/54,772 exact source pixels, native/Linux checks and tall joined-crop fix | Precise balcony/rib/window/coping/plant/early-pier dimensions, masonry/glass/shadow paint, full-ground pixel phase and final approval |
| Small houses62/63 and corner shops64/65 |4466…4470/4580…4582; company versus brick remaps, house snow only at3 versus snowy shop1/2/3, empty first shop body | Eight volumes: open cross-gabled frames, pink porch/real supports, separate gardens, three-storey chamfered shops with inset windows/steps, cornices and red-white canopies; roof-axis/snow/garden corrections, all32 actual state/recolour cases and focused native/Linux checks | Exact gable/porch/garden layout, roof inset/corner glazing, masonry/grain/source shading and ground pixel phase; final approval |
| Two-tile hotels66…69 |4471…4476/4583/4584;1×2 alongY, ground-owned first sites, body-owned later paving, original snowy2/3 pairs | Eight volumes: joined main/cross-tile roof and wall/floor seams, lower south pavilion/setback, real voids/glazing/door, lower canopies and exposed foreground planting; site-height/roof-length/footprint corrections, root/seam regressions, all16 actual states and64 joined native/Linux views | Precise early frames, roof intersection/slope/overhang, wall/window/planter dimensions and painted shadows;96×53 versus96×52 early and96×61 versus96×60 mature framing; final approval |
| Cabins56/57 |4448…4457; two source-identical variant pairs with distinct plans/chimney/grounds; snow only at3 | Twelve half-grid volumes, separate pitched/attached roofs, open frames/recesses, large-cabin chimney, real timber stacks and retained bare snow approaches; source/street and focused native/Linux checks; all distinct actual family/stages and eight mature variants | Precise log/roof/yard orientation and proportions, snow/wood grain and source-ground pixels; exact56/v0/s1 and57/v0/s0 unavailable but their identicalvariant1 states captured; final approval |
| Shop58/59 and church60/61 |4458…4465/4578/4579; ground-owned first structures, missing first bodies, snowy2/3 and completed-only paving | Ten volumes, open brick frame, exposed recessed loft above entrance gable, hollow short-ridge church roof, tall stone piers/side annex, late glazing and checker step; source proportions/annex/snow corrections, all sixteen actual states and focused native/Linux checks | Exact early-wall/roof/glass/brick/stone/checker proportions and painted shadows, whole-tile raster phase and final approval |
| Cottage48/49 and offices50…55 |4430…4445/4574…4576; source recolours, cottage snow only at3 versus office snow at2/3; original soil-to-completed-ground transition |21 volumes: porch/stairs and gable trim, steel/glass grid/antenna/low wing, ribbed core with two lower projections, stepped pavilion/terrace; all actual32 states/32 mature recolours, source/street corrections, explicit face-selective paint and native/Linux checks;50/54 tropical captures/source equality | Precise frame/roof/window/rib/porch proportions, reflections/grain and grounds; cottage frame top remains one pixel above source; full-tile ground raster phase and final approval |
| Arctic houses44…47 |4420…4427, genuine identical0/1/2 across each plain/snow pair, snow only at3;3924 early soil and4418/4419 completed grounds | Ten volumes: two-storey ochre flats with real dormers, low red houses, distinct piers/open rafters/window bays, recessed doors, full paving and raised rear stacks; frontage/yard corrections, all sixteen actual cases, exact native/Linux checks | Precise window/dormer/roof/material/snow shading;64×32 versus64×31 ground registration remains; matching top bounds is not approval |
| Shopping mall40…43 | Original2×2 block4406…4417;0/1 and2/3 aliases, empty41/42 early bodies and entirely ground-owned43 | Twelve volumes, original source-layer ownership, full joined footprint, connected L-shaped wings/footings, recessed entrances, brick/glass/gold/flower materials; independent cross-tile edge/contact regressions, all primary actual stages, ground-only43 and native/Linux exact checks | Roof widths/intersections and source proportions, brick/glazing/rib/garden detail,128×70 early versus128×67 source and128×72 mature versus128×69 source registration; first disconnected-pyramid iteration retained; no final approval |
| Navigation buoy | Classic's actual canal callback resolves sprite11304, not base-table GUI693;12×15 native source and239/240/250…254 animation entries; ordinary/Toyland differ99/180 pixels | Ordinary red float/open frame and separate solid green/orange/red Toyland marker; original lamps/foam and independent water; public waypoint navigation, actual native/Linux capture, source provenance and stock15.3 reload | One-pixel foam extent difference, frame/float paint, all water classes and ship clearances; wrong-source/climate iterations are retained |
| Cinema39 |4405 identical at1/2/3, absent0; independent4404 pavement and241…244 lights | Grey banded shell, recessed four-pier entrance, rooflights/red signs, full ground; all actual stages, native/Linux palette phases and exact mesh checks | Precise piers/rooflights, lettering/grain, source registration and final approval |
| Houses36…38 | Suspended office1563/1565 and1562/1564 grounds; Arctic1567/1569 and4571/4573 snow bodies, separate gardens | Twelve volumes; genuine bare-mast states/empty first bodies, supported cylinder/cables, two distinct small-house plans, recolours/snow and independent complete grounds; orientation/roof corrections and actual1930/1950/2050 cases; the later ordinary1950 small-town world supplies exact37/v0/s0 and38/v0/s0/s1 | Fine structural/paint/ground registration and all-angle final fidelity; earlier missing-state failures retained |
| All nine Toyland trees1947…2003 | Independent seven-state images and original palette tables |63 quarter-ground/half-height volumes: inverted cones, bitten lollipops, collapsing parasols, sliding cylinder collars, shedding umbrella panels, spotted/dry mushrooms, striped cones, banded globes and real disc tiers; all63 actual states and16,968 exact lifecycle/palette/scale views | Growing-state dimensions and one/two-pixel bounds differences, ribs/spots/grain/paint and complete all-angle fidelity; **urgent wide-view GPU cost regression** |
| Tree1597: olive column | Original1597…1603, olive24…29 leaves and grey2…7 bark; seven genuine lifecycle states | Seven quarter-ground/0.75-height volumes, upward forks/root flare, growing crowns and real shedding; source heights/widths refined, grey branches exposed, detached late leaf cluster repaired; all actual states and final native/Linux exact checks | Stage2/5/6 width differences, finer crown asymmetry/fork placement/leaf grain and painted highlights, slope/forest context and final approval |
| Closed rail wagons27/28/30/31/32/37/38 and corresponding mono/maglev/Toyland definitions | All four climate exports; ordinary roof/door/tank/end-panel differences, identical closed cargo pairs, exact shared modern coach/mail/armoured source comparisons |32 volumes/27 engine IDs, explicit climate cargo pairs, seven-window coaches, gangways, sliding doors, open ventilation, ribbed vans, rounded tanks/fillers and yellow modern sills;12 operating consists/69 actual climate-engine captures; corrected wheel gauge, native GL rotation rounding and axial coupler overlap; full409 native/Linux matrices pass | Precise bodies/roof/window/tank materials and registration, grades/curves/depot/bridge clearances, actual cargo services and final approval |
| House28: curved heritage tower and red-ribbed office |1531/1533/1535 versus1547/1549/1551; distinct source-identical variant pairs | Six volumes, real low frames/open roof wells, curved steel/glass frontage with retained red arches/turret, rectangular red ribs/portico; early footprint and heights corrected, excessive mullions thinned, dark interior floors retained; all actual family stages | Finer facade curve/turret location/arch/storey detail, reflection and masonry paint, source ground/raster alignment; top bounds alone are not approval |
| House29: two older-shop families |1537 mansard/white remap versus1539 chimney row/blue remap; all first bodies absent | Two completed bodies, shared source-identical bare first ground, real dormers, tall narrow windows, shops/doors and eight chimneys; corrected heights/windows/roof and exposed buried dormers; actual1940/1950 family states/recolours | Precise mansard/dormer/chimney/floor proportions, shop fascia and glazing/masonry/shadow paint, ground registration and final approval |
| House30: stepped gold office |1541/1543/1545;16 temperate/tropical exports identical across75,024 RGBA pixels | Three volumes, gold skeleton, widening/tapering ribs, recessed ground portico and blue glazing; real open first/second roofs and dark floors; heights/rib width corrected; all actual states and tropical city capture | Fine rib transitions/white highlights, window/storey details, roof grain, source-ground phase, all-angle final fidelity |
| House31: theatre |1553 with absent first body and actual241…244 marquee palette indices | Brick auditorium, blue/black arched marquee, poster/red strips, checked entrance and original cycling lamps; source height correction, all actual stages and four live marquee phases on native/Linux | Precise marquee/awning/lettering, facade/window/roof/shadow paint, checker/ground alignment and final approval |
| Toyland road174…185/192…203 | Eight distinct original cargo pairs3100…3163/3188…3251; each era trio shares its actual empty/loaded arrays | Sixteen quarter-grid volumes: sugar/toffee heaps, lavender cola structure/real brown fill, pink candyfloss hopper, maroon/blue/green platforms with batteries/cans/plastic, blue canopy with see-through spatial bubble outlines; connected/contact regressions, all24 actual engines, full/focused native/Linux checks, real sugar/cola production/delivery/depot and stock sugar reload | Short side profiles/over-wide diagonals, finer tank transparency and bubble contours, running gear/facade/cargo shading and source registration; other cargo services/clearances and final approval. Shared nose corrected from30px to28px; cola shell opened after hiding its load |
| Arctic/tropical road156…173 | Independent climate exports prove silver food rear panels differ from tropical company panels, Arctic paper adds a roof where temperate steel shares sprite IDs, and tropical copper has brown rather than company-blue ribs | Thirty-three volumes, complete climate/cargo pairs, closed food/water aliases only where source permits, roofed solid paper rolls, copper/fruit loads and genuinely open flared latex vats; connected running gear/loads/canopies, all21 actual climate/engine captures, native/Linux full exact checks and stock15.3 tropical round-trip | Common28×10 profile versus28×12/13 source,24px diagonals versus20/21, finer cab/tank/canopy/vat/load proportions and paint, real production/delivery, grades/clearances and final approval |
| Open road cargo124/125,141…152 | Original independent direction/empty/loaded arrays; black coal,64…68 grain,72…76 ore,107…111 logs/37…39 ends and16…23 upright steel coils | Twenty-eight explicit states, three source cab eras, open grey/ribbed beds, staked platforms, loads and genuine vertical coil holes; source/street refinements, all actual engines and both later coal production/delivery/full-empty/depot routes; full native/Linux state matrices | Profile height/diagonal width and registration, precise cab/wheel/bed/load shapes and paint, additional cargo services/grades/clearances and final approval; current28×10 profiles versus27/28×12 source remain WIP |
| House26: suburban variants | Original1500/1571…1575/1508…1518; bungalow first bodies absent while1497/1498 ground owns construction | Twelve volumes, four distinct plans, original sites/open shells/garages/hipped and gabled roofs; source plan/height/palette corrections, supported contacts and all sixteen actual variant/stages, including the missing1950 case from an ordinary1940 world | Finer bungalow footprint/interiors, eaves/window/garage details, masonry/roof grain, mature gardens/hedges and source-ground raster alignment; no final approval |
| House27: two flat families | Tan1521/1523 with empty first body/1519 ground pit; brick1525/1527/1529, source-identical variant pairs0/1 and2/3 | Six volumes, tan four-storey shell/open roof well/bay/chimneys/red hip; brick front foundations/five-storey facades/lower rear wings/grey roofs. Corrected initial reversed axis, facade height and bay placement; all actual family states and exact native/Linux checks | Precise projecting facade/roof/window proportions, interior rooms, brick/roof/ground/shadow paint and source registration; matching top bounds alone is not approval |
| Houses24/25: old houses/cottages | Four distinct1492/1494/1488/1490 bodies, already complete in all four house24 stages; cottage1496 absent at first stage and identical at1/2/3; initial3924soil identical | Five explicit timber/gable/thatch/L-plan volumes, connected roofs/chimneys, original empty/finished-stage rules, shared early soil and separate mature gardens; corrected dominant roof ramps, heights, party wall and cottage contact; all actual variants/cottage stages and full/targeted native/Linux checks | Finer timber/window/roof/plan precision, raised garden/fence/pond geometry and palette detail, common62×32 versus64×31 ground raster phase and final approval; variant3's original ground hedge extends three pixels above the flat plane |
| Docks, all six bank/water sections | Original2727…2732; actual ordinary/Toyland differences, including absent Toyland lamps/foam and different bank bounds | Twelve volumes, level joined decks, open central access, supported piles/bollards/railings, slope-embedded bank cuts, ordinary animated lamps/foam, original shore/water separation and full tiles; all actual sections/climates,512 joined palette/picking cases, actual palette cycles and held hovercraft/freighter review |94px joined ground width versus96source, one-pixel vertical phase, precise pile/railing/lamp/shadow/grain/foam detail, complete mooring/bridge/water-class context and final approval |
| Ship depots, both axes/tile parts | Original4070…4075; complete layered96×63 two-tile sources;12,472 structural pixels identical in temperate/Toyland | Four connected open sheds, stepped pitched roofs/skylights/company trim/windows, full original32×16/16×32 footprint, independent water, source/street/ship-context review, all-six-ship swept clearance,256 joined palette/picking cases and actual native/Linux depot cycles | One-pixel horizontal registration, exact end-roof/fitting/window proportions, grey grain/shadows, more water-class/climate/bridge context and final approval |
| Ships204…214 | Original3669…3700, independent ordinary/Toyland exports; actual empty/loaded arrays match within each bound family | Six quarter-grid tanker/freighter/ferry/hovercraft/Toyland passenger/cargo volumes, flared hulls, open holds, supported cabins/derricks/captains/fan hardware; original company/crash colours, all11 normal operating ships and both dock arrivals, source/street/Cab passes and stock15.3 round-trip/Linux reload | Remaining directional dimensions/registration, hull/cabin/captain/fan detail and paint, broader bridge/lock/depot clearances, cargo/effects and final approval |
| Stadium houses20…23 and32…35 | Grounds1479…1482/1554…1557 persist in all states; bodies1483…1486/1558…1561 are absent at0 and identical at1/2/3; actual palette indices227…231 and241…244 | Eight permanent full16×16 pitch quadrants and eight stand parts; joined soccer lines/gridiron yard lines, covered brick stands/open gate, two-tier steel stands, H goals/floodlights/scoreboard; retained palette cycles, whole-block source/street/context review and actual stages; corrected roof/light heights | Remaining field-mark/circle proportions, tier/roof/crowd/signage detail, full-source pixel/ground alignment and final approval;128×64 native ground bounds versus128×63 original retain a one-pixel phase difference |
| Houses15/16: stucco and mansard shops | Original1464…1469, original(3,1)/(2,0) anchors;16 has red/blue/white roof remaps and already-raised first construction | Six common-footprint volumes, open window/shop bays, two-storey black gable/two chimneys, three-storey roof-well form and timber frames; source top-height corrections, street/neighbour and all actual1950 stages | Exact wall/window/roof proportions, masonry/roof grain, recess/shadow paint, ground raster phase and source registration |
| House17: modular office | Original1470…1472 and four red/blue/orange/green palettes; first pavilion differs in height from later base | Separate early pavilion, twin dark cores, supported cubic modules/round-window paint, three coloured upper pods and original recolours; corrected first-stage/overall height, all actual1990 stages, whole tall-sheet review | Module sizing/arrangement is still too regular/sparse, pointed cap profiles, round window detail, core/base texture and source-ground registration; matching top bounds is not approval |
| House18: warehouse | Original1473…1475, tan32…38 masonry/roof and grey framing; initial excavation, partial roof/open front, completed glazing/ramp | Three states, three pitched roof bays, real unfinished roof openings, side clerestory/front panes and grounded loading steps; over-height first version reduced; all actual states | Roof-panel orientation/detail, finer openings/ramp proportions, tan grain, material/shadow placement and source-ground alignment |
| House19: rooflight office | Original1476…1478, flat early red rim versus later raised plinth, metal frame and nine rooflight panes | Flat foundation, open tall frame, closed blue glazing/interior floors, stepped rooflight bays and four attached rounded landings; all actual states and source top bounds checked | One-pixel left roof-frame extent difference, precise rooflights/stair profile/glazing bars, reflections/shadows, floor raster phase and final alignment |
| Trees1912/1919: saguaro and column cactus | Original1912…1925;88…94 live ribs,104…111 dry stems; seven states each | Explicit rounded columns, three connected unequal saguaro arms, grounded roots and genuine shrinking/drying states; all14 native bounds now agree; source/street/context and all actual states reviewed | Precise bends, rib/shadow paint, finer cap profiles, source registration, slopes and all-angle final fidelity |
| Trees1821/1828: bent and tufted palms | Original1821…1834;96…102 versus88…94 foliage, copper trunks, distinct white foot on1828, retained dry fronds | Fourteen connected stages with explicit arching feather fronds, broader tufted blades, different crowns/colours and dying volume; oversized first crowns shortened; all actual states observed | Several one-pixel bounds differences, overly regular/dense crowns, finer trunk curve, leaf/tip/shadow paint, source-ground registration and later slope/forest/LOD review |
| Buses116…122 | Regal3284…3291, ordinary3092…3099, FosterMk23476…3483 and separately reviewed Toyland3092…3099 | Four quarter-grid bodies, source-specific bonnet/forward cab/modern window band/Toyland face, connected grounded wheels and open interiors; ordinary public bus fixtures and actual native/Linux captures | Source dimensions, notably diagonal24px versus20/21 and profile10px versus12 high; finer cab/window/roof/wheel details, all grades/clearances and later source approval |
| Closed cargo126…140,153…155,186…191 | Source direction/cargo arrays and separate ordinary/Toyland exports | Eighteen mail/oil/livestock/goods/armoured/toys/sweets bodies bind24 definitions; real vent gaps, rounded tanks/fillers, source-permitted identical cargo aliases; actual27/33-vehicle climate fixtures | Directional proportions/registration, finer running gear/markings/materials, actual cargo/clearance transitions and later source approval; unconverted vehicles in fixtures are not counted |
| Rail depot families0…3 | Original layered four-direction tables, railtype relocation and separate weather grounds | Twelve classic/mono/maglev bodies, independently opaque full-tile floors, open corridors, running voxel rails and electric wire; corrected roof heights,96direction/320company views, actual electric/monorail captures | Exact ground/source raster phase and roof profiles, wire/support detail, all climate/direction/traversal clearances and final approval; tramkind5 remains |
| Industry9/10: equipment hall and transformer gantry | Original2051 blank/2052 shell/2053 equipment;2054 gantry and2055…2060 spark children with original offsets | Open auxiliary shell, three finned banks, brick casing and pipe highlights; six porcelain stacks, suspended cores and open steel/bus bars; six explicit cyan arc volumes, read-only actual animation, parent-aware draw layers; source/street/layout passes and alpha-visible registration | Exact casing/hood/steel/core/insulator shapes and paint, arc contours/halo thickness and all-angle attachment; current framing equality is not full source fidelity or approval |
| Industry7/8: cooling tower and boiler hall | Original2045…2050; source2048 is transparent; original3924 soil, ordinary type1 layouts | Three basin/partial/full tower states with connected piers, hollow waist and inner-face-only dark lining; two glazed boiler/annex/chimney states, open flue and source metal collars; repeated source/street/layout/live passes correct exterior lining leakage, rim/grain, roof extents/heights and flue opening | Tower's extra width pixel/early top pixel, exact concrete/stain/lining and brick/roof/window patterns, fine collar placement, complete-site consistency and all-angle final approval |
| House14: shops/offices | Original1461/1462/1463, draw anchor(1,3), available1930–1960, four identical variants | Three common-footprint volumes, four upper window rows, shop displays, projecting ledge, grey gable/red chimneys; repeated material/height/open-bay/interior-shadow passes, street/neighbour and actual four-stage review | Exact frame/window/roof/shadow pixels, ground raster phase, soil/masonry detail and later climate/LOD passes; zero approval |
| Road depot family4 | Original ground2634 and wall/roof1408…1413, four layered directions; temperate/arctic/tropic identical, Toyland has cleaner roof/wall grain | Four explicit open bays and separate opaque floor, original company clerestory, masonry/shadows and folded grey roofs; source/street/vehicle-context passes, actual four exits and truck traversal; four separate Toyland variants; all16 company palettes and invisible-floor ownership verified | Exact folded-roof profile, pixel placement/ground framing, detailed brick/metal pattern, repeated clearance/grade/LOD review and final approval |
| Industry ground0…6 | Construction3924, bare2022 and stockpiles2023…2025, all four source states | Five explicit palette volumes; supported sloping mounds, low coal spillage, matching pair edges and full16×16 substrate; palette-frequency/source/street/actual-state refinement; bore clipping retains unlit palette data | Fine pile contours/grit/shadow placement, source raster phase (64×32 voxel tile versus64×31 original), all slopes/climate/context passes and final approval |
| Vehicle123: Balogh coal truck | Empty3292…3299 and loaded3380…3387, original company/grey/black materials, three axles and lamps | Separate open/coal-filled tipper volumes, quarter-grid cab/bonnet, actual wheel/axle contacts, interior shadows; later shorter body, larger wheels, darker coal; all company/crash palettes and actual0/20–20/20 state checks, four-angle saved cargo reviews and operating GL Cab | Directional proportions still differ (head-on8×17 versus8×20, profile24×11 versus28×12, diagonal22×16/17 versus20/21×14/15); fine cab/rim/running gear, slopes/infrastructure/other climates and final visual approval |
| Industry tiles0/1: coal-mine winding headgear | Original2011/2012 construction,2013…2015 operating wheel poses;36×44 early/58×50 complete | Five explicit open-steel/shell/wheel volumes; connected rings, distinct spokes, axle, inclined ropes and corrugated shelter; source/street/layout passes refine heights, endpoints and steel details; real coal service emits all three animation sprites | Fine wheel profile/materials, masonry/roof details, under-frame shadows, all-angle neighbouring clearances and later source/LOD/final approval |
| Industry tiles2/3: coal-mine engine/machinery houses | Original2016…2021, four stages each; completed49×41/37×43, source-indexed masonry, corrugation, windows and grey piers | Six explicit site/frame/house volumes; actual open rooms/recessed glazing, painted eave shadows, three gable/two side window rows on the raised house, twelve perimeter posts; source-aligned review fixes origins/overhangs and quarter-grid excavation corners; all four actual construction captures | Exact window/door/brick/grain and roof pixel placement, mine grounds/piles, later climate/LOD/context passes and final visual approval; matching dimensions/registration is not pixel agreement |
| Vehicles23/24: SH30/SH40 | Identical original2937…2940 for both engines, all eight directions/cargo states; indexed yellow62…67, company199…203 and grey roof/gear | Shared explicit quarter-grid body, yellow cab ends, original company sides, grey sill, windows/vents, wheels/lamps and open diamond pantographs; source/street/actual terminus passes reduce bright fittings and roof contrast | Exact directional proportions/paint placement, coupled consists, grades/roof-wire contact through all infrastructure and final visual/state approval |
| Tree family1590: drooping spruce | Original1590…1596,96…101 needles,1/2 deep shade and104…110 wood; native7×19 through17×43, final10×39 | Seven explicit radial-bough states, hanging needle volumes and exposed woody connections; first pass corrected disconnected dying supports, visible mature wood, thick needle blocks and bare spread | Active WIP: too-regular/bulky boughs, source needle placement, remaining width/height differences, all actual stages and later slope/LOD/context review |
| Tree family1583: silver column | Original1583…1589,96…102 foliage/104…109 wood; native6×22 through14×48, final8×29 bare silhouette | Seven explicit volumes, fuller low boughs, branching wood, short broken dead form, paint-only highlights and actual dying gaps; native-scale framing refinement and all seven live stages | Fine leaf/rim asymmetry, scattered surviving foliage, bark highlights, slope/LOD/context follow-up and exact source fidelity |
| Tree family1576: slender lime | Original1576…1582; native7×22,10×31,12×42,15×49,15×49,12×49,7×38 lifecycle images | Seven explicit volumes, original leaf/bark/deep-shadow colours, connected ascending branches/root flare, progressively absent foliage; shorter0.75-height detail cells, clustered colour grain and refined low/late crowns; all seven actual stages captured | Finer crown asymmetry, source-scale leaf/twig texture and highlights, branch registration, slope/forest/LOD follow-up and final source approval |
| Vehicle238: Dinger100 | Native directional sprites3781…3788; empty/loaded source sprites identical | Half-unit cells, swept wings, rear-mounted engines, high tailplane, cockpit/windows, belly/gear and company palette; later reduced wing chord, pods/wheels and highlight bands; actual stand/flight/Cab captures | Exact source silhouette/scale, wing/fuselage/tail detail, live loaded/crashed states, shadows, all-angle airport clearance and later source/street review |
| House 0: tall office | Steel sprite1423; brick/recoloured1425; site1421/frame1422 | Separate material/silhouette variants, stepped glazed core/collars, roof grain and core shadows; later brick pass removes the steel variant's projecting ribs | Exact window/floor/core proportions, brick variation, source-scale edge highlights, all recolours and repeated street/live review |
| House 1: red Z-plan office | Native 44×62 sprite; `house-001-0-3.pam` | Authored stepped footprint, seven window rows, recesses/sills, parapet/roof; corrected blue-grey palette and authored height/anchor after source comparison | Cornice thickness, window/floor proportions, brick variation, all variants/construction states, close/live second review and final source matching |
| House 2: courtyard flats | Native 34×33 sprite; `house-002-0-3.pam` | Authored ring volume, recessed windows, door, stepped roof; raised roof to match source framing and darkened courtyard-facing material | Refine four-wing roof character, courtyard depth, facade detail, variants/construction and later context review |
| House 3: church | Native 40×48 sprite; `house-003-0-3.pam` | Authored nave/transept/tower, stepped roofs, finial, recesses and stained glass; source review prompted XY orientation correction | Tower/nave proportions and placement, spire/finial scale, openings, brick/roof detail, all construction and later live/Cab passes |
| Houses 4/5: large/snow office | Site1440/frame1441/completed1442 and native snow reference; independent lift1443 | Eight window rows, plinth/piers, roof vents and painted shadows, snow materials, actual lift shaft/cabin; corrected overly recessed glazing | Exact facade/roof proportions, snow distribution and small highlights, shaft registration and repeated climate/angle/LOD passes |
| House 6: townhouses | Hip1444/1445/1446 and gable1502/1504/1506 source families | Three-building layouts, stepped roofs/chimneys, independent site/shell volumes, inset windows and inward-facing construction shadows | Source-pixel footprint/spacing, roof/brick marks, entrances, recolours and later neighbour/live passes |
| Houses 7/8: paired hotel | Sprites1448…1453; original1×2 layout, complete source-pair sheet | Shared footprint/notch, four storeys, roof pavilion/pool/loungers, canopy, side frames, room partitions and dark construction interiors; corrected seam-window edge and bright floors | Exact pool/pavilion and floor/window proportions, masonry/roof detail, all-angle/climate/LOD follow-up and final source approval |
| House 9: statue | Native58×42 sprite1454, including corner posts; early stages have no body sprite | Explicit horse/rider/raised arm, pedestal/plaque, stepped silhouette, metal highlights and posts; later connected elbow/hand and softened plaque | Fine figure proportions/pose, pedestal registration, source-scale detail and later street/neighbour passes |
| House 10: fountain | Native29×30 sprite1455; early stages have no body sprite | Stepped basin/rim, pedestal shadow, fine quarter-grid jet/droplets and original dark/glitter water indices; reduced jet thickness and diagonal rim stripes | Precise circular outline, source detail/brightness, all animation phases and later climate/angle/LOD review |
| House 11: pond park | Native64×56 sprite1456; identical stages1/2/3, blank0 | Two explicit voxel crowns/trunks, lawn, kidney-shaped pond, path/bank and painted shadows; masked water grain/animation; corrected leaf striping and path/pond placement | Finer crown silhouette/grain, source-scale path/pond shape and natural grass/shadow transitions, all-angle/LOD follow-up |
| House 12: autumn park | Native64×57 sprite1457; identical stages1/2/3, blank0 | Lobed voxel crown, branch/trunk, lawn/path and ground shadow, source24…29 autumn palette; street/office-neighbour and actual stage1/3 views | Crown asymmetry, highlights/undersides, trunk placement, softer ground variation and later source/context passes |
| House 13: compact office | Native50×65 sprite1460, site1458/shell1459; brick/white/red/brown source palettes | Three storeys, framed glazing, layered cornice and roof grain; actual open construction rooms; source pass shortens windows and corrects cornice to16/18 blue-grey | Precise cornice pattern, window/room proportions, interior shading, masonry variation and later context/climate/LOD review |
| Airport 24: glass hangar | Native 64×56 rear/roof sprite 2655 plus front component 2656 | Hollow stepped barrel roof, open doorway, three glazing bands, ribs/company paint; second pass adds rear framing, source-grey ribs, lower blue glazing and glass highlights | Finer roof curvature/reflections, wall proportions, aircraft entry/clearance and further climate/company/live passes |
| Airport 19/23: terminal A/C | Native60×69 sprites2650/2654, separate placement/orientation metadata | Three storeys, inset supports, company canopy/pavilion bands, roof posts/aerials and grain/shadows; transposed C volume with independent registration; later shorter posts and softer roof shadows | Exact footprint/height and glazing proportions, fine aerial/roof marks, all company colours and aircraft/airport-layout clearance |
| Airport 21: round concourse | Native52×61 sprite2652 | Stepped chamfered body, blue supports, roof drum/aerial, grain and cast shadow; shared corner tones remove microstep striping and shadow becomes rounded | Source curve/facet precision, glazing/roof fixtures, company variants and later aircraft/angle/LOD review |
| Airport 25…28: passenger piers | Native22×23,20×20,24×22 and44×40 sprites2659…2662; original32…38 material indices | Tee/fence, two elbow orientations and long raised corridor, supports and corrugated surfaces; source-specific highlight refinement; all types captured in city layout | Precise spans/heights, end/door detail, terminal joins and operating-aircraft clearance; later source/street review |
| Airport 32: radio tower | Native54×94 sprite2601, grey1…8 and beacon239/240; separate company fence2663 | Quarter-grid open lattice, face-connected braces/guy wires, connected antenna/panels and original alternating lamps; orbit/street/live and corrected paired-palette observations | Finer member/dish registration, source silhouette and all-angle/LOD/aircraft-context review |
| Airport 47: control tower | Native 44×81 sprite 2651 | Raised supports, five floors, observation cabin, beacon/aerials; second pass corrects grey roof, stepped dish and balcony railing | Source floor/window proportions, roof fixtures/shading, support thickness and further live/company passes |
| Airport 20: fenced tower | Same tower plus fence sprite 2663 | Independent inherited volume with fence posts/rails; four orbit/street and neighbour checks | Match fence weave/placement and review this particular tile in its real airport layout |
| Airport 22: L-shaped terminal | Native 39×47 sprite 2653 | Real recessed corner, four floors, raised supports and roof parapet; second pass adds inset glazing on exterior and recessed-corner walls | Precise frame/cornice/pillar proportions, roof detail, entrance/access details and later source/company/climate passes |
| Airport 43: small airfield hangar | Native 64×56 sprite 2657 plus front component 2658 | Shared hollow barrel topology with independently authored dark roof/ribs, timber walls, company fascia and three inset side windows; later dark roof-panel variation | Roof/end-cap shading, wall grain, aircraft clearance and further orientation/live review |
| Airport 31/51/52: rotating radar | Sprites 2680–2691; twelve red/grey lattice poses plus SW/NE fence | Authored mast, open lattice and all baked frames; coarse-grid review exposed filled openings, corrected with thin quarter-grid bars; every frame observed on actual city/international/intercontinental tiles | Fine colour/angle matching, pole/base scale, source-edge registration and later climate/company/Cab review |
| Airport 39/73: company flag | Sprites 2676–2679; four poses and fence | Four solid waving-cloth states, pole and corrected three-unit picket fence; both actual airport variants observed through all frames | Cloth outline/shading and border placement, additional close views and climate/company passes |

Breadth-first evidence: `pass1-bus-family-review`, `pass1-closed-road-family-review`,
`pass1-rail-depot-refined`, `pass1-cactus-family-review`, `pass1-palm-family-review`
and the later `pass1-tropical-canopy-dimensions` under `build-macos`. The last contains
the current native-scale/source tree comparisons, isolated street views and building
contexts. Palm bounds still differ by one pixel in several stages; source pixel
patterns and footprint registration remain WIP. `pass1-212-current-renderer/inventory.json`
records current coverage/contact bounds with zero automatic approvals. Native and
Linux `pass1-212-cpu-rounding-final` preserve exact full rendering comparisons.

Commercial evidence: `pass1-stucco-mansard-first`, `pass1-commercial-1990-first`,
`pass1-commercial-proportions` and targeted `pass1-*-live` captures. The first city
capture still shows the generation dialog; reloaded saves provide normal UI/world
review. Tall house comparison sheets now preserve complete art at4x by expanding
their panel dimensions. All20 selected top bounds agree after corrections; the
common ground raster discrepancy and house19's extra left frame pixel remain.
Current inventory is `pass1-commercial-current-opengl/inventory.json`; native GL and
Linux `pass1-commercial-current-validation` pass the expanded exact renderer checks.
The finer prototype differences in the table remain queued behind missing Pass 1 families.

Stadium evidence: `pass1-stadium-indexed-source`, `pass1-stadium-first-review`,
`pass1-stadium-proportions`, `pass1-stadium-native-full` and Linux
`pass1-stadium-full-validation`. Ground-only stage0 is explicitly located/reported;
it does not fabricate a body. Both complete32×32 layouts retain full ground coverage,
independent tile IDs and matching white-line seams. Original goal sprite ownership
crosses one sub-tile but remains inside the complete stadium footprint.
`pass1-stadium-{gridiron,soccer}-live-1800` observes all original palette phases,
with Linux `pass1-stadium-live-palette` repeating the scoreboard/crowd check. Actual
gridiron captures cover temperate, Arctic and tropical worlds. Stock15.3 round-trip
and Linux `pass1-stadium-stock-reload` preserve the ordinary map/blank-body state.
Current inventory: `pass1-stadium-proportions/inventory.json`. Whole-block source
comparisons use genuine layer offsets; matching top bounds is not artwork approval.

Ship evidence: `pass1-ships-open-propeller-mounts` contains current source-scale,
orbit/street/context galleries and inventory. Earlier `pass1-ship-proportions` and
targeted `pass1-*-live` captures retain the dimensional iterations. All11 engines
operate through public-NoAI climate fixtures; `pass1-ships-stock-reload-current`
on Linux repeats the full current renderer matrix after an official15.3 round-trip.
Initial native6,000-frame ship Cab captures revealed the missing depot at street level;
the later `pass1-ship-depot-source-palette-current` and both service Cab runs now show
voxel structures. Docks now have their own voxel paths and climate/ground review.
Tanker/ferry/hovercraft directional bounds
still differ by one or more pixels. Source-perfect shape/paint/clearance stays WIP.

Dock evidence: ordinary/Toyland source exports in `pass1-dock{-toy,}-source`, current
registered comparisons in `pass1-docks-grounded-bank-review` and
`pass1-docks-toy-source-review`. The first dock review retains excessive underground
bank piles; the corrected source/street views clip them to their supporting slope.
`pass1-{hovercraft,freighter}-moored-review` shows real held calls, and native/Linux
`pass1-docks-lamp-foam-*` records the original cycles. Matching geometry checks do not
erase the remaining source-raster and fine-art differences.

Evidence: `build-macos/voxel-house-context-review` and the later
`build-macos/voxel-building-second-pass`. The latter includes the courtyard and
orientation corrections. Earlier `voxel-houses-first` and diagnostic runs contain
useful intermediate images but are **not passing verification artifacts**.

Airport evidence: `voxel-airport-first-review`, `voxel-airport-refined-review` and
`voxel-airport-street-review` under `build-macos`. The latter supplies all four street
directions and fitted neighbour groups. The public-NoAI `voxel-airport-fixture`
places a commuter airport at **(65,34)**; tower and hangar are actually captured.
Other airport buildings/fences/ground remain visibly incomplete in those captures.

`voxel-terminal-small-hangar-review`, `voxel-small-airport-live` and
`voxel-airport-second-pair-refined` add the L-terminal and small hangar, with isolated,
four-sided street, neighbour and live review. The new `voxel-two-airport-fixture`
adds a country airport at **(75,34)** through the public API; the fixture enables the
normal never-expire-airports setting. Official OpenTTD 15.3 loads/re-saves this map,
then the refined native run reloads it with the original AI identity.
Native Vulkan/GL and `build-linux-user/voxel-eight-model-validation` pass the expanded
**192** voxel comparisons. There are still **zero visually approved models**.

Animation evidence: `voxel-airport-animation-first`, the refined
`voxel-radar-open-lattice-review`, `voxel-international-animation`,
`voxel-intercontinental-animation`, `voxel-open-lattice-stock-reload`, and Linux
`voxel-open-lattice-validation`. Latest 36-model checks cover **864** views. Native
source/animation strips and four-sided street sheets were inspected; live completion
reads original frame state without writing map/animation data. Narrow-view runs
`voxel-radar-fine-review` and Linux `voxel-airport-animation-validation` did not
observe the offscreen flag, so they are not complete live-animation passes.

Use `--gallery-voxel-prefix airport_radar_sw_` for focused review, and
`contact_sheet.py <directory> --animation-prefix airport_radar_sw_` for a frame strip.
The inventory reports expected source frame counts and missing bindings separately
from visual approval. Ground/apron/runway content remains outside these prop bindings.

Rail evidence: `voxel-rail-first`, `voxel-transport-final-native` and the Linux
`voxel-transport-refined-validation`. Conventional/electric, monorail and maglev
retain six straight routes, reservations, slope support and junction clearance.
Diagonal rails use face-connected voxel steps. Depot/crossing track uses the shared
palette path. Source review corrected overly bright rails, golden sleepers and a
large diagonal chequerboard ballast pattern. A later maglev pass replaces brown
shoulders/plain slabs with concrete, panel joints and inset edge strips, retaining
one shared panel grid through overlapping routes. Evidence: `voxel-maglev-panels-review`,
`voxel-maglev-single-opengl` and `build-linux-user/voxel-maglev-panels-validation`.
Further maglev operating/switch detail, frogs,
bridge running tracks, snow/climate material and further Cab/LOD review remain.

Compact triangulation reduces the eight authored volumes from **70,468 to 62,564
triangles**, with unchanged cells/palette/shape. The full old/new orbit, street and
neighbour galleries match **41,574,400 RGBA pixels /96 images** exactly in
`voxel-compact-contact-gallery/comparison.json`. The earlier whole-edge experiment
failed strict raster comparison and was corrected; no tolerance was added.

Rail comparison exposed an existing overlapping-maglev-slab colour disagreement
near diagonal ports. A mesh-ray regression reproduced it for four layouts/three
LODs. Edge suppression now uses the actual tile-clipped slab band, rather than a
capped centreline. After that correction, compact/reference junction galleries
match all **1,638,400 RGBA pixels** in `voxel-maglev-agreement-compact/comparison.json`.
`compare_galleries.py` supports both PAM and verified compacted PNG inputs.

## Office, townhouse and source-shadow passes (2026-09-23)

`VoxelHouseState` resolves explicit states as `variant*4+stage`. A generic stage
binding covers another variant only when the original building sprite is identical;
the actual source recolouring is retained. World capture and the read-only locator
use the same upstream world-coordinate tile hash. `--reference-house-stage N
--reference-house-id H --reference-house-variant V` requires an actual matching
capture, rather than modifying construction/variant state.

New office passes corrected hidden glazing, regular roof chequers, pier highlights
and broad roof shadows. `scatter_paint` adds explicitly bounded deterministic material
grain to occupied cells; it neither derives geometry from images nor consumes game
RNG. The brick tall office now omits projecting steel ribs while retaining its core.
Office checkpoint's57-model catalogue: **282,727 occupied cells,207,370 exposed faces,35,694
conforming rectangles /277,466 triangles**. Gallery/reference checks pass1,368 views.
The earlier indexing gallery pair predates this intentional silhouette change.

Live large-office review exposed the source lift being projected across the facade.
It is now a2×2×10-cell cabin in a real shaft bay, driven by original `GetLiftPosition`.
All37 reachable positions/four turns (148 views) pass visibility, instance/ID and
clearance checks. Native Vulkan/GL observed eight actual positions at(80,116), with
no renderer change to lift position/destination. Base-sprite provenance for the lift
and parent is required before substituting either; palette/opacity/tile IDs remain.

Townhouse source review requires two distinct layouts. Hip variants0/1 and gable
variants2/3 each have three buildings and separate site/shell volumes. Later passes
inset corner-wrapping windows, soften sills/trim, remove glazing from construction
and assign darker inward/reveal faces rather than black solid openings. All16 house6
bindings and actual mature variants/construction captures are technically checked.
Precise source proportions, marks and every later climate/LOD pass remain art work.

Evidence: native `voxel-office-shadows-refined`, `voxel-large-office-lift-validation`,
`voxel-offices-final-opengl`, `voxel-office-arctic-fixture`, `voxel-townhouses-refined`
and `voxel-brick-office-silhouette-review`; Linux `voxel-office-arctic-reload`,
`voxel-townhouse-interior-shadows` and `voxel-brick-office-silhouette-validation`.
`contact_sheet.py <source-directory> --house-source 0 4 5 6` supplies all16 original
state/variant references per ID. `house-parts.json` and `house-lift.pam` record the
independent cabin's native4×13 sprite and placement metadata.

The normal1980 larger-city fixture (`--city-size 6`,512×512,64towns) supplies rare
office0/4 construction stages absent from the smaller map. Initial missing-stage
lookups are retained failures. `voxel-city-house-0-stage-{1,2}` and
`voxel-city-house-4-stage-{0,1,2}`, plus the initial city stage0 capture, pass. Official
15.3 re-saves the city map; `voxel-city-stock-reload` passes current renderer/picking
and actual house4stage1 capture. These are ordinary generation/settings/save APIs.

No model is approved. Remaining source-shadow detail, exact scales, source-variant
recolouring and all-angle/street/neighbour review remain for all these models.

## Joined hotel and civic-detail follow-up

`contact_sheet.py <source-directory> --house-pair 7 8 --pair-axis y` composes the
original sprites at their actual offsets for all four stages. Multi-tile voxel
galleries now use upstream1×2/2×1/2×2 ordering and physical offsets, in addition to
isolated part/category views. Hotel names include `context-house-7-stage-0`…`-3`
and `context-house-7-neighbours`; the latter joins both halves beside two offices.

The first hotel pass had over-bright interior floors and lacked room partitions;
later authoring corrected those and added source window/corner framing. A seam test
found a construction opening ending at the tile boundary; its corrected frame is
continuous. Native `voxel-hotel-refined-review`, `voxel-hotel-final-opengl` and Linux
`voxel-hotel-refined-validation` cover isolation, joined orbit/street and actual
stage0 at(96,18),stage1 at(104,170),stage2 at(148,108),stage3 at(304,9), with the
second tile immediately along+Y. Native `voxel-civic-catalogue-review` adds the
current full catalogue and dedicated joined-neighbour context.

The statue/fountain pass retains empty source stages0/1 instead of inventing early
geometry. Source comparison refined the sculpture's hand/elbow contact, plaque tone,
fountain jet width, droplet phases and rim shading. The fountain uses explicit
**0.25×0.25×1** cells for its thin jet, with independently authored basin geometry;
no source image creates geometry. Current source/street/live evidence is in
`voxel-civic-first-review`, `voxel-civic-refined-review`, `voxel-civic-catalogue-review`
and Linux `voxel-civic-final-validation`. Initial fountain gameplay framing was
partly occluded by a neighbouring tower; later rotated views improve visibility.

Pool colour inspection matched the original dark-water animation table, not static
company-blue paint. Hotel pools use original245…249 indices; fountain spray adds
250…254 glitter phases. `--verify-voxel-water 8` or `10`, with `--running` and a
benchmark, observes indices actually used by emitted geometry on one real tile.
Five original colour phases pass on fountain(302,11) and a hotel pool, across
native/Linux Vulkan/GL runs. This is a read-only palette/capture observation, not
simulation animation or an all-phase visual approval. Evidence includes
`voxel-hotel-water-native-opengl`, Linux `voxel-hotel-water-opengl` and
`voxel-fountain-water-validation`. All existing and remaining assets still need
the complete repeated-review process.
The radio follow-up exposed shifted-index extraction in those early water diagnostic
reports. Corrected evidence is `voxel-pond-palette-corrected`,
`voxel-hotel-palette-corrected` and Linux `voxel-fountain-palette-corrected`; they
observe the actual emitted indices. The rendered palette path already used the
correct texel centres. See the correction entry in `VERIFICATION.md`.

## Park and vegetation authoring follow-up

The park volumes use explicitly bounded cell-centre ellipsoids as canopy lobes and
flat pond/shadow shapes. Compiler checks verify rounded corners, symmetry and
six-connected occupancy. Optional material masks on `scatter_paint` retain the pond
bank when adding ripples. These are authored shapes/material choices, never geometry
extracted from the reference image. The separate62 tree families remain unconverted.

The first leaf materials produced strong light/dark contour bands along voxel steps.
Repeated orbit/street review removed those face ramps, retaining authored cell tones
and vertical lobe shading. Later pond placement keeps the path along its bank, and
original245…249 water phases remain. Source-scale crown detail, lawn grain and soft
shadow transitions remain WIP. Current shapes are not final source-perfect approvals.

Evidence: `voxel-parks-first-review` (failed live lookup, useful first galleries),
`voxel-parks-refined-review`, `voxel-parks-neighbour-opengl`, Linux
`voxel-parks-first-validation` and `voxel-parks-refined-validation`. The ordinary1970
map supplies pond park11 at(170,15), including five observed palette phases; the1980
city supplies autumn park12 stage1 and3. The original missing pond lookup is retained.
Dedicated `context-house-11-neighbours` / `context-house-12-neighbours` put the parks
beside existing offices; all eight single-model orbit/street views were inspected.

## Compact-office follow-up

Compact-office evidence: `voxel-compact-office-first-review`,
`voxel-compact-office-refined-review`, `voxel-compact-office-brown-opengl`,
`voxel-compact-office-white-stage2` and Linux `voxel-compact-office-first-validation` /
`voxel-compact-office-refined-validation`. Site/shell/completed models have isolated
views; the mature volume also has a dedicated office-neighbour group. All source
recolours and actual construction stages are covered technically. Windows/cornice
received a second source pass; exact source fidelity and later review remain open.

## Airport terminal follow-up

Terminal A/C and the round concourse use source company palettes and their actual
placement/orientation metadata. The first pass's roof posts were too large, and
directional colours made the chamfered corners visibly striped. Later passes reduce
post height, assign shared corner tones, soften roof grain/shadows and replace the
round drum's rectangular shadow with a rounded patch. All eight isolated views and
the grouped airport context were reviewed alongside actual city-airport captures.

`--reference-airport --reference-airport-tile N` now requires both a matching lookup
and an emitted voxel tile. The city/country fixture contains19 at(65,35),23 at(65,34)
and21 at(67,35). The international fixture does not contain21; its failed lookup is
retained. Evidence: native `voxel-airport-terminals-first-review`,
`voxel-airport-terminals-refined-review`, `voxel-airport-terminals-final-opengl`,
Linux `voxel-airport-terminals-city-validation` and
`voxel-airport-terminals-refined-validation`. All models remain WIP; aircraft traffic,
clearance, precise source detail and later company/climate/LOD passes remain.

## Radio and passenger-pier follow-up

Source metadata now records actual indexed colour use. It confirms neutral32…38
pier panels and original239/240 radio beacons; company colour belongs to the separate
fence. The radio's lattice, guy wires, panels and antenna are explicitly authored on
a0.25×0.25×1 grid. A bounded canonical voxel-line operation preserves face-connected
diagonals and reversed-endpoint identity. Piers retain raised support gaps and distinct
tee/elbow/link layouts. Source palette refinement keeps37 highlights on the elbow/link
family and38 on the tee.

Evidence: native `voxel-radio-first-review` (model views useful, beacon observation
failed), `voxel-radio-palette-diagnostic` (retained diagnostic failure),
`voxel-radio-palette-corrected`, `voxel-piers-refined-opengl`; Linux
`voxel-piers-first-validation` and `voxel-radio-corrected-validation`. Actual city
tiles25(67,34),26(68,35),27(67,36),28(66,35),32(65,37) are captured. Corrected radio
checks observe three paired phases from both emitted beacon indices. Source precision,
fine members, joins, aircraft interaction and later lighting/angle/LOD passes remain.

## Terrain and railway fence passes

`terrain_geometry.hpp::MakeFenceMesh` authors seven palette volumes: hedge, hedge
with gate, white timber, cream/coral flowering hedges, stone wall and railway chain
link. Field bodies use half-unit XY cells; gate/board detail uses quarter units;
close chain wire uses eighth-unit XY/quarter-unit Z cells. Feet sample the terrain
over each cell footprint and embed below it; faces remain axis-aligned. Raised
diagonals retain the upstream corner height. Fine wire has face-connected steps.

Source review corrected six-unit generic heights to three-unit white timber,
3.5-unit gates, five-unit chain link and4.5–5-unit hedge/stone crowns. Palette cells
replace projected source charts. Later review replaced short repeated foliage rows
with deterministic local grain and less regular stone joints. This does not consume
simulation RNG. Crown silhouettes, foliage depth and dry-stone character still need
later source-scale refinement; current green/stone surfaces remain visually simple.

Reviewed all seven four-sided street sheets in `voxel-fences-all-family-review` and
`voxel-fences-refined-validation`, then the corrected hedge/gate/blossom/stone sheets
in `voxel-fence-corner-agreement`. `voxel-fence-half-tile-validation` on macOS/Linux
adds individually selected diagonal fences, actual raised surfaces and retaining
walls. `--gallery-fence 6 --fence-slope 33 --fence-layout 2` selects the raised west
half-tile example; `contact_sheet.py <directory> --gallery --fence-style 6
--fence-layout 2 --street --tight` selects its four eye-level views.

A30-pixel full-gallery difference during gate consolidation exposed conflicting
colours on overlapping hedge caps. A ray regression reproduced six failures on
flat and inclined corners. Shared corner grain now agrees; this is an intentional
join correction, not a tolerance exception. The one-volume gate matches the
corrected two-part reference exactly in isolation and complete perimeters, including
640×640 orbit/street checks. Four gate edges now use4instances instead of8 and
39,960 rather than41,748 close vertices (24,576 rather than26,688 at farther LODs).
Sloped railway sprite aliases share the same slope-keyed edge mesh.

Final native Vulkan/GL and Linux Vulkan core/synchronization checks pass **828**
views: all families, vanilla slopes, three detail levels, all16 railway layout slots,
12raised diagonal cases and full-size gate comparisons. These establish exact
palette/instance/reference/picking behaviour, not identity to original sprite art.
Actual field families were located in the generated1970map; the traffic fixture
supplies real railway fences. The locator's initial non-field-ground assertion and
earlier corner/draw-order differences remain recorded failures in `VERIFICATION.md`.

Still required: precise source silhouettes and colour distribution, mixed-family
corners, climate/company variants, later moving LOD/Cab passes and production-level
neighbour consistency. **No fence family has final visual approval.**

## First voxel aircraft checkpoint (2026-09-23)

`aircraft_dinger_100` is explicitly authored on a0.5×0.5×0.5 grid, facing+X.
Engine238 state0/1 bindings share geometry because the original empty/loaded sprites
are identical. `DrawVoxelVehicle` retains original smooth position/heading, company
palette, opacity and IDs; resolved base-sprite provenance gates the authored route.
`--verify-voxel-vehicle 238` requires actual world capture of that engine.

`contact_sheet.py <source-directory> --vehicle-source 238` shows all eight directions
and both source cargo states. Source, orbit and street passes reduced oversized
engine pods/wheels, narrowed swept wings and removed broad erroneous highlight bands.
`voxel-aircraft-wing-review`, Linux `voxel-aircraft-wing-validation` and native
`voxel-aircraft-final-wing-opengl` pass1,896 model views and192 continuous-heading,
company-palette/cargo, CPU-instance and transparent-picking comparisons.
`voxel-aircraft-held-final-0`…`-3` repeat actual airport views with the voxel body;
some views are naturally occluded. Earlier `voxel-aircraft-stand-view-*` predate it.
`voxel-aircraft-cab-6000` runs the operating aircraft, but retains24 work overruns.
Only cargo0 has an actual emitted-world marker so far; synthetic cargo1 agreement
does not prove live loaded/crashed states. Proportions, fine shadows/markings, gear,
all clearance/state cases and final fidelity remain open. No visual approval.

Later palette follow-up extends the pose matrix to all16 company tables and the
original crash recolour, for1,088 views. An untextured colour oracle applies upstream
tables directly to authored indices, independently of voxel palette strips and atlas
sampling. Native Vulkan/Linux GL match colours and IDs exactly. Actual loaded/crashed
gameplay and effects remain separate open state checks; palette agreement is not
source-shape or final visual approval.

## First standalone tree family (2026-09-23)

`tree_lime_00`…`_06` bind all seven original stages of family1576. Unlike the older
component-tree fallback, each lifecycle shape is explicitly authored, including
actual empty space around dying branches. The detail grid is0.25×0.25×0.75; source
review shortened the initially over-tall1-unit vertical grid. Roots/branches are
face-connected, foliage uses80…86, bark105…109 and living lower crowns retain source2
deep shadows. Later passes soften broad material bands, add coarse bounded grain,
fill out the mature lower skirt and reduce the remaining late-stage leaf clusters.

The optional `scatter_paint` colour-block size groups the coordinate hash before
painting, preserving occupancy and optional material masks. It is deterministic
authoring data, not image-derived geometry or game RNG. Compiler tests cover shared
block colour, protected materials/open cells, invalid sizes and all seven authored
trees' connectivity/progressive foliage loss/bare-stage palette.

`contact_sheet.py <directory> --tree-source 1576` displays all stages/palettes at one
source scale. Tree reference manifests include actual indexed colours and framing.
`--reference-tree 1576 STAGE` / `renderer3d tree-locate 1576 STAGE` use original layout
and per-tile growth rules read-only. Whole-family base-sprite provenance gates the
voxel path; palettes, transparency and tile ownership remain upstream-driven.

Evidence: native `voxel-lime-first-review`, `voxel-lime-refined-review` (GL),
`voxel-lime-stage-{1,2,4,5,6}-live`; Linux `voxel-lime-first-validation` and
`voxel-lime-refined-validation` (stage0/core/sync). The ordinary1970world supplies
stages0…6 at(141,116),(139,117),(121,135),(121,121),(134,111),(126,115),(121,139).
First review selected a map-edge tree; the refined locator prefers readable interior
single-tree tiles. Some forest views remain occluded by unconverted neighbours.
Four-sided street and `context-tree-1576-neighbours` galleries compare the tree with
townhouses/compact offices. These are repeated WIP passes, **not final approval**.

Runtime verification checks168 exact tree state/palette/scale/camera views in
addition to the catalogue's2,064 merged/unit-cell comparisons. The remaining61
component families retain5,460 older lifecycle/LOD checks; those are not voxel
coverage. Explicit tree LOD and subsequent complete-scene performance review remain.

## Silver column and native-scale follow-up (2026-09-23)

Family1583 adds seven `tree_silver_` volumes, including the original shorter final
dead shape rather than merely hiding the living crown. Source colours are96…102
foliage and104…109 bark. Its stages0…6 were located/captured at(164,140),(127,128),
(139,160),(120,118),(116,133),(130,129),(128,136) in the same ordinary1970 world.

Native-scale review uses a distant virtual canvas at the fixed40° lens, cropped to
96×96; no large framebuffer is allocated. Black ground hides embedded root cells.
`contact_sheet.py <gallery> --tree-comparison BASE --source-directory <references>`
compares all seven source/model views at5× nearest pixels and records image bounds.
This exposed widened crowns from colour ellipsoids and overly dense dying fronts.
`ellipsoid_paint` changes only existing cells; it cannot enlarge the silhouette.
Explicit diagonal gaps expose connected branches, while original shade ramps gain
small deterministic clusters. Both the lime and silver families received these
later source/orbit/street/context passes.

`voxel-columns-final-scale-review/renderer3d-reference/tree-*-source-comparison.json`
records matching overall native-scale dimensions for all14 states. **Matching bounds
is not matching every silhouette/material pixel, nor final visual approval.** Fine
foliage placement, bark highlights, source-style asymmetry and further LOD/context
review remain. Earlier comparison images deliberately retain their mismatches.

Evidence includes native `voxel-silver-first-review`, `voxel-trees-native-scale-review`,
`voxel-columns-shading-review`, `voxel-columns-silhouette-review`,
`voxel-columns-grain-review`, `voxel-columns-final-scale-review` and
`voxel-silver-stage-{0,1,6}-live`; Linux corresponding first/shading/grain/final-scale
validation runs. Current336 exact voxel-tree views are separate from5,376 older
component views for the remaining60 families. Geometry is manually authored throughout.

## Drooping spruce: active review

`tree_spruce_00`…`_06` are the first pass for family1590. Explicit connected lines,
hanging needle blocks and baked radial rotations retain actual space between boughs.
A connectivity regression caught cardinal supports cut by dying-state openings;
restored woody connections pass without weakening the test. Mature brown spokes and
thick needle blocks were reduced in the next pass; the bare branch spread was widened.

Native `voxel-spruce-first-review`/`voxel-spruce-refined-review` and Linux corresponding
validation runs pass renderer/tree/picking and core/synchronization checks. Actual
stages3/4/5/6 are captured; `voxel-spruce-stage-{0,1,2}-live` adds targeted native
early-stage captures, so all seven states now have initial gameplay evidence. The current
native-scale comparison still differs in several bounds, and the boughs remain too
regular/bulky compared with the original drooping sprays. This is **active WIP**, not
an approved or completed fidelity pass. Source-scale views now carry an ID-derived
alpha mask, preserving genuinely black leaf pixels when cropping review images.

## SH30/SH40 and spruce follow-up (2026-09-23)

`rail_sh_electric` binds engines23/24, empty/loaded. Original source images are
identical across both definitions, including their opposite-direction symmetry.
Native source export now includes actual indexed colours, offsets and dimensions.
Vehicle comparison sheets use eight native-scale directions; several proportions
still differ, so no source-perfect approval is claimed. Pantograph diamonds remain
open and connected to the roof; wheels/buffers/roof members pass connectivity checks.

`fixture_rail.py --train-engine 23` selects the available engine through NoAI; add
`--train-hold` to stop it near the east terminus after the verified route. The manifest
records actual engine/held state. `--reference-vehicle 23` locates a visible instance
and requires actual voxel capture. Held SH30 and SH40 fixtures retain their own AI.
Four SH30 orbit captures include a clear station/track/wire view; others are tree-
occluded. Source, orbit, street and later roof passes are in `voxel-sh30-first-review`,
`voxel-sh30-roof-refined`, `voxel-sh30-held-view-*` and Linux corresponding validation.
Official15.3 round-trip/reload and a6,000-frame moving Cab test pass scoped checks.
They do not prove coupled-car clearance, every grade, crash gameplay or final fidelity.

Spruce artifacts `voxel-spruce-needles-review`, `-open-bough-review`,
`-staggered-review` and Linux `-staggered-validation` refine connected drooping
strands, radial overlap and intermediate tiers. Fine needle placement, natural
asymmetry, exact source bounds and later complete-scene review remain WIP.

## Footprint/ground extension review (2026-09-24)

`inventory.py --footprints` reports occupied world bounds, contact bounds/area and
outside-tile review prompts. All `footprint_reviewed` flags remain false; legitimate
roof/rope overhangs need original-layout review. Red-Z-office/site origin moves(6,5)
to(5.5,4.5), mine headgearY−0.5→0, engine-house/siteX−1.25→−1. Ground contacts stay
inside the tile with shapes intact. Earlier exact mine registration records predate
these shifts and cannot establish current alignment approval.

House source exports now include ground images/palettes/offsets. Use
`--house-source 14 --house-layers` or `--house-comparison 14 --registration` with
`voxel-house-ground-alignment-source/renderer3d-reference` as source directory.
Latest `voxel-shops-open-construction-final` contains the layered four-stage comparison,
shell turntable, street neighbour sheet, actual stage1 and current inventory. Earlier
1980 lookups correctly found no1930–1960 house14; ordinary1950 generation supplies
all stages without map-state edits. Final construction cuts remove inherited window
sashes and keep dark open rooms. The runtime-style ground UV path still renders62×32
versus64×31 original; full16×16 coverage is retained and the discrepancy stays open.

Terrain correction puts the first substrate at map height and selects matching
half-unit edge samples only at voxel/rough Toyland contacts. Initial732 missing pixels
became one after height correction, then zero after conformance. The final independent
continuous-plane oracle covers24 flat/two-ramp/rotation/origin views and rejects any
interior sky hole or insufficient reference coverage. Native Vulkan/GL and Linux
Vulkan/core/sync/Arctic GL pass. This does not approve every half-foundation/overlay
or convert all terrain to voxels. See `VERIFICATION.md` and `PERFORMANCE.md`.

The later bundled-app `voxel-extension-mine-placement-review` passes actual graphics2
stage3, industry/ground/picking checks and exports the original joined mine layout.
Source, street and gameplay images were inspected after the containment shifts.
Engine-house comparison now measures49×24/49×41/50×42 for site/frame/completed versus
48×23/48×40/49×41 source. These one-pixel extent/registration differences are retained;
fine wall/window contrast, corrugation and ground grain remain in the defect list.

## September24 power-station/source pass

Mine `voxel-mine-facade-material-review`/`voxel-mine-openings-refined` correct the
light facade to source57, darker faces to108/107 and enlarge openings whose recessed
glass disappeared in the native view. Street views retain actual recesses, sills and
painted lintel shadows. Linux `voxel-mine-openings-validation` passes; previous engine
house one-pixel bounds differences remain and fine material/facade fidelity is WIP.

Power-station references are in `voxel-mine-ground-source-reference`, tiles7…10.
The new public-NoAI `voxel-power-station-construction-fixture` funds original type1
and saves ordinary elapsed0/16/30/44days, retaining its own AI. `voxel-power-cooling-first-review`
exposed dark interior material appearing on exterior staircase cells. Explicit
`lathe_paint_inner` now recolours only cavity-bordering faces, retaining exterior
grain/occupancy/top rims; deterministic inward grain avoids axial colour striping.
The initial detached pier was corrected before rendering. These are authored profiles,
not image-derived geometry. `voxel-power-cooling-inner-face-review` retains the fix.

`voxel-power-boiler-first-review` and `voxel-power-boiler-refined-review` correct roof
overhangs, height, wall contacts, marker selection and a previously filled narrow flue.
Latest `voxel-power-source-refined-final` has source registration, street/context,
actual stage1 and inventory; Linux stage0/stage2/core/sync checks pass. Boiler frame
50×48 and completed50×58 bounds and original tile offsets agree; this is not a pixel
match. Cooling remains44 pixels wide versus43, and its early state is one pixel taller.
Its ground contacts stay within the source(1,1)…(15,15) region across all stages.
Body8's source2048 is a transparent1×1 image: no stage0 body is introduced. Comparison
sheets explicitly label absent exports for transparent sources, never a fabricated
passing mesh. At this checkpoint auxiliary9 and transformer10/sparks were still unbound;
the later pass below adds them. Fine fidelity and final approvals remain required.
Ground7/8 uses the same original3924 soil as the mine site.

## Visible-source/ground audit follow-up (2026-09-24)

`voxel-visible-source-audit` retains fresh source exports, all145 model galleries,
all selected house variants, ground-only early civic/park stages and current inventory.
Industry comparison records distinguish `original_carrier_size`/carrier placement
from alpha-visible dimensions. This exposed transformer10: a64×74 carrier contains
46×49 visible artwork. The oversized first gantry was corrected; support flanges and
tile placement now match the visible source bounds. Remaining steel/core/coil geometry
and spark shape/halo differences are plainly visible and remain WIP. Original2059 and
2060 RGBA are identical; their differing native offsets are preserved in separate poses.

The source/state/street passes on auxiliary9 corrected four initial banks to the actual
three, added the source brick casing/side pipes, softened hood bands and lowered its
roof eave. Its26×26 construction and33×39 completion bounds/placement now agree. A
boiler regression also restores masonry gables after roof removal. Original blank
stages remain absent. Parent/child coincidence no longer depends on mesh addresses;
the first1-pixel GPU/CPU failure and later exact layer checks are retained.

The four-stage layered audit was rerun for all15 house IDs. It does not award approval.
Key next-pass findings (model roof/top relative to original, native pixels): tall office0
about2–3px too high; red-Z1 about1px high; church3 construction2px high but completed
top2px low; offices4/5 about1–2px high; townhouse6 and hotel7/8 tops around1px low;
fountain10 top2px high; pond park11 top1px high; autumn park12 top4px low and its path/
crown/shadow shapes remain visibly different; compact-office13 shell2px low. Statue9,
completed13 and shops14 top bounds agree but materials/silhouettes remain unfinished.
Most ground planes remain62×32 versus64×31 source; park volumes have their own64-pixel
footprint/raster differences. Preserve real playable coverage while investigating
native raster phase and source-aligned materials. Matching full carrier rectangles
or isolated silhouette sizes is not sufficient evidence of footprint alignment.

## Complete-scope queue

### Foundation and transport follow-up (2026-09-23)

All **13 common foundation forms** now use authored rubble volumes, covering the
**66** leveled, inclined, half-tile, two-level and special railway combinations in
`foundation-cases.json`. Source export now includes **104 foundation sprites**:
14 original, 74 additional slope/wall variants and 16 half-tile variants. Geometry
is derived from upstream foundation surfaces and explicit cell rules, not images.

Close support cells are **0.5×0.5×0.25**, middle **1×1×0.5**, distant **2×2×1**.
Columns fit below the playable upper surface and embed into the original soil.
Non-rendered occupancy cells hide soil contacts and upper caps before meshing, so
grass/roads do not acquire a coplanar stone overlay. These masks also make merged
and unit-cell hidden-face decisions identical. Distant grids retain their cell quads:
an earlier long-triangle version changed one visible pixel/ID at subpixel scale.

Repeated source/orbit/street review refined the tan/grey/dark rubble mix, stone
proportions and highlights. Diagonal retaining walls initially showed alternating
light/dark microstep stripes. Their exposed X/Y steps now share the authored coarse
wall light ramp; four-direction mesh-ray colour checks cover that correction.
The cells remain axis-aligned. Gameplay slopes, commands, RNG and map state are
unchanged; custom foundation sprite replacements retain their original drawing path.

Review artifacts: `voxel-foundation-first-review` (useful first images, failed strict
verification), `voxel-foundation-rubble-review`, `voxel-foundation-diagonal-refined`,
`voxel-foundation-road-opengl`, `voxel-foundation-final-opengl` and Linux
`voxel-foundation-diagonal-validation`. Every form received an orbit/context pass;
street sheets include all half-tile directions and actual building/track interfaces.
The real voxel-house foundation is at **(215,13)** in the normal1970 map; the title
map supplies railway foundation12/slope12 at **(203,19)**. The older levelled traffic
fixture contains no qualifying rail foundation; its failed lookup remains recorded.

Source precision, stone relief, shared-tile joins, detailed sloping top-edge contacts,
all-climate variants and later moving LOD review remain. Actual town screenshots
also visibly expose unconverted neighbouring house/tree materials; these are still
part of the complete migration. **No foundation form has final visual approval.**

The wide title benchmark exposed excessive transport geometry. Far flat straight
running sections now reduce longitudinal subdivisions while preserving the exact
quarter-unit cross-section and eighth-unit height grid. Near/middle, diagonal,
graded and maglev-junction models retain their previous grid. Ray probes compare
the full running-head cross-section; expanded GPU coverage is8,240 views. The wide
run improves from about35.8 to37.8fps but still fails the target. The new component
census identifies further running-rail/fence/tree geometry reduction as active work.

Construction follow-up: six new volumes provide the office site/open frame, flats
site/shell and church masonry/roofing stages. Repeated review removed residual office
glazing through explicit material erasure. Galleries, neighbouring scenes and actual
generated-world states were inspected. Source metadata now includes sprite framing.
`voxel-house-{1,2}-stage-{0,1,2}-live` and church stage1/2 captures find real 1970-world
states; the earliest church uses the separate 1950 save in
`voxel-church-construction-ordered`. No map state was edited to create a stage.
Some early captures predate the scripted camera ordering fix and are not final
framing evidence. `voxel-flats-construction-review` and the ordered church capture
show the corrected final view. All models remain WIP: masonry variation, openings,
exact proportion/source matching and later street/context passes remain required.

| Category | Current voxel coverage | Required coverage |
| --- | --- | --- |
| Houses | 28 / 110 definitions,392 nonempty source-aware body bindings,8 permanent ground definitions; original blank civic/park/stadium stages retained; zero approved | Every definition, variant, construction state, animated part and multi-tile join, with final individual review |
| Industries | Bodies8 / 175 tile definitions, eleven ground bindings and six spark child poses; zero approved | All construction, operating/animated, cargo and climate variants |
| Vehicles | 35 / 256 initial bindings, two cargo states each;32/88 road definitions; zero approved | Bodies, running gear, all directions, company/cargo/livery, crash and animation states |
| Trees | 7 / 62 initial family bindings,49 volumes; zero approved | All seven lifecycle states, climate/snow/palette variants and detail levels |
| Airport tiles | 18 / 74 definitions bound; all frames of the five animated radar/flag definitions and original radio beacon palette entries; zero approved | Every building, apron/runway, fence, radar, flag and helicopter-infrastructure/animation state, plus final source/context approval |
| Railway | First voxel running assemblies for all four systems; zero approved | Later source/state/LOD passes, switch/frog/slab detail, all bridge/depot/crossing integration and climate variants |
| Other transport | Depots5 / 6 families, four directions and separate source/weather floors; zero approved | Roads/trams, stations/stops, remaining depots, signals/catenary, bridges/aqueducts, tunnels, docks, locks, buoys and other water infrastructure |
| Terrain and details | Seven fence families and13 common foundation forms have initial voxel volumes; zero approved | Final fence/foundation fidelity, joins and climate/context review; every terrain surface, field stage, rock/snow, grass/rough/desert/shore and water presentation |
| Objects/effects | Power-station sparks have six initial voxel poses; zero approved | Headquarters/stages, landmarks/objects, smoke, remaining sparks, rotors, wakes, explosions and other original effects |
| Consistency/performance | 243 volume/frame models, four running-rail systems, seven fence families and13 foundation forms; wide GL46.7fps/Vulkan53.7fps, with sustained/foreground targets still open | Individual/source, footprint/ground, street/Cab, neighbour and live passes for every category; complete-scene LOD, memory and sustained performance |

Next work should expand the highest-visibility missing categories (including
railways and airports) while continuing every converted building's fidelity/state work.
The presence of a voxel volume is never a substitute for the required repeated review.

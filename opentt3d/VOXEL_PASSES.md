# Breadth-first voxel development passes

## September 26 rendering-priority update

The follow-up instruction supersedes the earlier strict voxel requirement for
**trees and roofs**. Terrain steps render at2× their original height; object
dimensions and simulation coordinates retain their existing scale. Sloped roof
surfaces are permitted wherever they better reproduce the original structure and
paint. LOD meshes must be generated automatically, not authored as separate models.
Matched performance remains poor with voxel-tree LODs, so the previous projected
material3D trees are restored as the normal path. Their existing lifecycle/climate
and source-fidelity checks still apply; voxel tree data remains diagnostic history.
All other catalogue, footprint, contact, state and fidelity gates below remain active.

## Active work window and complete goal

- Strategy recorded **2026-09-24 05:31:32 UTC**.
- Work at least until **2026-09-26 19:00:00 UTC /1PM CST September26**. Earlier deadline
  audits do not satisfy this minimum. Check the actual clock before ending the window.
- Updated window recorded at **2026-09-26 00:53:04 UTC**. The earlier00:51:14UTC audit
  does not satisfy this extension. Catalogue-wide Pass1 and the complete quality/
  performance objective remain unfinished.
- Final clock/process audit: **2026-09-26 03:07:14 UTC**. The requested minimum has
  elapsed; this work window ends for that reason. Catalogue-wide acceptance and the
  entire multi-pass objective remain unfinished, with zero final visual approvals.
- **New extension recorded03:09:04UTC September26:** the03:07 audit belongs to the
  previous window and does not satisfy the19:00UTC minimum. Continue breadth-first
  implementation; publish frequent verified commits/pushes/main integration and at
  least daily/noteworthy development releases. Keep native review windows backgrounded.
- The severe tree throughput regression and complete catalogue/quality objective
  remain required work; subsystem completion is not a reason to end the window early.
- Recreate every original world asset and relevant state as faithful voxel artwork,
  including already modeled assets: houses, vehicles, trees, industries, every railway
  system, airports, stations, depots, bridges, tunnels, roads, water infrastructure,
  terrain, objects and effects. Include construction, climate, variant, animation,
  cargo, crash and other applicable states and multi-tile joins.
- Final quality remains source-comparable first-glance/pixel fidelity, coherent
  all-angle/street/Cab geometry, original footprints and ground alignment, consistent
  scale, source shadows/recesses/highlights/markings/material character and sustained
  smooth performance. Completion is unproven; keep playtesting and finding defects
  if the objective appears complete before the minimum.

## Pass gates

1. **Complete basic coverage first.** Every asset/state needs recognizable voxel
   geometry, correct dimensions/orientation/placement/contact footprint, dominant
   source colours, essential structures/openings, original selection/palettes,
   visibility/picking and essential vehicle/door/track/infrastructure clearances.
   Preserve original empty states. Share geometry only where original differences
   permit it. Generic boxes, stretched placeholders, billboards and retained
   non-voxel fallbacks do not qualify as completed voxel coverage.
2. **Structural fidelity across the catalogue.** Refine roofs, windows, doors,
   supports/machinery, vehicle bodies/running gear, tree crowns/branches/lifecycles,
   construction/animation shapes, joins and neighbouring/infrastructure interactions.
   Review real source art and preserve established placement/footprints.
3. **Artwork and pixel fidelity across the catalogue.** Restore painted shadows,
   recessed shading, edge highlights, glass/reflections, masonry/roof/vegetation
   patterns, markings/fittings/weathering and consistent palette/material scale.
   Correct remaining source silhouettes and registration.
4. **Production review.** Systematically inspect source/all-angle/street/Cab views,
   isolated/adjacent/gameplay scenes, every state/climate/variant/layout, transparency,
   picking, clearance/transitions, performance and memory. Continue correcting defects
   until the entire objective is supported by evidence.

Do not advance a small group through repeated cosmetic passes while large unconverted
categories remain. Prioritize common/highly visible and straightforward families;
include representative complex assets early to expose integration/tooling defects.
Reuse genuinely shared source structures. Existing detailed models retain their
current quality and participate in the same catalogue-wide audits.

## Pass 1 coverage checkpoint and queue (2026-10-02; 1,782-volume effect-breadth checkpoint)

Latest effect-breadth increment reaches1,782 volumes: four roadworks orientations,
eight chimney, five train-steam, six diesel-exhaust, six electric-spark and five shared
charcoal-smoke states plus sixteen large-, twelve small-explosion and four breakdown-smoke
states plus fourteen bubble states bind80/80 presentable effect sources through320
climate bindings. Bubble threshold4754 stays unbound; it is never presented upstream.
Five spark volumes
preserve a source-proven identical final pair with separate original timing. Original
lifetime/motion controls and fixed-anchor source bounds are recorded in `VOXEL_REVIEW.md`;
Fourteen source-specific bubble rims/fragments now have integrated artwork. Large explosions retain their
source-sized ignition, visible fork/crown openings and detached late fragments. The
twelve small-explosion states match source bounds, retain the filled early core and
genuine later opening, and clear the original two-unit flat-ground emission datum.
Ordinary single-tile clear-area commands supply complete48-phase small lifetimes;
the random train-crash context remains unobserved. Twenty integrated graphical/regression/
fallback executions pass; the cold Vulkan replay misses one phase and remains a failed
complete-lifetime control. Nine complete lifetimes are accepted individually.
Four breakdown-smoke states match source bounds and retain separate genuine volumetric
puff chains, gaps, detached knots and blue/warm motes. The original five-unit emission
altitude, stationary spawn and random failure countdown remain unchanged. Their staging
audit retains nine complete original countdown lifetimes from twelve replays, including
eight-bit progress wraps and both pool orders. Three missing-phase failures remain
preserved; four paused/disabled absences pass. Twenty-seven integrated graphical/regression/
fallback executions pass, with7,983 observations and nine independently complete lifetimes.
Both integrated Toyland replays and higher-pool OpenGL miss phases and remain failures.
Fourteen bubble states match all native source bounds and retain connected rounded
XYZ rims with genuine bores, separate reflections and eight free volumetric rupture
knots. All27 integrated graphical/regression/fallback executions pass; both fresh
backends retain complete independent burst/absorption lifetimes.12,046 observations
and eight complete lifetimes (six bursts/two absorptions) are recorded. The earlier
cold-OpenGL staging absorption misses nine phases and stays failed. All preceding
models/material faces/owners and earlier source/model captures remain exact.
These additions preserve all preceding volumes and do not complete the catalogue-wide
Pass1 gate or establish final visual approval.

These counts describe existing bindings, not automatic Pass 1 acceptance. The detailed
evidence/defects remain in `VOXEL_REVIEW.md`, `VERIFICATION.md` and `PERFORMANCE.md`.

| Category | Existing voxel bindings | Pass 1 coverage work |
| --- | --- | --- |
| Vehicles | 256/256 engine definitions, including35/35 locomotives,88/88 road,81/81 wagons,11/11 ships and41/41 aircraft with four rotor states and three independently mounted train collector volumes | Flat-body tunnel gauge repaired; slope/curve wheel contact, contextual station/depot/bridge/Cab clearance and all-family source/dimensional work remain; bindings do not establish Pass1 acceptance |
| Houses | 110/110 definitions with body or ground geometry;109 body definitions and88 ground definitions | Final source/state/variant/join/ground audit and catalogue-wide later fidelity passes; bindings alone do not establish Pass1 acceptance |
| Trees | 62/62 families,434 lifecycle volumes, including all Arctic snow and nine Toyland families | Source-proportion/branch-shape and per-stage palette corrections, complete actual-state/climate review and the severe wide-view throughput regression remain; bindings do not establish Pass1 acceptance |
| Industries | 175/175 primary definitions with body or ground bindings:129 body owners,175 grounds | Basic layer bindings include eight plastic poses, fizzy bubble palettes, four factory children across50 frames, bubble-generator children across40 frames, toffee's70-frame cutter/shared redraw and sugar's15 children across96 frames with genuine absences. Six Arctic forest and twelve Arctic farm models bind independent body/ground states, passing actual construction/cargo and forest harvest/regrowth. Non-temperate industrial grounds, other distinct climate artwork, remaining procedural children and complete source/state/layout acceptance remain.268 original child-state references are exported; source export alone does not establish voxel coverage |
| Airports | 74/74 primary tile definitions:56 body owners and18 ground-only definitions;74 independent grounds | Elevated heliport44, four-climate taxiway/grass/worn-airfield/small-runway surfaces and radar/windsock grounds are bound; independent Toyland terminal/hangar artwork, exact lamp phases and complete source/street/layout acceptance remain |
| Depots | 6/6 families,24 directional bindings | Tram body/floor/wire bindings now cover the missing family; all-family source/ground/vehicle clearance and later fidelity review remain |
| Rail systems | Four running assemblies | Remaining signals/catenary, station structures, bridge/tunnel systems and state integration |
| Other transport | Both ship-depot axes/four voxel sections; six dock sections/twelve ordinary-Toyland volumes; separate source-resolved ordinary/Toyland buoys | Roads/trams/stops, locks/aqueducts and remaining infrastructure; full water-class/ship/bridge fidelity and clearance review |
| Terrain | Seven fences,13 foundations | All remaining ground/detail/water/climate/seasonal surfaces and transitions |
| Objects/effects | Five original transmitter/lighthouse/owned-land/normal-statue/Toyland-gnome volumes with13 climate bindings, six power-station spark poses, four original helicopter rotor states and80/80 presentable effect sources through320 climate bindings | Headquarters ground/body, locks, rivers, disasters, wakes and remaining procedural objects/states; source/all-angle/emission-context fidelity remains open. The original-object source inventory records24 tile layouts/five HQ sizes and11 HQ ground-only slots. Complete bindings and short native controls do not establish Pass1 acceptance or8/10 quality |

The1,092-volume catalogue adds four bus bodies, eighteen closed road-cargo bodies,
twelve rail-depot bodies/four floors/one wire, and28 cactus/palm lifecycle volumes
plus15 commercial-house volumes,16 stadium stand/pitch volumes, six ship families
and four ship-depot sections/twelve dock volumes, plus five old-house/cottage and
eighteen suburban/flat construction volumes, twenty-eight open-road cargo states and
thirty-three Arctic/tropical road volumes, sixteen Toyland open-cargo volumes,
twelve city-house volumes,32 closed-wagon volumes, seven olive-column tree states,
twelve suspended-office/Arctic house and ground volumes,63 Toyland tree states,
cinema/pavement, two resolved navigation-buoy climates and twelve shopping-mall
construction/roof/ground volumes, ten Arctic flat/house/ground volumes and21 cottage/
glass-office/ribbed/setback tower volumes, twelve cabin, ten shop/church and sixteen
small-house/corner-shop/joined-hotel volumes,21 late Arctic office/tower volumes and
17 tropical house/hut/flats/church volumes,21 final tropical house/tower volumes,
52 Toyland house/ground volumes,315 temperate/Arctic/tropical tree lifecycle volumes
and17 ordinary fixed-wing/eight remaining aircraft bodies plus four rotor volumes,
45 ordinary-climate open-wagon volumes and16 independent Toyland wagon volumes to the145-volume
strategy baseline. The previous detailed models retain their
quality. All17 company/crash palettes, continuous vehicle poses, tree-state binding,
invisibility/picking and root/door connectivity have technical checks. Normal public
fixtures provide actual fleet movement and lifecycle observations.

The33 ordinary fixed-wing aircraft share eighteen bodies only where their original
direction/cargo sprite arrays match. FullGL/Vulkan fleet matrices pass; source sheets
retain wing/fin/fuselage/shading/diagonal differences for the later catalogue pass.
All41 aircraft service actual destinations in public NoAI fixtures. Toyland aircraft
have separate climate bindings, and each helicopter passes actual four-state rotor
stop/restart and ground-contact observations. Source fidelity and full airport/Cab
clearance remain open. All81 wagon definitions now have bindings;69 newly bound
engine/climate cases are captured in twelve normal consists. NativeGL/Vulkan each
pass68,544 new wagon poses. Source sheets retain side/diagonal proportions, bright
uniform paint, simplified ribs/cargo grain and canopy/coil detail for later review.
Sixteen freight routes pass actual full loading, accepted delivery and return with
32 saved full/empty captures. Toyland fizzy drinks now also passes observed bubble-input
delivery, full loading, accepted town delivery and both saved states onGL/Vulkan.
Five loaded/empty freight routes pass real bridge/tunnel traversal; complete rendered
contextual clearances remain open. All35 locomotives now have bindings and all55 climate/railtype service
fixtures/captures pass. The1,133 repair clears the faceted tunnel gauge and independently
fits the electric collectors; fullGL/Vulkan matrices pass. The1,144 sawmill addition
preserves original construction differences, completed-only log/board piles and all
five independent grounds. The1,169 candidate adds six forest and19 refinery volumes:
four nine-pine growth bodies, production logs/stumps/litter, six refinery construction
families and independent soil/paving. Both backend forest cycles and24 actual refinery
construction selections pass. Source/street findings remain in `VOXEL_REVIEW.md`;
the1,180 oil-rig checkpoint adds11 volumes, all20 actual construction selections,
registered six-tile layouts and actual helicopter253 support/rotor observations on
both backends. The1,247 checkpoint adds67 volumes for oil-well29…32, farm33…38,
bank58/59, food60…63, paper64…71, plantations116/117, waterworks118…120 and airport
63/64/69. The88-run actual industry sweep verifies288 independent grounds,242 body
selections and46 original empty selections onGL/Vulkan. Later source comparison
revokes the eight Arctic farm runs:40/44 original layers differ, and independent
Arctic volumes remain missing. The renderer retains their supplied artwork. The
remaining80 runs validate240 grounds,198 bodies and42 original empty states,
including both food climates. All eight electric-engine curved-route/contact observations pass.
The expanded323-pair source audit also identifies missing Arctic snow-forest bodies/
grounds and independently painted non-temperate soil3924/oil-well2173 grounds.
Those source layers are retained until independently authored variants exist;
matching coal/power/refinery/oil-well bodies retain their own voxel ownership.
Catalogue breadth, final fidelity and production performance remain unfinished.

**Pass 1 remains incomplete.** New bindings do not automatically establish correct
source dimensions/ground registration or every clearance. Bus/van diagonal/profile
differences and remaining palm one-pixel bounds stay recorded; cactus bounds-only
agreement is not pixel fidelity. Full catalogue migration takes priority over
cosmetic leaf/rib/roof/masonry passes. Next: continue unconverted
industry/infrastructure/vehicle/tree groups. The first commercial batch preserves
original early-state differences and all actual stages; finer modules/rooflights/
window/paint work and the common62×32 versus64×31 textured-ground raster discrepancy remain.
Both stadium families preserve empty first-stage bodies, permanent full-tile voxel
pitches, four-tile ownership/joins and original crowd/scoreboard palette animation.
The new final tropical/Toyland group has132 actual state/recolour captures in total
(36 tropical and96 Toyland); corrected Toyland
geometry passes the corrected96-case sweep. The boot gift's ground overlap and unsupported handle/
pavilion parts are fixed, with exact32 joined views. Later source comparison still
requires gift-bow shape, roof/window/crown proportions, source-painted shade/grain,
sign lettering and palette fine detail; zero approvals remain.

The315 newly added tree volumes pass rooted-support checks after repairing cut-off
dying-crown fragments and cedar leaders. Source/native comparisons expose overly wide
young Arctic crowns, insufficiently spreading bare forks, regularly tiered/rounded
crowns rather than original asymmetry, overly solid fan-palm leaves and incomplete
stage-specific source palette choices. These are open source-fidelity/Pass1 issues,
not accepted final artwork. Snow-side selection and dead succulent palette ramps are
corrected immediately; tall-source review framing now preserves the full tree.
NativeGL exact checks cover all three new groups; complete tree verification covers
24,528 lifecycle/palette/scale and20,832 distant views. Actual cedar1667/mature,
snow-pine1765/mature and peach-palm1926/mature observations pass; complete315-state
actual coverage and source corrections remain required.
Their128×64 footprint raster versus128×63 source is recorded without shifting/shrinking
the playable32×32 block. Fine pitch/tier/crowd/signage fidelity remains later-pass work.
All11 ship bindings retain original cargo aliases and company/crash recolours; normal
temperate/Toyland fleets move and visit both docks, with stock15.3 re-save/Linux reload.
This is not cargo delivery, full bridge/lock clearance or directional-fidelity approval.
The depot's sprite panels are now replaced by connected voxel walls/roofs, preserving
open waterways and independently drawn water. Both native service routes and a held
Linux stock-round-trip route complete observed depot traversal. Source96×63 bounds
match, with one-pixel horizontal phase and finer fittings/paint still requiring work.
All six dock sections retain distinct ordinary/Toyland detail, original sloped ground
and real lamp/foam palette cycles. Bank piles are trimmed to the actual supporting
slope; whole-tile ground remains. Held hovercraft/freighter mooring and stock reload
are scoped checks, not all-ship/all-waterway clearance approval. Joined ground still
renders94pixels wide versus96 in the source; no footprint was shrunk to hide that phase.
Old-house24 keeps all four completed bodies even in stage0; cottage25 retains its
empty first body. The shared bare soil is a source-identical ground alias. Source
review fixes dominant roof colours, heights, joined walls and cottage placement;
later timber/window/material refinement and garden-ground migration remain queued.
Suburban26 and flats27 retain ground-owned construction, genuinely absent bodies,
source-permitted variant aliases and actual open construction. Source review corrects
their basic plans, front/rear apartment orientation, storeys, wall/roof heights and
dominant palette ramps. All actual suburban variant/stages and both flat families'
states are reviewed; footprint/source pixels and detailed art are not finally approved.
Open-cargo coal/grain/timber/ore/steel trucks preserve genuine empty beds, visible
loads, connected straps/logs and upright coil openings. Later coal engines have real
production/delivery/full-empty/depot evidence; the other loads retain synthetic state
verification pending actual service. Side profiles remain two pixels short and several
diagonals wider than the original art; no automatic dimensional or Pass1 approval.
Arctic/tropical food, paper, copper, water, fruit and rubber retain actual climate
artwork, roofed/open cargo structures and complete cargo pairs. All21 climate/engine
cases have actual captures; the food vans select separate rear panels for each
climate. Ordinary fleet movement and full geometry/palette checks are not cargo
delivery evidence. Side profiles remain two/three pixels short and diagonals too wide.
All eight remaining Toyland road-cargo families now have distinct source-specific
empty/load geometry and all24 engine captures. The overlong shared Toyland nose is
shortened to the source28px profile; a closed-looking cola shell is opened so real
cargo stays visible. Sugar/cola have genuine production/delivery/full-empty/depot
evidence and stock reload. Other Toyland loaded art remains synthetic/source-state
proof. All88 road bindings are present, but their dimensions, paint and clearances
still require later review; they have not automatically passed the complete Pass1 gate.
House28's two tall office families,29's two shops,30's gold facade and31's theatre
retain open construction, absent first bodies and real palette animation. Source
passes correct basic footprint/height and facade/roof mistakes; all actual family
states are found in appropriate ordinary worlds. Matching top bounds do not approve
turret/curve/window/roof/sign detail or the existing ground raster-phase discrepancy.
Closed wagons retain climate-specific source artwork and cargo aliases only where
the original pairs match. Real coupled consists expose and correct an over-wide
wheel stance and overlapping axial bodies. Renderer-only map-step length adaptation
preserves source diagonal proportions; all-curve/slope/clearance review remains.
Olive-column1597 preserves its grey forks and distinct olive foliage through all
seven states. Source review corrects crown heights and width, exposes branches and
repairs dying-leaf connectivity. Remaining stage2/5/6 width and fine leaf/fork/paint
differences remain later-pass work; matching mature bounds is not approval.

The new36…39 bodies and independent grounds retain the suspended glass/masts, Arctic
plans/snow and cinema piers/rooflights/lamp phases. Source/crop/orientation corrections
and actual-state checks are recorded in `VERIFICATION.md`. Joined mall40…43 now retains
its ground-owned south pavilion and other source layers, empty bodies, complete tile
coverage and source-identical state pairs. Registered review fixes disconnected roof
and footing edges; source roof widths/intersections, framing and material detail remain
unapproved. Arctic flat/house44…47 now has actual shared construction states, completed-
only snow and original ground selection. All sixteen live cases are captured; source
frontage/yard orientation is corrected. Fine dormers, masonry, snow and ground pixel
phase remain. Cottage48/49 and offices50…55 now preserve their individual construction,
recolour/snow/ground rules, real porch/roof openings and separate wings/setbacks.
All actual states/recolours are captured, including three cases supplied by the1930
fixture. Fine facade/roof/porch/garden and source registration remain unapproved.
Cabins56/57 and shop/church58…61 preserve late snow versus snowy2/3, real roof/opening/
annex structures and original ground ownership. All distinct actual family/stages are
captured, with two source-identical cabin variant1 substitutions. The small-town world
also supplies the earlier missing37/38 exact cases. Small houses62/63 retain their
cross-gables/porch/gardens; corner shops64/65 preserve missing0, original brick remaps,
chamfered entrance/canopies and snowy1/2/3 cornices. The two-tile hotel66…69 retains
empty first bodies, raised ground-owned sites, original body-owned paving, connected
roof/structural seams and a lower south pavilion/setback. All source top bounds now
agree; whole-ground raster phase and finer roof/window/masonry/garden detail remain.
Offices70…77 retain their different low/full-height frame rules, real balcony/roof
voids, joined gold-office slots/gardens and source brick/company recolours. All48 actual
state/recolour cases pass;70's tropical source and actual context are checked. Tropical
78…83 retain two distinct house plans, a striped thatched cottage, four unique hut/palm
layouts, the flats' late upper storey and church arcades/finials. All36 actual cases
pass, using an ordinary small-town world for missing early cases. Source body-owned
gardens/paving remain body-owned; above-soil half-cell slabs fix initial coplanar
flicker without changingXY footprints. Fine source art and ground raster phase remain.
Continue missing house84+ and other unconverted categories.

Toyland's actual lifecycle differences are explicit, including bare full-height
initial poles and last states that still retain candy, caps or discs. One/two-pixel
registration, several growing-state proportions, ribs/spots/grain and final art stay
queued. The original wide-map path remains approximately3fps; opt-in conservative
Vulkan visibility and capture improvements reach55.78fps in a controlled synchronous
run. Asynchronous camera readiness, GL, frame spikes and smooth60fps remain unresolved;
bindings and correctness checks do not satisfy performance.

## Work selection and defect routing

- **Immediate blockers to basic coverage:** footprint/contact/placement, wrong state or
  palette, broken rendering/picking, disconnected required parts, blocked doors/routes
  and essential clearances. Correct before counting that family as Pass 1 verified.
- **Pass 2 queue:** finer window/roof/core/vehicle/tree proportions and structural detail
  beyond the recognizable basic version, all-state refinements and later joint review.
- **Pass 3 queue:** exact masonry/grain, tiny trim, weathering, detailed highlights and
  source-pixel corrections that do not invalidate basic placement or silhouette.
- **Pass 4 queue:** exhaustive complete-world visual/performance consistency and platform
  checks. Existing wide-view performance failures and long-submit stalls stay recorded.

The earlier detailed house/park cosmetic queue is deferred behind missing Pass 1
families. Its actual placement/contact defects remain eligible for immediate fixes.
No family receives final visual approval merely because its binding or tests exist.

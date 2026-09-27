# Authored model sources

## Active voxel migration

The current goal requires **every world asset** to be recreated as voxels. Editable
cell volumes and six-face Classic palette materials are in `voxels.json`.
`compile_voxels.py` validates/compiles boxes, paint, cuts, repeats, stepped roofs and hollow barrels
to cell runs; the renderer builds shared, hidden-face-free conforming surfaces.
Compact triangulation keeps actual colour/crease edge samples and shared rectangle
cuts. Thin rectangles and unit strips beside colour changes or occupied/empty silhouette edges retain reference
cell diagonals; larger interiors use ears without skipping boundary vertices. Reference/contact
surfaces can retain the original triangulation when depth interpolation must match.
All four construction states for houses 0…8 and13…19, and static airport bindings 19…28,32,43 and47 use this
path, together with all twelve frames of radar tiles 31/51/52 and all four flag frames
of 39/73. `rail_geometry.hpp` also authors voxel running assemblies for all four rail
systems; `terrain_geometry.hpp` authors all seven terrain/rail fence families and
the 13 common foundation forms.
`inventory.py` keeps these procedural families separate from the JSON volume count.
All remaining categories/states and final visual approval remain work.
See `opentt3d/VOXEL_REVIEW.md`.

Airport binding ownership follows the original tile sequence. Ground-only source
tiles require an `airport_ground` binding and no fabricated `airport_tiles` body;
this includes the timber buildings33/34. Tile35 splits the lower office/paving
from its control cabin/tank body. All grounds remain opaque under building
transparency/invisibility. Current provisional airport coverage is53/74 definitions,
47 body owners and35 independent grounds. Source-ID equality alone does not permit
a climate alias: distinct Toyland19…28/43/47 artwork remains supplied until separate
volumes are authored. OriginalZ=-128 fence children use native screen-space offsets
in source registration rather than world-space XYZ.

House binding states encode `variant*4+stage`. A generic0…3 stage binding can cover
another variant only when its original building sprite exactly matches variant0;
source recolouring still applies. Use explicit states for different layouts, as with
the steel/brick tall office and hip/gable townhouses. Statue9 and fountain10 bind
stages2/3; their original empty early-stage bodies remain absent. Parks11/12 bind
their identical stages1/2/3, with stage0 absent. The historical614-volume checkpoint
had1176 nonempty resolved house bindings. Current counts are in
`opentt3d/VOXEL_PASSES.md`; they do not establish final approval. The office lift is
an independent `infrastructure`1443 binding, positioned by the original lift state.
`--reference-house-stage N --reference-house-id H --reference-house-variant V` selects
an actual generated-world case. `--verify-house-lift --running --benchmark-frames N`
observes actual motion; it does not force positions or change animation state.

House source exports retain ground images/palettes/offsets. Use `--house-source 14
--house-layers` or `--house-comparison 14 --registration --source-directory ...` to
review original ground/body placement. House14 needs an ordinary1930–1960 world;
the1950 fixture supplies all stages. `inventory.py --footprints` reports world/contact
bounds and area; outside-tile flags require explicit source/layout review, and no
footprint is automatically approved. Preserve playable coverage instead of shrinking
it to conceal original-versus-perspective raster-phase differences.

Shopping-mall40…43 shares original0/1 and2/3 art. The south43 pavilion is entirely
ground-owned;41/42 have no early body, while40's upper piers/roof are separate sprites.
Twelve volumes preserve this selection and the full2×2 footprint. Roof and foundation
cross-sections meet at the actual north/east/west tile boundaries. Use
`--house-block-comparison 40 --source-directory ...` for registered whole-block review.
Source roof proportions, material detail and pixel framing remain WIP. Inventory counts
84 house definitions with body or ground geometry,83 body definitions and62 grounds.

Arctic flat/house pairs44/45 and46/47 share original construction states0/1/2. Only
the completed above-snow state changes the body to4423/4427 and ground to4419. Preserve
stage2's mature-looking unsnowed body over bare3924 soil. Their ten authored volumes
retain real roof/dormer/window/door openings and independent full paving/rear stacks;
all sixteen actual states are captured in an ordinary1950 Arctic world.

Cottage48/49 gains snow only at completion; offices50/51,52/53 and54/55 already have
their snowy roofs at stage2. All retain bare3924 soil through stage2 and independent
completed grounds. Their21 volumes preserve porch/roof openings, steel/glass grids,
antenna, lower projections and upper setbacks. `face_paint` uses the explicit form
`["face_paint", material, mask, x0,y0,z0,x1,y1,z1]`: mask bits select
`-X,+X,-Y,+Y,-Z,+Z`; only existing occupied cells and those face colours change.
This prevents a vertical facade brush from painting a perpendicular wall solid.

Cabins56/57 have two distinct original plans: variants0/1 share the larger cabin with
chimney;2/3 share the smaller opposite-axis cabin without it. All three early states
are shared across plain/snow definitions; snow and separate completed gardens appear
only at3. Preserve attached lower roofs and the original bare approaches through snow.
Shop58/59 and church60/61 have no stage0 body: their first raised piers/walls belong to
the ground. Both pairs gain snow at2/3, with completed paving only at3. The church roof
is a hollow shell, and its glazing/annex roof are absent from the frame state.

Small houses62/63 have company-recoloured cross-gables/porch and completed-only snow/
gardens. Corner shops64/65 have an absent first body and source-identical1/2/3 bodies,
including the snowy roof/cornices of65; preserve the original brick remap796 and
red-white canopies. The original3924 ground remains bare in every shop state.
Hotel66/67 and snowy68/69 form1×2 pairs alongY. First structures are ground-owned;
later paving belongs to the body and must disappear with it under transparency.
The main roof, middle cross-gable, floors and facades meet at the actual tile seam.
Use `--house-pair-comparison 66 --pair-axis y --source-directory ...` for registered
whole-pair review. `--house-pair` now includes both original grounds, even when the
first bodies are empty. The southern lower pavilion and front planting clearance
must not become a stretched full-width/full-length upper roof.

Offices70/71 retain original brick remaps796/797, pink stepped balcony fascias and
snowy2/3 roofs. Tower72/73 must remain a low open ring/colonnade at both1/2; only3 is
the tall ribbed tower. Gold offices74/75 and76/77 join alongX, retaining open facade
slots/roof wells at1/2 and permanent gardens in every state. Joined native exports
write tile-origin sidecars and expand tall crops without changing the review lens;
the comparison tool also reads the earlier fixed crops.

Tropical78…80 retain distinct foundations, shared1/2 open frames and completed-only
gardens/roofing. House81 has four different plans, all absent at0 and source-identical
at1/2/3 within each variant. Gardens, palms, huts and paving belong to the original
body sprites; bare3924 soil remains independently visible under hidden/transparent
bodies. These authored surface slabs touch the soil and are half a world unit thick,
avoiding coplanar flicker without changing the full tile'sXY coverage. House82 gains
its inset upper storey only at3; church83 is absent at0 and identical at1/2/3.

Houses15/16 require an ordinary1930–1960 world;17 starts in1977,18 in1983 and19 in1985.
The first mansard state is already a raised frame; the modular office's early pavilion
is taller than its later base; rooflight19 gains its raised plinth after the flat
first foundation. Do not substitute generic construction shapes. Source recolours
remain runtime table selections. `--gallery-voxel-prefix house_` selects this batch.
House comparison panels grow to fit tall art while retaining native4x magnification.

Old-house24 has four genuinely different body sprites, each already finished in
every construction stage. Cottage25 has no first body; its1/2/3 body is identical.
Initial ground3924 shares the existing full-tile soil volume. Mature gardens retain
their distinct original textures while ground-detail migration continues. Both types
need an early world (24 until1951,25 until1952); the ordinary larger1950 fixture
supplies the otherwise missing ground-only cottage state. Source reports now include
body size/offset and ground sprite IDs alongside the variant/stage summary.

Suburban26 has four distinct layouts. The first two bungalow building sprites are
empty, but their original ground images contain the excavation/unfinished walls;
these remain `house_ground` volumes. The other three variants keep separate sites,
open shells and completed roof/garage shapes. Flats27 preserves two source-identical
variant pairs, a ground-only tan site, open roof well, tall brick front facades and
later rear wings. Review contexts lower the generic substrate beneath independently
bound house grounds. Use normal1940/1950 worlds for actual cases; unavailable stages
must be found in an appropriate ordinary world, never manufactured by the renderer.

Stadiums20…23 and32…35 have separate `house_ground` bindings for their permanent pitches.
Their original body stage0 is empty; stages1/2/3 share the source-identical stands.
Ground remains opaque under building transparency/invisibility, shares terrain edge
cuts and retains underground-bore clipping. Whole-family original-sprite provenance
refreshes with texture generation. Ground-only focus is reported distinctly; it cannot
substitute for required actual body capture.

`contact_sheet.py <sources> --house-block 20 21 22 23` composes a four-tile source in
upstream north/east/west/south order. Fully voxel-ground-bound blocks also export
native joined scenes; use `--house-block-comparison 20 --source-directory <sources>`
for registered source/model review. House manifests now include original indexed
body/ground palette colours. `--verify-stadium-palette 20|32 --running
--benchmark-frames N --blitter 40bpp-anim` observes all five original crowd phases and,
for32, all four scoreboard phases on one emitted tile without setting game state.

Houses28…31 add two tall-office construction families, two older-shop bodies, a
stepped gold office and the theatre.29/31 preserve their absent first bodies; their
soil aliases are tested separately with `--verify-voxel-meshes mine_ground_`.
`--gallery-voxel-prefix house_city_` exports the twelve volumes. Use normal1940/1950
worlds for29 and1963+/1973+ for28/30. Theatre31 retains palette241…244; `--verify-house-palette
31 --running --benchmark-frames N --blitter 40bpp-anim` observes all four live phases.
The same command also supports stadium20/32; their older command remains valid.

Office36 retains the two bare-mast stages1/2 and suspended glazed body3, with an absent
first body and independent concrete grounds. Arctic37/38 preserve two original plans,
red/grey and blue/red source recolours, matching snow silhouettes and separate gardens.
`house_next_` selects these twelve volumes. Native house exports fit projected bounds
at unchanged scale and write `model-voxel-house-…-native-….json` tile origins; the
comparison tool also reads earlier fixed-size captures. Cinema39 uses `house_cinema_`
and supports `--verify-house-palette 39`; all four original lamp entries remain.

The nine Toyland tree families1947…2003 use63 `tree_toy_` volumes. Preserve the actual
last-state rules: some retain candy/caps/discs, some lose all cloth, and the tiered
family starts with a full-height bare pole. Angular `radial_paint` and `radial_erase`
brushes use explicit sector masks on occupied cells; erasure can filter a material.
`radial_paint` optionally ends with `[phase_degrees, twist_degrees_per_cell]` to curve
its painted sectors with distance from the centre, as on a peppermint roof. These
finite angles stay within−360…360; the brush preserves holes and other height ranges.
They do not sample images. All63 actual states and exact palette/lifecycle checks
are recorded, but wide-view geometry cost is currently a severe performance defect.

Original industry exports also include `industry-procedural.json`: ordered child
selections and resolved imagery for Toyland143/162/165/174, including construction
and genuinely absent intervals. `contact_sheet.py <references>
--industry-procedural-source 143 --stage 3` assembles those original parent/child
layers at one fixed registration across every frame. Source export does not change
industry animation or simulation state; it does not establish voxel child coverage.

Cola137 uses three `cola_` volumes: a shallow gold bowl, source-identical stage1/2
blue cup and completed cup with an open leaning straw. Its original2077 soil shares
cotton's independent Toyland-only binding. Both original layouts retain full straw
height beyond the sorting box. Joined industry reviews accept a nonzero base sprite
with no resolved ink as genuinely absent (toy-shop141 stage0); a visible unbound body
still prevents complete export. No empty placeholder model is inserted.

Toy-shop138…141 adds eight `toy_shop_` bodies with four coloured interlocking-brick
towers, top studs, crenellated walls, an open courtyard/gateway and four raised flags.
138 remains ground-only in every stage;141 stage0 remains genuinely transparent.
Stages1/2 share source-identical volumes. The three projected body cuts retain linked
custom-source fallback; original2022 soil shares the sweet factory's Toyland-only
ground. `--gallery-voxel-prefix toy_shop_` includes the joined four-tile layout.

Plastic-fountain148…155 adds sixteen `plastic_` volumes: eight completed airborne
splash poses and eight independently animated basin grounds. All24 stage0/1/2 body
slots remain empty; each original ground exists at every construction stage. The
recessed16×16 basins retain white/yellow retaining edges and raised liquid lobes.
The front retaining slopes meet the original tile boundary. Fifty shared authoring
components preserve the reviewed prototype's occupied cells and paint exactly.

`--verify-plastic-fountain` / `renderer3d verify-plastic-fountain` observes all eight
actual graphics-ID phases on one unchanged industry tile. Each counted body must
share that capture with the matching independently emitted voxel ground. Diagnostic
captures cannot qualify; missing/replaced layers reject at setup, and paused one-pose
observations do not pass. The observer reads the ordinary animation without changing
tile state or simulation RNG. Partial custom replacements retain the supplied path
across each layer's eight original source poses. Use a running service save and
`--gallery-voxel-prefix plastic_` for the independent source/layout review.

Fizzy156…159 adds seven `fizzy_` volumes: six can/glass apparatus bodies and one
independent4676 soil.156 stays ground-only,157 remains empty before completion, and
158's construction chain keeps its distinct source ownership. The159 can has a real
open interior; completed liquid and the leaning hollow straw are separate components.
Quarter-unit glass rims and reflected edge paths preserve clear spaces in real3D.
The connected157…159 body source cuts retain linked custom replacement fallback.
Twenty-eight shared components, polylines and exact prism masks preserve every
reviewed prototype cell/colour; source registration and fine fidelity remain provisional.

`--verify-industry-palette 157 158 159 --running --benchmark-frames 600` requires all
five original indices227…231 on each actual completed body, followed by five palette
phases on one unchanged tile/industry. Diagnostic captures cannot count. The same
observer retains steel grounds52…57's seven original fire phases and at least two
emitted animated materials. Missing bindings and a body lacking231 correctly fail.

The factory143 child path uses independent infrastructure bindings4717…4720 and the
original ordered50-frame draw table. Conveyor screen steps(-2,+1) become world+X;
stamp offsets(0,+dy) become world-Z. All four original children must be bound before
connected142…146 bodies use this path.4675 ground remains independently selectable.
`--verify-toy-factory --running --benchmark-frames 9000` observes all selected children
from the same actual capture on one unchanged industry tile. Supply the factory
through ordinary cargo delivery; its idle frame0 alone cannot pass.

The twelve provisional factory volumes cover seven body owners, four children and
independent4675 soil; fourteen genuinely empty body slots remain unbound. In particular,
144 owns the early blue tower while145 owns the completed tower, and holder4717 owns
separate wall/front-shaft fragments. Forty-five factored components preserve the
reviewed quarter-unit occupied-cell/material hashes. Static joined stages have no
cross-owner cell overlap. Original frame30 completely occludes the duck under the
press; frames29/31 retain partial compression. Exact contact and surface fidelity
remain provisional. Both9,000-frame supplied-service observations capture all50 frames,
and all1,624 preceding models retain their hashes. See`opentt3d/VOXEL_REVIEW.md`.

Every named voxel gallery also exports`model-voxel-NAME-native.{pam,json}` at the
fixed source-scale lens and actual model origin. The JSON`model_origin`keeps spatial
registration visible before a study has a runtime binding. Bound factory galleries
add all50 original child compositions and`voxel-industry-procedural-143.json`.
`contact_sheet.py --industry-procedural-comparison 143 --source-directory EXPORT`
checks exact ordered source selections/absences and places source/model images at
the same parent origin. Joined industry sheets include declared procedural children.

Bubble160…163 uses three source-owned bodies plus the fixed clear cylinder4746 and
yellow plunger4747. The original names`spring`and`bubble`refer to those two children;
floating-bubble effects4748…4762 are separate. Stage0 has no children, stages1/2 only
4746, and completed162 draws4747 then4746 through the original40-frame sequence.
The plunger's screen travel changes only world-Z by`dy-68`; construction ignores
the animation-frame byte. Body sources160…162 and both child bindings are linked
for custom-source fallback. Shared4675/4676 grounds retain independent checks.

`--verify-bubble-generator --running --benchmark-frames 1800` observes every original
frame from actual same-capture child selections on one unchanged tile/industry.
Diagnostic captures cannot count. Bound galleries export both construction child
compositions and all40 completed poses; use`--industry-procedural-comparison 162`
with`--stage 1`, `2`or`3`. Ground-only members receive individual native captures even
when their selected layout reuses an older family's exact soil model.

Toffee164…166 has two original children at **every** construction stage: cutter4767
then4766. Classic4766 exactly redraws parent4764 at net screen offset0. Bind4766 to
the same model as all four165 body states; runtime and diagnostic galleries reuse
that physical owner. A different owner or missing cutter rejects the connected
body family while each3981 ground remains independently selectable in Toyland.
The inclined cutter follows world`(+d/2,0,-d/2)`, projecting to the original`(-d,+d)`.
The original255 entries mean zero displacement, never child absence.

`--verify-toffee-quarry --running --benchmark-frames 2400` requires all70 completed
frames from actual ordered selections on one unchanged tile/industry. Construction
ignores the animation byte. Procedural galleries retain73 states, including stages
0/1/2, and explicitly label the shared-parent child. Use
`--industry-procedural-comparison 165 --stage 0`through`3`; source comparisons verify
that the alias's original pixels and net registration really match the parent.

The integrated toffee family contains four provisional volumes and nine shared
components. Three independently bound Toyland grass tiles reuse the source-checked
airport lawn. The native/street review, source aliases,70-frame travel, zero-intersection
audit and all1,641 preceding-model hashes are retained under`breadth-toffee-final-*`.
Industry source comparison sheets expand to fit the complete registered source/model
union, including overhangs. Exact surface paint and fine shape remain in later passes.

Sugar-mine diagnostics preserve all96 original completed frames: sieve4775…4779,
cloud4784…4789 and pile4780…4783, in that order with genuine middle/trailing absences.
The sieve moves along its crossbar at constant worldZ; its baseline screenX8 maps
displacement d to world(-d/4,+d/4,0). Clouds and piles have independently registered
poses. Construction has no children. Linked172…174 body/source checks require all
fifteen child bindings; the four167…170 stockpile grounds have a separate linked
source/binding check.171…174 Toyland3981 grass remains independently selectable.
`--verify-sugar-mine --running --benchmark-frames 2400` observes all96 actual frames
on one unchanged tile/industry; galleries and hidden children cannot satisfy it.
`--industry-procedural-comparison 174 --stage 0`through3 reconciles the original
ordered selections and99 total diagnostic states. The integrated22-volume family
contains three source-owned post cuts, four ground-owned stockpile cuts, five hollow
wire sieves, six falling-grain distributions and four growing piles. Twenty original
body slots stay empty. Three shared components and stepped ownership prisms preserve
all prototype cells; every1,645 preceding model hash remains unchanged. Rod passages
clear rim/fill through all96 frames; independently registered grain depths clear every
growing pile. Source/native/street and live controls are retained under
`breadth-sugar-final-*`. Fine source paint/shape and final visual approval remain open.

`fixture_industry.py --industry 31 --climate toyland --cargo-service
--destination-industry 30 --destination-town-site --supply-industry 28 --city-size 4
--cargo-snapshots --service-observation-ticks 6000` funds a real battery→toy-factory→
town-shop chain. The optional third supplier uses ordinary funding, roads, a separate
truck and full-load/accepted-delivery orders. Both trucks must load, deliver and
return; the input truck must reach actual full capacity. Original industry-spacing
rules remain in force. The ordinary two-industry route retains its existing defaults.

`water_buoy` is infrastructure693's semantic state0 binding; `water_buoy_toyland` is
state1's separate solid green/orange/red marker. Classic's world image is resolved
through `GetCanalSprite(CF_BUOY,tile)`; the GUI/base-table image is different. The
capture adapter checks the actual base-set source and preserves custom fallback and
original water. `--reference-buoy --verify-buoy-beacon --running --benchmark-frames N`
checks actual239/240 lamps and250…254 foam. `--export-infrastructure` records the real
source when a buoy exists, and `contact_sheet.py --buoy-comparison --source-directory
...` compares tile placement. The ship fixture's `--buoy-waypoint` builds and observes
ordinary navigation through a real buoy tile.

The first voxel vehicle, engine238/Dinger100, uses a0.5-unit grid and faces+X.
Vehicle binding states0/1 mean shared/default empty/loaded; explicit climate pairs
use `climate*2+cargo` (Arctic2/3, tropical4/5, Toyland6/7) and take precedence over
that default. Every declared pair must be complete. These share a body only where the
original source images match. Original company palette, continuous heading and
upstream vehicle state drive its instances. `--verify-voxel-vehicle 238` requires
actual world capture, and `--gallery-voxel-prefix aircraft_` exports review views.
Use `contact_sheet.py <vehicle-source-directory> --vehicle-source 238` for all eight
source directions/both cargo states. `fixture_rail.py --airport city --aircraft`
creates a public-NoAI service route; add `--aircraft-hold` for its verified returning
loading stop. Stage each fixture's own `ai/` when loading the save. Full vehicle/state
coverage, source precision and final approval remain open.

The aircraft catalogue adds distinct propeller, delta, high-wing, twin/four-engine
and futuristic multi-body volumes. `fixture_aircraft.py --first-engine 215
--last-engine 238` builds a normal operating fleet, observes each aircraft at an
actual destination service stop and saves it outside its hangar. Use that fixture's
`ai/` directory during reload. Native source comparisons remain required for each
independent family; equal source-direction arrays justify aliases only within the
same graphics climate. All41 aircraft definitions now have body bindings: Toyland's
five planes and helicopter use explicit6/7 states, independent of the normal artwork
behind overlapping sprite numbers. Normal aircraft sources match across temperate,
Arctic and tropical exports in1,120 directional/cargo views.

Helicopters have separate body and four original-state rotor volumes. Sprite3901
binds infrastructure states0..3, selected from the actual3901..3904 rotor sprite;
partially replaced rotor/body art keeps its supplied rendering. Rotors use the body's
smoothed position and retain fixed-world source poses, original palette and unclickable
ownership. Both parts remove the original aircraft anchor's one-height-unit offset so
zero-height authored wheels/skids meet the airport surface. Cab hides its own rotor.
`--verify-aircraft-contact <engine>` checks actual stationary support against the
airport ground. `fixture_aircraft.py --service-hold-ticks 256` holds ordinary full-load
service through saving, then releases it after reload. Use `--verify-helicopter-rotor`
with a running benchmark to observe all four states and the stopped-to-running transition.
Per-engine pose checks include128 independent joined-rotor CPU/GPU comparisons.

Vehicle source exports include `aircraft-rotors.json` with original palette indices,
size and offsets. `contact_sheet.py <gallery> --vehicle-comparison 253
--helicopter-rotor-state 0 --registration --source-directory <references>` composites
the original body/rotor at their own offsets and compares vehicle-anchor-aligned views.
All-angle native and street captures include all four rotor states. These technical
checks do not establish source-shape, paint or complete airport/Cab clearance approval.

Slender wings/fins can use `['prism', material, axis, lower, upper, outline]`, written
as JSON with double quotes. The outline is an explicitly authored simple integer
polygon in the two other axes, in their X/Y/Z order; axis2 gives an XY wing and
axis1 an XZ fin. The half-open extent extrudes occupied voxel cells between the
stated bounds. Rational cell-centre scan conversion preserves winding independence
and concavities. Self-intersection, clipping and degenerate outlines are rejected.
The resulting geometry remains ordinary voxel cells and uses the same mesher; this
operation does not read source images or generate artwork from them.

Vehicle verification includes all16 original company recolour tables and the crash
palette. The colour oracle maps face indices through upstream tables into untextured
vertices, independently of atlas/palette-strip sampling; geometric/CPU-instance and
transparent-picking checks remain exact. This does not substitute for live cargo,
crash/effect state review or source-perfect shape/detail approval.

The breadth-first road batch includes buses116…122 plus closed cargo126…140,
153…155 and186…191. Ordinary and Toyland bodies remain separate where source artwork
differs, even when sprite numbers coincide. `fixture_road.py --climate toyland
--first-engine 129 --last-engine 203` creates a normal public-NoAI moving fleet;
stage its own `ai/` on reload. See `tools/opentt3d/fixtures/road/README.md`.
`inventory.py --vehicle-families road` groups actual climate/direction/cargo sources
and keeps Pass1 acceptance false. `contact_sheet.py --vehicles --engine-range 123 173
--direction 2 --preview-scale 6` makes a compact source overview.

`smoke.py --verify-voxel-poses 129` runs the full1,088-pose exact company/crash/cargo
matrix for its default pair, independently of actual live capture. All declared
climate pairs are checked: food156…158 has2,176 poses across both original climates,
without changing game settings. `--reference-vehicle N --reference-vehicle-binding S`
requires that exact active climate/cargo binding in both focus and actual capture.
The complete renderer check covers every declared voxel vehicle binding. Mismatch diagnostics retain both
CPU/GPU images. CPU yaw products round separately to prevent compiler-only fused
multiply/add from selecting a neighbouring face at subpixel boundaries.
Several IDs may follow `--verify-voxel-poses`; every requested matrix must report
completion, enabling one bounded background process to check a complete new fleet.

Open road cargo124/125 and141…152 binds genuine empty and loaded volumes. Grey
tippers/company-ribbed hoppers, timber stakes/straps and red coil platforms remain
distinct. Logs have flat cut ends; steel coils are upright with real central holes,
as the source directions show. Use `--gallery-voxel-prefix road_open_` and native
`--vehicle-comparison ENGINE --loaded` for review. `fixture_industry.py --coal-service
--truck-engine 124|125 --year 2050 --cargo-snapshots --depot-directions` supplies real
loading/delivery/return and depot evidence. Other cargo services and exact directional
proportions remain separate from synthetic palette/state checks.

Arctic/tropical engines156…173 add food, paper, copper, water, fruit and rubber.
Food156…158 has separate Arctic/tropical rear-panel paint and no shared default body.
Paper retains its canopy/solid rolls; copper its brown ribbed hopper; rubber its open
flared vat and real white fill. Sprite numbers alone do not establish climate aliases.
Use `--gallery-voxel-prefix road_climate_` and source exports from the appropriate
climate. `inventory.py` reports resolved `voxel_climate_states`; movement fixtures
and synthetic loaded states do not establish production/delivery.

Toyland174…185/192…203 supplies the remaining eight road-cargo families; every original
road engine116…203 now has a voxel binding. `--gallery-voxel-prefix road_toy_` exports
the sixteen empty/loaded volumes. Keep real open beds, visible cola, solid batteries/
cans/plastic and see-through spatial bubble outlines rather than closed-box aliases.
`fixture_industry.py --cargo-service --climate toyland --industry 36
--destination-industry 27 --truck-engine 174 --year 2050 --cargo-snapshots
--depot-directions` supplies real sugar loading/delivery and depot review. Cola uses
29→33 and177. Public actual-tile queries place adjacent roads for each industry layout;
the existing `--coal-service` remains available. Reload each fixture with its own AI.

Closed wagons use the `wagon_closed_` prefix and explicit source-climate pairs for
conventional coach/mail roofs, goods doors/panels, armoured bands, tropical oil tanks
and refrigerated ends. Modern coach/mail/armoured source equality is checked before
sharing across climates. `fixture_train.py` creates actual attached consists for all
four climates and conventional/electric, monorail or maglev tracks; see its fixture
README. `--reference-vehicle` includes visible attached train parts and retains their
own picking IDs. Movement does not establish cargo production/delivery.

Original trains use eight map-step centre spacing. Voxel train presentation adapts
longitudinal length to that convention, retaining diagonal source proportions and
coupler clearance without altering vehicle positions or simulation lengths. The
96-byte instance record stores this scale in a flagged, otherwise unused normal-
offset word. Rotated unmirrored palette instances also stage CPU-rounded yaw values;
explicit shader products avoid driver-specific matrix-dot rounding at coloured
edges. Exact CPU/palette/picking checks and metadata/spacing regressions remain.
Mesh batches use first-captured order within each explicit parent/child layer.
Allocation addresses must not choose coplanar colour or picking precedence; CPU
regressions and32 exact GPU allocation/submission/opacity views enforce this rule.
`smoke.py --verify-instance-order` separately exercises those views,24 parent/child
views and the mixed-opacity matrix, including on the original GL3.2 fallback.

Ships204…214 now bind six quarter-grid families, including distinct Toyland captain
vessels. Their original empty/loaded source arrays match, permitting those aliases.
`fixture_ship.py --climate temperate|toyland` builds a public-NoAI canal/depot/dock
fleet. Every available ship must move away and enter loading state at both docks;
temporary normal full-load orders make first arrivals observable before being
released. This does not manufacture cargo or prove cargo delivery. See
`tools/opentt3d/fixtures/ship/README.md`; reload each save with its own `ai/`.

The `hull` operation is `["hull",material,centre_y,knots]`, with explicit increasing
`[x,lower_half_beam,upper_half_beam,keel,deck]` sections. Optional final deck material
and integer rim width coat only upward faces without changing occupancy. Validation
rejects unbounded, nonfinite, unordered or clipped profiles. Hulls use authored
controls, never image-derived geometry. Vehicle source comparisons expand panels to
fit long ships while retaining native5x magnification and source registration.

`ship_depots` binds axis0/1 and original north/south parts0/1 to four `water_depot_`
volumes. Whole-family structural provenance is checked independently from the original
water-class ground. Open ends, matching tile joins and every original ship's swept
cross-section have regressions. `--reference-ship-depot 0|1` requires actual capture
of both parts; `--verify-depots` also runs256 joined ship-depot palette/CPU/visibility/
water-picking views. Use `--ship-depot-source` or `--ship-depot-comparison
--source-directory ...` for joined original/voxel review. Normal recurring depot
fixtures and the optional public stop/restart hold are documented in the ship fixture.

`docks` binds original graphics0…5 and ordinary/Toyland states0/1. Keep the level
eight-unit deck across both tiles; the bank's piles terminate at its actual slope.
Original water classes, shore/canal-bank ground and bridge drawing remain independent.
Toyland source bodies genuinely omit lamps/white foam; do not alias those details.
`--reference-dock N` requires actual voxel capture; `--verify-stations` includes512
joined dock palette/CPU/ground-picking cases. `--dock-source` and `--dock-comparison
--source-directory ...` retain original layer offsets and complete two-tile footprints.
Use `--verify-dock-palette 4|5 --running --benchmark-frames N --blitter 40bpp-anim` to
observe original lamp/foam phases on a real non-Toyland dock. Source-perfect review
and all-clearance approval remain separate from these checks.

For an authoring iteration, `smoke.py --verify-voxel-meshes house_` runs exact cell-
mesh/CPU-instance, source-house palette, transparency/picking and atlas-relocation
comparisons for that model prefix. Joined-house checks include every neighbouring
piece even when only a secondary piece matches the prefix. Unknown prefixes fail.
`--verify-renderer` retains the complete mesh, vehicle, tree, industry, lift and
renderer/navigation matrices; the focused option is a separate family-level check.

`rail_sh_electric` shares engines23/24 because their original directional/cargo images
are identical. Vehicle source exports retain palette indices/framing; compare with
`--vehicle-comparison 23 --source-directory <export>`. The gallery command exports
native-scale vehicle directions alongside orbit/street views. Use `fixture_rail.py
--train-engine 23` for a public-API operating train, optionally `--train-hold` for a
verified normal stop at the terminus. `smoke.py --reference-vehicle 23` requires both
read-only focus and actual voxel emission. Stage the matching fixture's `ai/`.

All35 original locomotive definitions now have voxel bodies. Engines1 and16…21
keep independently inspected Arctic/tropical forms; sprite-number reuse does not
permit sharing those climates. The remaining normal monorail/maglev artwork matches
across the three ordinary climates. Toyland locomotives retain separate bodies and
their original eye/lamp details. Engine8/10 and13/15 share matching source artwork.

Train volumes use explicit vertical grids calibrated to the original one-level
tunnel loading gauge. Their XY footprints, wheel gauge, cargo voids, authored cells
and0.5-unit running-rail contact plane remain explicit. The pose verifier checks all
body vertices against the actual faceted tunnel profile including inward ribs;
longitudinal spacing and slope/curve contact require their own contextual review.

`vehicle_collectors` binds each fixed roof attachment separately: parts0/1 for
SH23/24 and part0 for TIM25/AsiaStar26. The independent open frames retain the body's
smoothed position, heading, original company/crash palette and picking owner. Their
lower mount stays on the roof insulators while the upper frame follows the wire;
each contact shoe samples its own position at a tunnel mouth. Surface samples use
the actual captured wire endpoints/elevations, including half-runs and bridge grades.
The interior electric
wire is at7.55units, with its descending approach ending before the stone arch.
`--verify-voxel-poses 23 24 25 26` includes joined all-angle, palette, transparent-pick,
CPU/GPU and independent-height checks. Native source views include the collectors;
`model-voxel-train-ENGINE-collector-STATE-VIEW` adds joined street/orbit views for
surface0, tunnel1 and mixed-height2 states.

Use `fixture_rail.py --train-engine 23` and then a bounded background run with
`--reference-tunnel --verify-train-collectors 23 --running --benchmark-frames 3600`
to require actual surface/portal/tunnel observations on one operating locomotive.
Repeat for24…26 with their own fixtures and AI directories. A held catalogue save
cannot establish this movement check. These observations do not change the original
train state, map, orders or simulation RNG.

The Balogh coal truck123 has distinct empty/loaded volumes. Use
`fixture_industry.py --coal-service --cargo-snapshots` for ordinary0/20 and20/20 saves,
`--reference-vehicle 123 --reference-cargo empty|full` for paused actual-state review,
or `--verify-voxel-cargo 123` with a running benchmark to observe both amounts on one
rendered vehicle. These checks never set cargo or change the simulation.

Industry bodies0…3 and separate `industry_ground`0…6 bindings preserve the original
four-slot construction/animation selection. Source/registered sheets use
`--industry-source` or `--industry-comparison`, optionally `--industry-ground`.
Industry body and ground bindings may now declare `climate*16+stage`: Arctic16…19,
tropical32…35 and Toyland48…51. Shared0…3 bindings keep their original source-climate
guards; an explicit active-climate state takes precedence. Reserved slots4…15 and
climates outside0…3 reject. Equal source numbers do not make differently painted
climates aliases. Body and ground selection stays independent, while connected source
cuts and original child completeness checks remain linked. Native industry sidecars
record `climate` and `binding_state`; their filenames still use construction0…3.
Inventory reports explicit body/ground states separately from shared stages. Actual
world-capture logs record the selected climate/binding alongside the construction stage.
The `mound` operation takes the same material/bounds as a box and fills an explicitly
bounded elliptical cone from its base; every column is supported. It never reads
source image geometry. `--palette-counts --preview` reports reference colour frequency
for manual material work. Ground keeps the complete playable tile footprint.

The eleven `sawmill_` volumes cover industry11…15, including distinct foundation,
open-framing and roofed states for11…13. Original14/15 bodies are absent through
stage2; their completed round logs and separated timber boards sit on the independently
owned full3924 soil. Connected rafters/roof planes, cut-through rooms/doors, the cutting
table/worker and every board's supporting battens remain explicit cell geometry.
Use `fixture_industry.py --industry 2` for real construction checkpoints and
`--gallery-voxel-prefix sawmill_` for source/street review. Tests enforce original
per-state palettes and grounding of every disconnected physical part; source-painted
roof/wood detail and final approval remain open.

Six `forest_` volumes cover four distinct nine-pine growth bodies, felled logs/stumps
and their independent full-tile litter. Original graphics17 is a production state:
wood dispatch changes a mature graphics16 tile to completed17 (construction stage3),
then the normal tile loop restores16 and restarts growth. Its four identical2076
source slots share one body. `--verify-forest-cycle --running --benchmark-frames 9000`
observes mature→logs→all four growth states on one unchanged tile/industry. Use the
ordinary forest-to-sawmill fixture's service save; a newly funded construction save
alone never establishes the dispatched-log state. Observation consumes no simulation RNG.

Nineteen `refinery_` volumes bind graphics18…23, including hollow open vessels, pipe
and cross-braced process frames, three flare service platforms, the completed flare,
the raised cooler and an L-shaped office. Original3924 construction soil and1420
completed paving remain independent full-tile grounds. Stages2/3 share bodies where
their original sprites match; flare20 instead shares open stages1/2. Every disconnected
physical component is grounded, openings are real air cells, and occupied XY bounds
remain inside the tile. Use `fixture_industry.py --industry 4` and `--reference-industry
GRAPHICS STAGE` / `--reference-industry-ground GRAPHICS STAGE` for actual selection.
Palette grain, hatches, pipe/brace profiles and final visual fidelity remain under review.

Power-station bodies7/8 add cooling-tower and boiler/chimney construction volumes;
ground7/8 reuses the identical original3924 soil. Body8's transparent source2048 gets
no stage0 volume. `fixture_industry.py --industry 1` creates ordinary public-API
construction checkpoints. Source comparison explicitly labels transparent bodies.

Auxiliary9 and gantry10 add the equipment banks/steelwork and six original cyan spark
poses. Original2051 and early transformer bodies remain empty. `--export-industries`
also exports `industry-effects.json` with child and parent sprite offsets. Use
`--industry-effect-source 10` or `--industry-effect-comparison 10 --source-directory ...`.
`--verify-power-sparks --running --benchmark-frames N` observes all six real child
frames on one tile; it never forces animation state. Parent/spark binding requires the
complete original family. Sparks have independent frustum bounds and an explicit
child draw layer that preserves ordinary depth and picking without a depth bias.

Industry comparisons use alpha-visible bounds and retain original carrier dimensions
separately; transparent padding is not geometry. Native exports expand their crop to
include tall/overhanging geometry and write a tile-origin registration sidecar; source
registration sheets retain both complete silhouettes at the same native scale.
House-native galleries include all
selected source variants and original ground-only empty-body stages. Layered house
composition retains source offsets while cropping only transparent padding.

`lathe` takes a material, XY centre and explicit `[z, outer_radius, inner_radius]`
profile knots. Optional five-value knots add `[dx, dy]` centre offsets, interpolated
through height for leaning open tubes. The inner lining follows adjacent sloping air
cells while preserving exterior faces, and the complete swept bounds are checked.
An optional `[x_scale,y_scale,angle_degrees]` transforms the cross-section. Heights
increase strictly; volumes are bounded and consume no simulation RNG. `lathe_paint_inner` uses the same profile
but only repaints faces beside its inner air column, preserving occupied cells,
exterior colours and rim faces. An optional final `[frequency,seed]` gives deterministic
inner-face grain. Generated per-face palette combinations share the normal16-bit
material budget. Both operations use authored controls, never image-derived geometry.

Road-depot family4 has `depots` states0…3 for temperate/arctic/tropic directions and
4…7 for the distinct Toyland texture variants. `depot_floors` is independently opaque
under building transparency/invisibility. `--depot-source 4` assembles original layers;
`--depot-comparison 4 --registration --source-directory ...` retains their tile offsets.
Use `--reference-voxel-depot 4 --reference-depot-direction N` for an actual exit.
`fixture_industry.py --coal-service --depot-directions` builds all four exits and a
real delivery/maintenance loop; `--verify-depot-traversal 0` observes its normal
visible/inside/visible states during a running benchmark. Whole-family provenance
and original relocation/catenary routes remain respected. All artwork is still WIP.

Rail/electric/monorail/maglev families0…3 also bind all four directions and their
original climate group. `depot_floors` states0/1/2/3 select normal/snow/desert/Toyland;
`depot_wires` family1 keeps electric contact wire independently visible/transparent.
Running rails/ballast/supports remain the existing procedural voxel assembly. Source
provenance checks include each railtype's original sprite relocation. Floors retain
their full16×16 footprint under building invisibility; tramkind5 remains unconverted.

Use `--reference-airport --reference-airport-tile 21` to locate a particular original
airport graphics type and require its actual voxel capture. The default without a
type still selects any bound tile. `--gallery-voxel-prefix airport_terminal_` reviews
the terminal A/C and round-concourse family. Their source company palette is retained;
support, glazing, roof posts/aerials and painted shadows are authored separately.
Airport pier layouts25…28 and radio tower32 also use explicit volumes. Infrastructure
reference manifests include actual indexed `palette_indices` (direct RGB pixels have
no index). These identify the radio's original239/240 alternating beacons.
`--verify-radio-beacons --running --benchmark-frames N` observes three original paired
phases on an emitted radio model. `VoxelPaletteMask` extracts the actual texel index;
texel-centre coordinates must be truncated, not rounded to the next entry.

Standalone tree family1576 has seven explicit volumes (`tree_lime_00`…`_06`) on a
0.25×0.25×0.75 grid. All stages retain original source colours, including actual
gaps/bare branches rather than a painted dying shell. Whole-family original-sprite
provenance gates the path. `--reference-tree 1576 STAGE` locates and requires an
actual tree; the locator reads upstream layout/growth rules and never changes them.
`contact_sheet.py <directory> --tree-source 1576` shows all source stages/palettes at
one scale; `--gallery-voxel-prefix tree_lime_` includes street and building-neighbour
contexts. Tree manifests include indexed colours, offsets and dimensions.

For clustered material grain, append a positive integer colour-block size after the
optional source-material mask, for example:
`["scatter_paint","lime_leaf_85",3,37,3,10,27,22,23,63,"lime_leaf_84",[2,2,2]]`.
One deterministic hash value covers that cell block; geometry and nonmatching
materials are preserved. Omitting the block retains the original single-cell grain.
This is explicit authoring data, not image-derived shape or simulation RNG.

Family1583 adds `tree_silver_00`…`_06`, with its own silver foliage and shorter dead
trunk. `ellipsoid_paint` accepts the same material/bounds as `ellipsoid` but only
recolours occupied cells, so a highlight cannot enlarge a crown or fill a gap.
Native-scale galleries use the fixed lens on a distant virtual canvas, cropped to
96×96. Compare with `contact_sheet.py <gallery> --tree-comparison 1583
--source-directory <original-export>`; matching image bounds is not final fidelity.
Every family still needs source, street, neighbour, lifecycle and live follow-up.

Drooping-spruce family1590 is in active first/refined review, with explicit radial
boughs, hanging needles and separately restored woody supports. Its native-scale
silhouette/detail still needs work. Native tree captures now derive background alpha
from object IDs, so black needle/shadow materials remain part of the visible bounds.

Tropical families1912/1919 add saguaro/column cacti;1821/1828 add bent/tufted palms.
Each has seven explicit0.25×0.25×0.5-grid volumes. Cactus forks and palm fronds connect
to grounded stems; dying states change occupied structure as well as colour, except
the source column cactus's first dying silhouette, which genuinely stays unchanged.
Palms retain different leaf palettes/blade density and the tufted family's white foot.
Source dimension review does not approve fine leaf/rib/shadow patterns or registration.
The catalogue-wide four-pass queue is in `opentt3d/VOXEL_PASSES.md`.

Multi-tile review uses the original house layout and independent tile IDs. The
hotel7/8 exports `context-house-7-stage-0`…`-3` plus `context-house-7-neighbours`,
with both halves beside other offices. Source comparison uses `contact_sheet.py
<directory> --house-pair 7 8 --pair-axis y`; `--pair-axis x` selects a2×1 pair.
House source sheets retain all16 original variant/stage records per ID.
Single-tile primary houses also export `context-house-ID-neighbours`, for example
the park11/12 office-neighbour scenes. Secondary pieces are reviewed with their
complete multi-tile parent rather than presented as standalone neighbouring houses.

Hotel/fountain water uses original animated palette245…249; the fountain spray uses
250…254 glitter phases; park11 also retains original pond animation. Do not replace
these with static blue paint. The fine jet has an explicit0.25×0.25×1 grid.
`--verify-voxel-water 8`, `10` or `11`, with a running benchmark,
observes five original colour phases on one captured model and checks that its mesh
actually emits animated indices. The observer is read-only and does not approve
source fidelity or every animation phase.

Use `smoke.py --gallery-voxels` for isolated, street and neighbour-context reviews.
Each model has four orbit views (0–3) and four six-unit-eye street views (4–7).
Use `--gallery-voxel-prefix airport_radar_sw_` for selected models and
`contact_sheet.py <directory> --animation-prefix airport_radar_sw_` for a frame strip.
`contact_sheet.py <directory> --gallery --voxel-model airport_glass_hangar --street`
selects a street sheet; category contexts use names such as `context-airport_tiles-0`.
`compare_galleries.py <reference-directory> <actual-directory>` compares every RGBA
pixel across matching exported/compacted voxel galleries; it does not approve source fidelity.

Fence galleries: `smoke.py --gallery-fence 0 1 2 3 4 5 6 --fence-slope 3` exports
four orbit/four street views for each family. Select them with `contact_sheet.py
<directory> --gallery --fence-style 1 --street --tight`. Railway-only
`--fence-layout 0..15` selects an upstream layout; slope33/layout2 is a raised west
half-tile, while slope253/layout3 is a steep northern half-tile. Pass the same layout
to the contact-sheet tool. `--reference-fence 0..6` locates actual field/rail geometry
without changing map state; `--verify-fences` checks palettes, terrain/diagonal
placement, exact CPU/GPU instances, gate partition equivalence and transparent picking.

Foundation galleries: repeat `--gallery-foundation SLOPE FORM` to export independent
sets, for example `--gallery-foundation 8 1 --gallery-foundation 29 5` (levelled north
slope and two-level steep north). `foundation-cases.json` lists the 66 supported review
pairs. Select a sheet with `contact_sheet.py <directory> --gallery --foundation 5
--foundation-slope 29 --foundation-context --street --tight`. Each pair has eight
isolated/ground and eight building-or-track context views. `--reference-foundation
voxel-house` (or `house`, `road`, `rail`, `station`, `industry`, `any`) locates an actual
matching structure without altering it. `--verify-foundations` checks all cases at
three detail levels and street angles, with exact instance/unit-cell/picking checks.

Foundation columns fit between the original soil and playable surface. Palette
rubble has shared three-dimensional grain, source-space stone proportions and
authored diagonal-wall shading. Hidden soil/top contacts are occupancy masks, not
coplanar stone caps. Close cells use 0.5×0.5×0.25; middle/far grids use 1×1×0.5 and
2×2×1. Their cell quads retain exact subpixel coverage. Upper ground surfaces remain
a separate part of the ongoing voxel migration.

Named `components` are reused with `["use","name"]` or an explicit cell offset.
`["erase_material","glass"]` removes that material from an inherited construction
volume, keeping openings genuinely empty rather than painting them black.
`["replace_material","old","new"]` preserves shape while changing occupied material
IDs in a derived model. `["scatter_paint", "material", frequency, seed, x0,y0,z0,x1,y1,z1]`
paints only existing cells in the explicit box. Frequency
1…1024 and unsigned32-bit seed select deterministic coordinate-hash grain without
simulation randomness. Use it for deliberately selected roof/masonry variation, not
automatic image conversion. Face-local palettes preserve recessed/interior shadows;
actual openings remain empty. `--house-source 0 4 5 6` on the contact-sheet tool shows
all16 native variant/construction references per house, including source palettes.
Append a material name after a scatter box to restrict painting to that occupied
material, for example `["scatter_paint","ripple",4,953,12,10,0,27,30,1,"water"]`.
This keeps pond banks and other details intact. `["ellipsoid","leaves",x0,y0,z0,x1,y1,z1]`
fills cells whose centres lie inside the explicitly bounded ellipsoid. It produces
axis-aligned voxel surfaces, not a smooth substitute mesh or image-derived foliage.
`["line","steel",x0,y0,z0,x1,y1,z1]` uses inclusive cell endpoints. Its canonical
direction and single-axis cell steps create a reversible face-connected wire or
brace, including diagonal3D members; out-of-grid endpoints and work-budget excesses
are rejected. The radio lattice and guy wires use this operation on a quarter-unit
horizontal grid. No simulation randomness or image-derived geometry is involved.
`["polyline","glass",[[x0,y0,z0],[x1,y1,z1],...]]` joins two to1,025 explicitly
authored integer cell points with that same reversible, face-connected traversal.
Component offsets, endpoint bounds and expanded-operation/work budgets also apply.
Repeating the first point closes a spatial rim while leaving its bore empty. Fizzy
glass paths use polylines to retain compact source controls and actual voxel volume.
`["rotate_z", angle, [pivot_x,pivot_y,pivot_z], operations]` bakes a component into
axis-aligned cells. Only positive-area XY cell intersections contribute, and nearest
source cells resolve material overlap deterministically. Cycles, clipping, invalid
angles and transform budgets are rejected. Horizontal cells must be square for a
Z rotation. `cell_size` can explicitly choose a finer detail grid; inherited models
retain their parent's cell size. Runtime animation selects the upstream frame and
does not rotate a smooth substitute mesh or change simulation animation state.
`palette_reference.py --indices 128 129 130 131` lists exact source palette colours;
`contact_sheet.py --preview --colours ...` reports matching indices from references.

These JSON files are the editable source artwork. Each part's proportions,
position and silhouette are explicitly authored. Current house/tree/vehicle
materials use the resolved **OpenGFX2 Classic 0.8.1** artwork with nearest sampling.
The same low-resolution base set supplies the original UI and every model category.
World textures start at native normal zoom; duplicated upscaled sprite levels are
excluded from the GPU atlas.

- `houses.json` and `trees.json`: runtime component assemblies.
- `industries.json`: initial mature industry components and explicit sprite
  bindings. Lathe profiles author hollow tapered walls and their top rims, with
  optional normalized source-image crops for wall, interior and rim materials.
- `vehicles.json`: named vehicle assemblies, shared components, loaded-cargo parts
  and explicit bindings covering all 256 vanilla engine definitions.
- `tools/assets/compile_vehicles.py`: validates those bindings, resolves assembly
  inheritance and extracts direction/cargo sprite metadata from pinned upstream
  tables. Its generated `opentt3d-vehicles.json` ships with the game. It generates
  no geometry from images.
- `models.json` and `tools/assets/compile_models.py`: earlier prototype sources and
  exporter, retained separately from the current world-scene path.
- `src/renderer3d/bridge_geometry.hpp`: current explicit bridge construction
  assemblies. `bridge_capture.cpp` attaches upstream-resolved materials, ramp
  directions and partial-column choices; no geometry is extracted from images.
- `src/renderer3d/terrain_geometry.hpp`: authored voxel fence structures and rubble
  retaining supports, cached by slope/layout/LOD. Face-local palette cells keep gate,
  hedge, post and wire colours separate within one volume; shared corner grain
  prevents conflicting coplanar caps. Foundations preserve the original height
  transform while replacing projected wall charts with stone cells.
- `tunnel_geometry.hpp`, `rail_geometry.hpp`, `station_geometry.hpp` and
  `ground_detail_geometry.hpp` in `src/renderer3d/`: explicit transport structures,
  paired station halls, crop growth, hay stacks and rock/snow components.

## Component materials

Runtime house/tree/industry parts can wrap explicitly chosen source charts around
an authored component instead of projecting the entire source sprite over it:

```json
["material", {"all": [0.65, 0.23, 0.80, 0.30], "repeat": [4, 4]}, [
  ["box", 0, 0, 20, 16, 12, 0.2]
]]
```

Rectangles are normalized `[left, top, right, bottom]` source-image coordinates.
Use `end`, `side`, and `top` to override X-facing, Y-facing, and roof/bottom charts.
`repeat` is measured in authored model units; omitting it fits the chosen chart
to the component. Triangle clipping at repeat boundaries preserves the original
surface, so charts do not interpolate across unrelated source pixels. A `colour`
RGB triple instead selects an explicit solid component material. `lit` defaults
to true. Lathe wall/interior/rim crops can also opt into `lit` face lighting, specify
`sides` and `angle` for circular/polygonal stacks, and use `vertical_repeat` in model
units. The compiler inserts profile rings at repeat boundaries to avoid UV seams
or stretched courses.

Industry tiles 8, 33, 39, 43 and 49 have first individual component passes: roof and
masonry charts exclude chimneys/glazing, which have their own geometry/materials.
Other models still need individual authoring and visual review; this feature does
not automatically approve them. `validate_models.py` rejects malformed runtime-pack
JSON before CMake copies it into the build.

## Vegetation components

All 62 tree sprite families now have separate `wood` and `foliage` groups. Natural
crowns use explicitly selected `foliage_crop` rectangles, optional per-stage crops,
and nearest-sampled repeats at approximately **two native texels per physical world
unit**. The native crop size, growth scale and physical branch/leaf coordinates
determine the repeat period, consistently across texture LODs. Fragment repetition keeps
small leaf charts from multiplying the triangle count. Named `bark_materials` bind
explicit source sprites/crops to model IDs; branch UVs follow the physical arc and
length through bends. `wood_colour` tints these charts relative to their authored
`reference_colour`. Snow aliases select their own bark material.

`tree_materials.scale` is an authored `[horizontal, vertical]` proportion adjustment,
independent of sprite framing. `growth` has seven stage scales. Natural dead trees
retain their authored branch structure; `retain_dead_foliage` keeps the original
solid succulent/Toyland form. `foliage_charts` uses ordinary per-part `material`
wrappers for Toyland colours, bands, ribs and spots instead of repeating leaf crops.

`tree_geometry.hpp` provides closed tapered branches, lobed crowns, drooping boughs,
folded leaf blades, paired palm leaflets and turned sector profiles. Shape seeds are
explicit modeling parameters, not simulation randomness. All three LODs share one
culling envelope. Fine geometry switches at 12/32 projected pixels; distant branches
omit unresolved twigs while retaining the tree volume. `renderer3d verify-trees`
checks all lifecycle/LOD combinations, independent material visibility, palettes,
transparent picking and CPU/GPU agreement. These checks do not set visual approval.

Batch turntables: `smoke.py --gallery-house 1579 1600 1950`; select a result with
`contact_sheet.py <directory> --gallery --gallery-model 1600 --tight`.

Natural turf and rough surfaces live in `clear_surface_geometry.hpp`: explicit
solid blades, pebble/mound layouts, Toyland pips and independently toned source
grain. Ground uses one complete bare-earth chart per tile, avoiding the former 8×8
repetition of a tiny crop. Raised grass and stone details share the physical texel
density policy. `--gallery-ground-detail 3 3 0` selects mature grass; kind 4 selects the five
rough layouts. The option can be repeated, and `contact_sheet.py --gallery
--ground-detail 4 0 --tight` selects a batch turntable. These models conform to the
same terrain triangles and tunnel cuts as the original ground capture.

Units match OpenTTD: a tile is 16 × 16 world units and one terrain height level
is 8 units. Buildings use a tile-local origin; vehicles are centred and face +X.
Vehicle components include boxes, prisms, elliptical cross-section sweeps and
explicit transforms. Geometry is shared between engines using the same assembly.
Directional source-pixel UVs stay attached to each mesh as it turns.

The pack is **incomplete**. The manifest distinguishes reference models from
development placeholders. A reference model is not yet a claim of finished
artwork: visual matching, material detail, and state coverage need review.

## Attribution and license

Model geometry and assembly: OpenTT3D contributors, 2026, GPL-2.0-only.
Current visual references: OpenGFX2 Classic 0.8.1, OpenGFX/OpenGFX2 contributors,
GPL-2.0-only. The authoritative current pin is `opentt3d/upstream.json`.

The older `models.json` prototype references OpenGFX 8.0 revision
`e68bd9b7cb60305aa98c687b6836e0e0b08e2847` in
https://github.com/OpenTTD/OpenGFX. Each model lists its reference paths. Original
per-sprite credits are in OpenGFX's `docs/authoroverview.csv`, available at that
revision. The compiled model library is distributed together with these sources.

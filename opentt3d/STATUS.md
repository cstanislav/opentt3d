# Implementation status

This file records implemented and verified work, not promises of completeness.

## Baseline

- [x] Public fork with original history: `cstanislav/opentt3d`.
- [x] OpenTTD 15.3 and OpenGFX2 Classic 0.8.1 pinned by full commit and archive checksum; Classic supplies both UI and model textures.
- [x] Container build and upstream tests verified (97 tests, Linux ARM64).
- [x] Native macOS baseline built; 96 upstream tests passed.
- [x] Native macOS mesh-renderer launch and framebuffer captures verified on Apple M3 Pro.
- [x] Current native suite201/201, including original factory child motion, source-specific Toyland industry restrictions, automatic LOD reduction/residency, doubled rendered slopes, train physical pitch/contact, retained-source reconstruction and copied-scene/active-worker residency. Printing`.17`, tram`.18`and steel`.1`pass every CI job. The electric-collector crash is locally reproduced with3,000ms presentation stalls and repaired by full-elapsed analytic smoothing: both delayed controls,8 clean local controls and release`.6`'s900-frame Linux support/collector journey pass.
- [x] Current1,624-volume catalogue passes its source/build and prior-model audits; asset/compiler/schema suite136/136 and downloader/screenshot/memory harness12/12 pass. New source-authored artwork remains under source/state/street review with zero final approvals.
- [x] Linux Mesa/llvmpipe mesh-renderer smoke test inside Docker/Xvfb.

## Renderer

- [x] Factory143 child capture preserves the original50-frame order/absence sequence,
  conveyor+X and press-Z motion. An isolated artwork study passes one unchanged
  tile/industry's full cycle after ordinary supply delivery. Missing-holder fallback
  retains all six independent grounds. Native model-origin and all-frame procedural
  source comparisons are available; the twelve study volumes await integration.

- [x] Fizzy156…159 adds six hollow-can/glass-apparatus bodies and independent4676 soil,
  preserving eight empty body slots. Coverage reaches154/175 primary definitions,
  115 body owners and154 grounds. All26 controls,48 actual construction layers,
  24 palettes,26 aliases,96 climate comparisons and1,617 preceding hashes pass.
  Both backends observe five phases across all five emitted bubble indices on each
  actual157/158/159 body; legacy steel regressions and missing-material negatives pass.
  All28 native views agree. Construction ownership overlap and fine fidelity remain open.
- [x] Compact authored polylines reuse the bounded, reversible face-connected line
  traversal. Translated closed-bore, malformed-path and expanded-budget controls pass.

- [x] Plastic-fountain148…155 adds eight completed splash poses and eight independently
  animated recessed basin grounds; all24 early body slots remain empty. Coverage
  reaches150/175 primary definitions,112 body owners and150 grounds. All24 controls,
  30 actual construction layers,40 palettes,48 aliases,192 climate comparisons and
  1,601 preceding hashes pass. Both backends observe all eight matching ground/body
  poses on one unchanged live tile. Missing-binding/paused negative controls reject.
  All48 native views agree; non-native differences and source fidelity remain open.

- [x] Toy-shop138…141 adds eight provisional castle bodies, preserving five empty
  construction slots, the courtyard/gateway and independent Toyland2022 soil.
  Coverage reaches142/175 primary definitions,104 body owners and142 grounds.
  All26 controls,54 actual construction layers,27 palettes,27 aliases,96 climate
  comparisons and1,593 preceding model hashes pass. All27 native backend views agree.
- [x] Optional ordinary third-industry input service supplies a processing factory
  through a separate full-load/delivery/return truck. Battery→factory→town-shop service
  passes17/17 input/output cargo and both returns; the existing two-industry regression
  retains its740-tick result. Original industry-spacing restrictions remain in force.

- [x] Cola137 adds three provisional bowl/cup/straw volumes and shares exact Toyland
  checker soil. Primary industry coverage reaches138/175 definitions,101 body owners
  and138 grounds. All24 controls,16 actual construction layers, real full/empty cargo,
  8 palettes,7 aliases,24 climate comparisons and1,590 preceding model hashes pass.
  All16 native backend captures agree; wider differences and fine fidelity remain open.
- [x] Explicit lathe centre offsets support leaning hollow profiles with bounded
  geometry and inward-only face lining. Compact cola geometry preserves every cell;
  only132 inward step-cell colours change. Gallery completeness distinguishes truly
  transparent base artwork from visible missing bodies, with positive/negative controls.

- [x] Battery135/136 adds five provisional bodies and shares cotton's exact Toyland
  soil, bringing primary industry coverage to137/175 definitions,100 body owners
  and137 grounds. All28 frozen controls pass, including16 live construction layers,
  loaded/empty trucks, both unchanged-tile harvest/regrowth cycles and four legacy
  timber/cotton regressions. All16 palettes,18 aliases,48 climate comparisons,
  1,585 prior model hashes and20 native backend captures agree. Fine fidelity remains open.
- [x] Original Toyland procedural export covers268 construction/completed states,
  108 distinct poses and23 resolved child images. Independent source tables, palette,
  ordering/offset and absent-state audits pass, preserving596 earlier original images.
  Child voxel artwork remains required; exported imagery does not establish coverage.

- [x] Sweet-factory131…134 adds ten provisional volumes, bringing primary industry
  coverage to135/175 definitions,98 body owners and135 independent grounds. Four
  original131 bodies stay empty. Gift wrapping, partial unwrapping and the finished
  peppermint-roofed hall retain both source layouts,28 palettes,27 aliases and the
  distinct Toyland2022 soil. Twenty-four controls pass56 actual construction-layer
  selections,17/17 and0/17 cargo, four climates, service and bundles. All1,575 prior
  model hashes and36 native backend captures agree. Fine fidelity remains provisional.

- [x] Cotton129/130 adds six provisional volumes, bringing primary industry coverage
  to131/175 definitions,95 body owners and131 independent grounds. Four growth states,
  harvested bare sticks and checker soil retain all16 palettes/18 aliases and distinct
  Toyland source guards. Twenty-four fresh frozen controls pass, including16 actual
  construction-layer selections, loaded/empty cargo, bundles and both unchanged-tile
  harvest/regrowth cycles. Timber regressions and all1,569 preceding models agree.
  Exact crown registration/paint remains provisional; this checkpoint precedes sweets.

- [x] Diamond91…99 adds26 provisional volumes and brings primary industry coverage
  to129/175 definitions,93 body owners and129 grounds. All21 empty body states and
  26 source aliases remain. Source91's upright hoist stands over95's ground-owned
  shelter; an earlier leaning-frame revision is retained. Twenty-four frozen controls
  pass102 actual construction-layer selections, four climates, full/empty diamond
  service and bundles. All1,543 previous models agree. Exact rock/source registration,
  paint and platform detail remain provisional; this checkpoint precedes cotton.

- [x] Apple's software OpenGL missing-triangle defect is reproduced and repaired
  locally with explicit homogeneous clipping. Five frozen controls, three package
  launches and72-view/21,180-sample ray-based checks pass, including ordinary/packed
  voxel paths, mixed ground and exact draw-order/picking regressions. The new
  extracted-package gate rejects the deliberately disabled correction. The title
  capture's88,931 black pixels disappear;10 hardware/software pixels still differ.
  Published`.14`passes every hosted job and independent attachment audit. Both hosted
  Mac software-OpenGL captures have zero black world pixels and differ from the
  matched Vulkan image at nine pixels. All seven hosted graphical package controls
  pass the72-view ray-based gate.

- [x] Arctic/tropical bank89/90 adds four provisional volumes, bringing industry
  coverage to120/175 definitions,88 body owners and120 independent grounds. Original
  finished-body construction aliases, separate completed paving, joined columns and
  dome ownership are preserved. All1,539 prior models agree. Twenty-eight controls
  pass, including64 actual construction-layer selections and ordinary gold service.
  Native registration and source/street fidelity remain provisional.

- [x] Seventy airport-surface volumes bring primary airport coverage to 73/74 and
  independently bound grounds to 74/74. Explicit climate/frame ground selection
  preserves distinct grass, taxiways, worn airfields and small runways; identical
  triangular overlays retain independent body ownership. All 1,468 earlier model
  hashes agree. Twenty background controls pass, including 8,016 visibility/picking
  views, live animations and aircraft contact. Final source/street fidelity remains open.

- [x] The elevated heliport brings primary airport coverage to74/74, with56 body
  owners and74 independent grounds. Its local60-unit deck remains unscaled above
  doubled terrain. All120 Guru/84 Powernaut support corners meet actual captured deck
  triangles. Twenty background controls pass four climates,192 visibility/picking
  views, original rotor stop/restart, development bundles and the oil-rig regression.
  All1,538 prior models agree. Separate Toyland body paint and final fidelity remain open.

- [x] Normal launches request3D without developer environment variables. Explicit
  `OPENTT3D_RENDERER=0` retains the original comparison renderer. The dedicated
  desktop-release workflow publishes Windows x64/x86/ARM64, macOS arm64/x86_64 and
  Linux x86-64 packages in release`.16`. Every hosted job passes after the unchanged
  Linux retry; the first missing-ascending observation remains recorded. All19 public assets,
  18 checksum entries,2,067 exact-commit source files and all six embedded package
  commits are verified. Mac signatures/dependencies/minimum15.0 and published local
  launches pass. Hosted ARM software OpenGL passes the repaired clipping gate and
  reviewed screenshots; Windows GPU/input and ARM64 native execution remain open.

- [x] Gold72…88 adds52 provisional volumes and82 independent body/ground layers,
  preserving54 empty bodies, the three original wheel poses, cross-owner roof/trough
  joins and distinct Toyland water/soil restrictions. Coverage reaches86 industry
  body owners and118 grounds. All24 reconciled background controls pass, including
  148 actual construction selections, full/empty12-unit gold delivery saves, both
  app bundles and18,000-frame live animations on both backends. All1,416 preceding
  model hashes agree; peak sampled memory is3,411,643,800bytes. The town-bank route
  uses ordinary public commands; the existing copper delivery route also passes.

- [x] Copper47…51 adds14 provisional bodies with all construction selections and
  three original wheel poses. Open frame, hollow flues, recessed bays and separated
  storage rows have support/clearance regressions. Coverage reaches81 industry body
  owners and101 independent grounds. All24 final background controls pass, including
  44 actual construction-layer selections, full/empty22-unit cargo captures, both
  app bundles and live three-pose wheel observations on both backends. All1,402 prior
  model hashes agree; peak sampled memory is3,060,075,880bytes. The Linux memory
  sampler now reports zombie/disappeared-process exits without masking the retained
   game log or fabricating zero-memory samples. The later full-elapsed timing repair
    passes local controls and the later`.6`Linux collector/support observation.

- [x] Iron-ore100…115 adds48 provisional ground-owned volumes, including terraced
  workings, boundary posts, raised hopper, open construction frames and joined roofs.
  All64 original body states stay empty; only source-identical1/2 stages alias.
  Coverage reaches96 industry definitions with ground bindings and76 body owners.
  All24 final background controls pass, including128 actual ground selections,
  full/empty22-unit delivery saves, both app bundles and two9,000-frame electric
  support/collector journeys. Peak sampled memory is3,257,437,472bytes. All1,354
  prior model hashes remain unchanged. Collector errors now include numerical pose
  inputs; temporary slow-frame injection is removed, and no crash repair is claimed.
- [x] Steel-mill52…57 adds28 provisional volumes for exposed construction frames,
  glazed roof bays, hollow flues, open furnace mouths and separate ground-owned
  machinery/molten metal. Only original-identical construction1/2 stages alias;
  tile55's middle/completed bodies remain empty. Coverage reaches76 industry bodies
  and80 grounds. The new read-only palette observer checks actual emitted fire
  materials through their original animation phases. All24 final backend/bundle
  controls pass, including90 actual construction layer selections,12 live palette
  observations and the normal iron-ore truck's full/empty delivery states. Peak
  sampled memory is3,181,382,944bytes; all1,326 previous model hashes are unchanged.
- [x] Twelve tram-depot volumes add the final depot family: all6 families/24 exit
  bindings now have voxel bodies, with separate oriented floors/embedded rails and
  contact wires. Source-climate comparisons permit exact cross-climate body reuse.
  Source offset selection now recognizes the original tram depot; a fixture-only
  no-graphics NewGRF enables a normal public-NoAI tram route and all four depot exits.
  All46 final backend/bundle controls pass, including32 actual exit selections and
  four observed vehicle/depot traversals. Peak sampled memory is2,676,313,088bytes.
- [x] Printing43…46 adds13 volumes with distinct construction, tiered joined roofs,
  four open flues, exposed workshop rafters and an open courtyard. Tropical factory
  121…124 shares39…42 only after128 climate/layer comparisons agree in pixels and
  registration. Coverage reaches70 industry bodies/74 grounds. All26 final backend
  checks pass, including32 printing bodies,62 tropical ground/body selections and
  the delivered-wood context. Peak sampled memory is2,675,067,928bytes.
- [x] Factory39…42 adds fifteen provisional volumes, including both original
  multi-block layouts and independently owned completed lower walls/paving. The
  completed42 body remains empty. Coverage reaches62 industry bodies/66 grounds.
- [x] A478-layer Toyland audit identifies215 source replacements. Climate guards
  now preserve distinct soil/rig layers and only paper67's changed completed body;
  unchanged construction and other independent owners retain their voxel bindings.
- [x] Tropical lumbermill125…128 adds twelve volumes with independent bare soil,
  all four construction selections, joined open canopy and supported timber stacks.
  Both backend geometry/state matrices, eight actual construction runs and four
  loaded/empty wood-truck captures pass; a public-command delivery/return is verified.
  Industry coverage reaches58 body/62 ground definitions; final artwork approval is open.
- [x] Ground-only airport33/34 buildings retain original opaque ground ownership;
  tile35 keeps independent office/paving and cabin/tank layers. Coverage reaches
  53/74 definitions,47 body owners and35 independent grounds. Both backend focused
  meshes and all six non-temperate airport matrices pass; older distinct Toyland
  terminals/hangars retain supplied art pending independent volumes.
- [x] Terrain steps render8→16 while retaining authored object dimensions. Raised
  foundations, bridge ramps/pillars, rails/catenary, tunnel earth and dock decks/piles
  pass the updatedGL/Vulkan infrastructure, ground-continuity, atlas and picking checks.
- [x] Four model LOD levels are generated automatically from authored cells, with
  nearest-bound screen sizing, palette-aware deterministic reduction and scene-pinned
  cache retirement. Native reduction/thin-part/bounds/reconstruction regressions pass.
- [x] Projected-material3D trees restored as the default per the user's performance
  instruction. Matched pre-terrain300-frame controls improve12.08/13.24→22.71/29.50fps
  with voxel LODs, then54.89/60.02fps with projected trees. Sloped roofs are permitted.
- [x] Both scene/navigation and62-family projected-tree matrices pass. Corrected
  electric23 routes complete9,000 frames/backend with doubled-grade wheel support,
  all four corner tracks and independent surface/portal/tunnel collector contact.
- [x] Rooted-tree/culling and steeper electric23…26 pose matrices pass on both backends.
  Both1,800-frame helicopter254 controls retain the local54-unit oil-rig deck,120
  support corners, all rotor states and restart.
- [x] Final portal-bank continuity, both live tree-style selections, exact atlas/picking
  and six matched performance controls pass. The updated local macOS app matches the
  frozen reviewed executable; all local native review processes have exited.
- [ ] Arbitrary-world smooth60fps remains unmet: final dense-Cab projected-tree controls
  average49.477/60.000fpsGL/Vulkan, with154/0 intervals over20ms. Catalogue/source-fidelity
  completion and complete current Linux verification remain unproven.

- [x] Matched expanded1,169GL/Vulkan matrices complete below6GiB with scene-pinned
  CPU surfaces and cold immutable GPU-page retirement:5,779,248,360/5,359,801,360bytes.
  Exact geometry, palettes, transparency, all climate/cargo bindings and world picking
  survive retirement/rebuild. Active geometry may exceed either soft cache budget.
- [ ] Smooth dense-world/Cab performance remains unmet: the concluding expanded-control
   samples average12.714/14.058fps. Interactive cache churn and Linux follow-up remain open.
- [x] Opt-in tunnel-tree visibility regions preserve exact RGBA/picking across20
  actual near-mouth/interior/exit, four-heading and tilted-Cab views on both backends.
  Matched90-frame dense-Cab controls improve11.40/12.73 to38.11/40.33fpsGL/Vulkan,
  reducing submitted vertices664,706,778→197,335,923. The optimization remains
  disabled by default; broader tunnel/climate/world review and60fps remain open.
- [x] Wider tunnel visibility controls pass all ten four-railtype/Toyland backend
  cases plus both18,000-frame moving-Cab runs:240 exact comparison views and
  55,296,000 RGBA/picking pixels; peak2,962,001,184bytes. Route timing still has
  missed deadlines/stalls, so production60fps remains unapproved.
- [x] Hidden native macOS framebuffer review with `--background`: GL, Vulkan and
  LaunchServices bundle report no activation/key/visible window and capture2560x1600.
  Same-backend56-view comparison preserves22,937,600 RGBA pixels; foreground interaction
  and cross-backend raster agreement remain separate unfinished reviews.
- [x] Memory incident reproduced under a6GiB guard; fixed duplicate CPU visibility results, per-frame GL instance-buffer replacement, historical transform retention and idle cancellation release. Native186/186 tests and6,000running GL frames complete (234seconds,5.86GiB sampled peak); same-catalogue original-mesh comparison matches16,384,000 RGBA pixels. Native Vulkan tree/order/atlas/live checks peak3.93GiB. Failed intermediate runs remain recorded.
- [x] Default one-worker GL follow-up completes1,200running frames plus exact storage/composition checks below6GiB (5.74GiB peak). Updated development app matches the final native executable; the preserved pre-fix executable also matches all16,384,000 world pixels with the same catalogue/backend/blitter.
- [ ] Arbitrary-map/multi-viewport/all-day memory limits and post-fix Linux/no-Vulkan execution remain unverified. The completed native memory soak is fixture-scoped, and GL remains26.86110fps rather than smooth60fps.
- [ ] Wide-view tree throughput remains below target. Original geometry reaches approximately2.52billion captured tree source vertices/frame; opt-in exact visibility/capture changes reach57.39769fps Vulkan and31.94751fps GL in6,000-frame asynchronous runs. Startup spikes, camera latency and foreground/hardware coverage remain unresolved; original approximately3fps failures are retained. No quality/distance/tolerance reduction hides the failure.
- [x] GL3.2/GLSL150 texture-buffer visibility, exact indexed references and reusable ordered pages preserve all4,096,000 control pixels. Native/Linux/no-Vulkan checks include5,712 distant parent/child cases and five1025-instance edited-stream cases, with actual background live runs. Hardware subpixel precision and original stream order remain respected; performance remains unapproved.
- [x] A diagnostic-order-dependent Toyland house108 pixel is traced to fractional atlas-origin cancellation. Sprite-local instance UV bias removes the loss in both shaders/CPU expansion; whole-world repack/clear/forced-row tests and original-reference comparisons pass. Direct palette lookup also invalidates before page eviction, with an actual source-node-reuse regression.
- [x] Full495 native Vulkan/Linux core/sync regressions complete11,880 mesh views,165,376 vehicle poses/304 bindings,16,968 tree views and2,856 distant visibility views, plus renderer/picking checks. Lossless packed vertices, original-triangle visibility and direct tree capture preserve the complete paused reference world; these are correctness checkpoints, not default-path or performance approval.
- [x] Native house reference crops fit actual projected geometry and retain tile-origin sidecars. This fixes the suspended office being cut at-96 instead of its-108 source top; registration sheets preserve both complete images at native scale.
- [x] Identical-binary paused GL captures expose allocation-dependent coplanar pixels. New CPU/GPU regressions reproduce changed colour and picking when only mesh allocation changes. First-captured batch order within explicit parent/child layers removes pointer sorting; both backends repeat4,096,000 paused-world pixels exactly. Native GL/Vulkan and Linux core/sync full416 checks pass9,984 model views/165,376 vehicle poses, including32 allocation/828 fence views. Focused Linux GL3.2/no-gpu-shader5 ordering, fence and3,264 wagon poses pass.
- [x] Vulkan skips zero-heading rotation work; the GL experiment is not retained after slower throughput. The earlier416-volume wide results were52.45036fps Vulkan/45.61511fps GL; the newer494-volume failure is recorded above. Exact tests remain required; global60fps remains unmet.
- [x] Cargo-deck/rim verification reproduced two exact colour-pixel differences between cell and greedy meshes. Thin rectangles and two-sided coplanar-colour guard strips retain reference diagonals without changing geometry or logical rectangles; interiors still merge. Full native/Linux renderer and transport regressions pass, with current5,976 model views/50,048 vehicle poses. Triangle cost and still-unmet wide performance are recorded.
- [x] Expanded vehicle checks reproduce a one-colour-pixel CPU/GPU face-boundary mismatch on Toyland mail129. Separately rounded CPU products fix compiler-only FMA contraction. Exact38,080 poses pass; a broad shader-precision experiment was removed after a36.2fps wide regression, recovering54.4fps with the CPU-only fix. Final212-volume native/Linux checks pass5,088 model and1,176 tree views; no source or complete performance approval.
- [x] Equipment hall9/gantry10 and six original spark poses extend the catalogue to145 volumes. Actual six-child observations pass on native Vulkan/GL and Linux GL. A strict1-pixel parent/child failure is fixed with explicit draw layers;24 GPU order/depth/picking cases and48 combined spark poses pass. Visible-alpha source audit corrects the padded transformer reference and records remaining house/source/ground defects. No visual approvals; full scope stays open.
- [x] Power-station cooling tower7 and boiler hall8 add five construction volumes, explicit hollow profiles, connected supports and open flues; source2048 remains blank. Inward-face palette painting fixes exterior lining leakage and preserves painted grain/rims. Public-NoAI state fixture, source/street/layout refinements and native/Linux checks pass. Current136 volumes/3,264 general views; zero approvals and full scope remain open.
- [x] Reproduced low-angle ground gaps (732pixels), aligned first substrates at map height and conformed voxel/checker contacts without subdividing ordinary whole-tile edges. Independent24 flat/two-ramp/rotation/large-origin coverage views pass native Vulkan/GL and Linux core/sync/GL. Full terrain/overlay/fidelity review remains.
- [x] House14 adds three common-footprint shop/office states, original ground-layer comparison, open construction bays and actual0/1/2/3 evidence. Current131 volumes/216 house bindings/3,144 general views; source fidelity and all-model alignment remain WIP. Footprint inventory now records occupied/contact bounds; red-Z/mine shifts supersede earlier bounds-only registration claims.
- [x] Depth-tested viewport mesh rendering and offscreen framebuffer composition.
- [x] Classic 40bpp native toolbar/status-bar comparison with official 15.3: 254,448 identical pixels; earlier HighDef checks remain historical evidence.
- [ ] Original UI clipping, overlapping windows, and palette handling.
- [x] Shared CPU/GPU perspective projection, focal-plane art proportions and quarter-turn camera mathematics.
- [x] Quarter-turn controls and camera-aware town/station/sign placement.
- [x] Loading, income and feeder-income effects retain world anchors and reproject per viewport; 48 orbit/dolly/Cab/secondary-view checks plus legacy-slot reuse pass.
- [x] Terrain-ray picking and cursor-anchored zoom/drag, including slope and retaining-wall cases.
- [x] GPU depth/vehicle-ID agreement, child-overlay IDs, and transparent click-through checks.
- [x] Geometry-aware tile ownership for building/infrastructure clicks, full 24-bit map indices and independent vehicle IDs; actual viewport input entry point verified across four rotations.
- [x] Elevated vehicle-follow pivots and camera snapshots for screenshot viewports.
- [x] Tiled GPU screenshots, complete-PNG detection and pixel-identical synthetic tile seams.
- [x] Calibrated square-pixel pinhole lens, reduced tall-building lean and continuous yaw.
- [x] Middle-button orbit; frame-rate-independent dolly zoom, with a −6 street-level close limit.
- [x] Fixed 40° viewport/Cab lens, disabled Cab zoom, and terrain-relative zoom-range recovery after orbit/pan.
- [x] Cocoa input recovery: `pass1-494-bundle-input-recheck` passes32 focus/capture cycles and four fullscreen transitions through LaunchServices. Earlier `front=loginwindow` failures remain retained; longer manual interaction/foreground performance remain open.
- [x] Reproduced polling cancelling delivered mouse-down events; event-authoritative button lifetime now passes real NSApplication/window dispatch, right/middle holds/releases and the focus/fullscreen probes.
- [ ] Longer native mouse/trackpad and construction interaction playtests after the repeated focus/capture probe.
- [x] Clicked-terrain-point yaw and vertical tilt, persistent release, tilted pan/zoom and screenshots; Cab free-look in both axes.
- [x] Reproduced close-orbit float-rounding drift at large map coordinates; compensated focus bits now survive orbit, anchors, dolly, snapshots, projection and culling. Large-world CPU regression and eight exact GPU/local-coordinate colour/picking views pass; the original failing city view passes without tolerance changes.
- [x] Infinite-far reversed depth on Vulkan/OpenGL; no fixed first-person geometry, terrain, picking or label cutoff.
- [x] Vehicle-window Cab button, smoothly turning first-person follow, and autoreplace/cancel handling.
- [x] Repeat-textured ocean outside the map when infinite-water generation is selected.
- [x] Frame-time benchmark harness and native MoltenVK device feasibility probe.
- [x] Benchmark-only captured-geometry breakdown by tile/vehicle ownership, with separate foundation, fence and running-track totals; wide-map GPU cost remains unresolved.
- [x] Vulkan game backend on Cocoa/MoltenVK and SDL/Mesa; GPU-resident world/UI composition and on-demand picking.
- [x] OpenGL resident viewport colour/ID/depth, original UI/animation shader composition, one-pixel picking and explicit screenshot readbacks. Cocoa shared-context producer/consumer synchronization, two-frame GPU backpressure and upload-before-Paint ordering.154,300 exact RGBA composition checks and8,192,000 full-screen RGB comparisons across32/40bpp pass; Windows runtime remains open.
- [x] Bounded6,000-frame fullscreen GL aircraft Cab improves over the CPU control from40.151fps/6,000overruns to59.948fps/63overruns. Full-image readback/CPU-copy costs are removed, but cold-frame, foreground and sustained smoothness work remains.
- [x] CPU samples reproduced world/UI palette updates waiting on in-use textures; frame-local palette revisions and cursor-inclusive retirement remove those waits. GL skips redundant opaque instance passes; a reproduced Linux GL/Vulkan0.99-boundary issue retains exact unpartitioned order where needed. Wide GL now50.834fps; current aircraft Cab60.003fps/16overruns. Both full-screen blitter comparisons remain exact; full performance approval stays open.
- [x] Immutable terrain/model instances, conservative culling, curved-mesh LOD and reusable capture storage.
- [x] Shared reusable instance-batch staging for GL/Vulkan, stable batch ordering and stale-scene retirement checks.
- [x] Persistent Vulkan meshes share append-only GPU buffer pages; nonzero offsets, oversized meshes, growth/reuse, colour and picking verified. Moving fixture: 675 meshes in 13 buffers.
- [x] Exact immutable-mesh vertex indexing in Vulkan/GL, preserving all 80-byte vertex data and triangle order; 16/32-bit paths, oversized buffers and original-stream fallback verified. A paired 592-image gallery matches 252,057,600 RGBA pixels exactly.
- [x] Palette-only instance batches use raster backface culling; mixed sprite overlays retain their original path. Wide title improves from 38.152 to 58.204 fps with indexing, but 502/600 work overruns remain. Current Cab cache: 677 meshes /18 buffers /71,511,632 used bytes.
- [x] Profile-guided hashed instance lookup, now with allocation-independent first-captured per-layer draw order; inactive Cocoa cursor resets avoid per-frame accessibility-image rebuilding.
- [x] Bounded 96 MiB source cache retains the exact upstream mip families; direct-decoder pixel/padding/framing checks pass on both platforms.
- [x] Immutable voxel-tree lifecycle masks avoid repeated string/tuple membership searches in wide captures; original-sprite provenance refreshes on texture-generation changes. Paired Vulkan43.589→56.584fps and GL40.531→49.510fps, with4,096,000 identical paused RGB pixels and tree/picking checks. Wide60 remains unmet.
- [x] World materials use native Classic or coarser pixels; vegetation charts share a physical texel-density target and clear ground uses one full tile instead of an 8×8 repeated crop.
- [x] Actual swapchain captures, GPU timestamp profiling, core/synchronization validation and no-Vulkan fallback build.
- [x] Earlier bridge checkpoint: running title at 2704×1756, integer zooms −3…5 averaged approximately 60 fps, 300 frames each.
- [x] Tree-checkpoint 2704×1756 running-title dolly matrix −6…5 averages 60 fps, one work overrun across 3,600 frames. The latest pooled dense map-centred 600-frame run has zero work overruns.
- [ ] Complete sustained smooth-frame-time coverage: later pooled and unpooled 6,000-frame Cab runs both expose an approximately one-second queue-submission stall. New per-section diagnostics retain that failure; foreground/all-climate/hardware coverage remains. See `PERFORMANCE.md`.
- [ ] Camera-aware terrain, vehicle, and sign selection.
- [ ] All secondary viewports, construction tools, overlays, and screenshots.
- [ ] Performance and lifetime checks.

## Artwork

- [x] Reviewed development catalogue1,247 JSON volumes,110 house definitions with body or ground geometry,109 independent body/88 ground definitions,62 tree families/434 lifecycle volumes and256 voxel vehicle definitions. Industries have54 body definitions and58 independent ground definitions; airports have21 body definitions and3 independent grounds. No final approvals.
- [x] Oil-well29…32, temperate farm33…38, bank58/59, food60…63, paper64…71, plantations116/117 and waterworks118…120 preserve independent grounds, source-empty construction slots and source-permitted repeated artwork. The80 accepted hidden actual-state runs pass240 grounds,198 visible bodies and42 deliberate empty body states, including both food climates and both backends; peak2,704,411,720bytes.
- [ ] Independent Arctic farm33…38 volumes remain missing. Source review finds40/44 layers differ, including a different farmhouse structure. The eight earlier Arctic binding runs are revoked as climate-coverage evidence; the current renderer retains supplied Arctic ground/body artwork instead of temperate voxel or legacy profiles.
- [ ] The expanded323-pair industry climate audit also finds snowy Arctic forest16/17 replacements and distinct soil3924/oil-well2173 grounds. Those layers now retain their supplied source outside temperate; unchanged coal/power/refinery/pump bodies remain independently voxel-bound. Complete climate-aware industry coverage is still missing.
- [x] Low airport terminal63/64/69 retains an open L-plan courtyard, supported parapets, recessed entry, original fence ownership and separately opaque2634 apron. Both backend galleries pass96 mesh and72 ground/body visibility views plus exact atlas/picking; all27 climate-source layer pairs match exactly. Source review fixed a perpendicular-pier paint brush that covered the side windows. Fine roof/window/paving fidelity remains open.
- [x] All eight9,000-frame curved-route runs pass for electric locomotives23…26: actual traversed corner-track bits, station/flat/grade/bridge/tunnel support and collector contact onGL/Vulkan. Peak2,816,019,552bytes. This is functional contact evidence, not smooth-frame-time approval.
- [x] All20 loaded-route support observations now pass, including the three remaining Toyland engine6/wagon52 cases. Both backends also observe all six original oil-well pump volumes through graphics30/31/32, and helicopter254 passes120 actual54-unit oil-rig deck supports plus every rotor state/restart. Swept-rotor contextual clearance and water/light phases remain open.
- [x] Eleven oil-rig volumes preserve all six original tile positions, four pilings/paired braces, intermediate platforms, completed derrick/flare and the54-unit landing deck. All20 actual construction selections pass, including the completed neutral station's water ground. Both native backends pass264 new mesh/1,616 industry-state views, exact atlas/picking and helicopter253 support/rotor observations. Source-registered joined and street views are retained; finer artwork, broader helicopter clearance and water/light phases remain open.
- [x] All35 locomotive body definitions have bindings:38 new volumes cover33 definitions and repair the older SH electric wheel gauge. Seven Arctic/tropical pairs retain different bodies;13 permitted source-climate pairs match208 views/58,808 RGBA pixels. Both native backends pass46,784 locomotive poses and1,344 rail/depot mesh views, with exact world-atlas checks below6GiB.
- [x] All55 locomotive/climate/railtype fixtures complete service, return and holding; all55 hiddenGL actual-selection captures pass below6GiB. Twelve additional public-NoAI train consists complete real bridge/ramp/tunnel journeys across all climates and original railtypes; rendered clearance review remains active.
- [x] Recalibrated train Z grids preserve XY footprints and the0.5-unit running support plane while clearing the faceted tunnel lining/ribs in every bound empty/loaded body. Three independent collector volumes follow each shoe's surface/portal/tunnel wire height; all four engines pass hidden live observation on both backends. Full1,133-volume GL/Vulkan matrices each pass27,192 mesh views,322,048 body poses and10,880 joined collector poses below6GiB.
- [x] Reproduced the locomotive LinuxVulkan tunnel failure locally: a tree root obscured640 lining pixels. Bounded bore clipping now accounts for each tree's local offset. The preserved CI saved world passes243,635 unobstructed lining pixels, unchanged vehicle state and exact atlas checks on nativeGL/Vulkan; Linux rerun remains required.
- [x] Eleven sawmill volumes bind industry11…15 construction, completed roofs, cutting machinery, logs and boards, retaining six original empty early bodies and all five independent grounds. Both backends pass264 new mesh views and840 industry body/ground views; all20 actual construction-state selections pass. The published candidate has1,144 volumes,13 industry bodies and16 industry grounds; final visual approvals remain zero.
- [x] Six forest volumes bind16/17 growth/logs/litter; both backends pass the unchanged-tile mature→dispatch→all-four-regrowth observation over9,000 frames. Nineteen refinery volumes bind18…23 construction, hollow vessels/open frames, flare/cooler/office and independent soil/paving. All24 actual refinery body/ground selections pass. Candidate totals are21 industry bodies/24 grounds; source/street differences remain queued.
- [x] Tall native industry review crops retain complete geometry and explicit tile-origin sidecars. Both final refinery backends pass456 mesh views,1,352 industry views and exact4,096,000-pixel atlas/picking checks.
- [x] Increasing synchronous Vulkan uploads retire obsolete oversized arena pages after their fence/descriptor reset. Eight changed transient payloads preserve exact colour/picking, address reuse and immutable-cache size; completed upload storage retains46,149,632bytes in two pages. Complete1,169 native matrices pass; the larger Linux/nativeCI workload still exceeds6GiB.
- [x] Both complete1,169 native matrices pass28,056 mesh views,322,048 vehicle poses/592 bindings,10,880 collector/384 rotor poses and exact world-atlas/picking below6GiB. The larger Linux/nativeCI workload still crosses the guard; its failures are retained and under investigation.
- [x] Fizzy-drinks wagon52 receives actual bubble-fed factory output, loads25/25, delivers to an accepting town and returns; hiddenGL/Vulkan full/empty captures select bindings7/6 below6GiB. Five additional conventional/electric/monorail/maglev/Toyland freight fixtures observe bridge/tunnel traversal in both loaded and empty states.
- [ ] Complete actual slope/curve wheel contact and contextual bridge/platform/depot/Cab clearances. The former64-body/91-case flat tunnel-gauge defect is repaired above; all-body binding and matrix coverage still do not establish accepted Pass1 source fidelity.
- [x] All81 wagon definitions now have voxel bindings:61 new volumes cover30 ordinary/Arctic/tropical and24 Toyland definitions. Empty beds, loaded heaps/logs/coils/rolls, raised canopies, open bubble/tank frames, rail-gauge contact and climate-specific artwork are preserved. NativeGL/Vulkan each pass68,544 new wagon poses; all69 new engine/climate combinations are captured in twelve operating-consist saves. Public NoAI coal loading/delivery/return and actual full/empty renderer selection pass. Complete cargo, clearance and source fidelity remain open.
- [x] Seventeen new aircraft bodies plus the existing Dinger100 bind33 ordinary fixed-wing definitions. Both native backends pass432 model views/35,904 company-crash-cargo-heading poses and exact atlas checks; all33 aircraft service destinations and pass live capture. Source comparisons retain shape/shading discrepancies.
- [x] Five Toyland planes, three helicopters and four original rotor states complete41/41 aircraft body bindings. Each helicopter passes128 joined poses, actual airport ground contact, all four rotor states and stopped-to-running transitions in held-service fixtures. One-unit aircraft ground-anchor offset and disconnected struts are repaired. Full source fidelity and airport/Cab clearance remain open.
- [x] Full41-engine GL and Vulkan matrices pass44,608 body/384 joined-rotor poses,720 model views and exact world-atlas checks below6GiB; the1,031 GL matrix peaks3.61GiB. Close airport60fps averages still include long presentation intervals and do not establish general smooth performance.
- [x] Final tropical houses84…90 pass36 actual cases; corrected Toyland91…109 pass96 actual cases,52-volume exact mesh/ground/join checks and shop/cafe palette animation. All-house source-fidelity review remains open.
- [x] New105 temperate,112 Arctic/snow and98 tropical tree states pass connected-root checks and focused nativeGL exact mesh checks. The1,002 Vulkan tree matrix passes24,528 lifecycle/palette/scale views and20,832 distant views. Source review identifies remaining crown/fork/proportion/palette defects; complete live-state coverage remains open.
- [x] Full1,002-volume nativeVulkan andGL matrices complete after retiring diagnostic references:24,048 model views,165,376 vehicle poses,24,528 lifecycle/20,832 distant tree views and exact world-atlas/picking/camera checks. Peaks4.38/4.52GiB under6GiB; changing transient payloads preserve address-reuse correctness without persistent-cache growth.
- [ ] Complete production validation/memory/performance remain pending. A600-frame generated-world wideGL run averages30.764fps under concurrent tooling load; the pre-pool binary control fails zoom framing. CI36217303691 passes macOS/Windows builds/tests and187 Linux tests after the macro repair. Linux software rendering passes24,456 mesh/200,192 vehicle poses before the one-hour timeout; independent GL/Vulkan jobs now retain every check with two-hour per-matrix bounds. Current full Linux/core/sync, all-day bounds and Windows runtime remain unproven.
- [x] Twenty-one office/tower volumes70…77 retain real balconies, different low/full-height frame rules, original recolours/snow, joined gold-office slots/roof well/gardens and all48 actual state/recolour cases. Tall joined crops now preserve complete geometry/tile origins; the older hotel images remain exact. Tropical70 source equality/actual capture also pass.
- [x] Seventeen tropical volumes78…83 preserve distinct houses/thatched cottage, four hut/palm plans, open frames, body-owned gardens/paving, late upper storey and church arcades/finials. Source review fixes coplanar floor flicker, dark-room/roof/site-wall placement and overlarge paving. All36 actual cases pass, with ordinary small towns supplying missing states; finer source fidelity remains WIP.
- [x] Sixteen small-house/corner-shop/joined-hotel volumes62…69 preserve individual snow/ground ownership, cross-gables/porch, chamfered entrances/canopies, full two-tile hotel seams and lower south pavilion. Source review corrects roof axes/length, site heights, hidden foreground and detached glazing; all32 small-house/shop state/recolour cases and16 hotel states are captured. Fine source/ground/paint fidelity remains WIP.
- [x] Twelve cabin and ten shop/church volumes56…61 retain two cabin plans/late snow/bare paths, source-owned ground construction, missing first bodies, open shop frame/exposed loft, hollow church roof and late glazing/annex roof. Registered review corrects ridge proportions/annex side and source snow ramps; all distinct family/stages have actual captures, two cabin cases via source-identicalvariant1. The new ordinary1950 small-town map also closes the older37/38 exact-state gaps. Fine source/ground fidelity stays WIP.
- [x] Twenty-one cottage/glass-office/ribbed/setback volumes48…55 retain individual snow timing, real construction/roof voids, porch/antenna/wings, source recolours and full grounds. All32 actual states/32 mature recolours pass, with1930 supplying three absent1950 cottage cases. Tropical50/54 source equality and actual captures pass; finer fidelity stays WIP.
- [x] Ten Arctic44…47 volumes retain distinct two-storey flats/low houses, source-identical early construction, completed-only snow/paving, real dormers/open rafters/door recesses and rear stacks. Source frontage/yard orientation is corrected; all sixteen actual cases and native/Linux checks pass. Fine artwork and ground registration remain WIP.
- [x] Twelve mall40…43 volumes preserve joined L-shaped roof/foundation edges, full four-tile footprint, recessed entrances and original ground-owned/empty states. Actual primary0/1/2/3 and ground-only43 captures,288 mesh/32 joined views and connectivity/edge regressions pass. Roof proportions, source registration and paint remain WIP.
- [x] Twelve suspended-office/Arctic house and ground volumes preserve bare masts, supported glass/cables, distinct villa/narrow plans, source recolours/snow and original empty states. Source orientation/roof/crop issues are corrected; remaining exact live combinations and fine fidelity stay recorded.
- [x] All nine Toyland tree families1947…2003 now have63 explicit lifecycle volumes. Real bites, lowering canopies, changing collars, open/stripped umbrellas, spotted/dry caps and added/lost tiers are tested; all63 actual states are captured. Their severe wide-view rendering cost remains unresolved.
- [x] Cinema39 has its original identical1/2/3 body, blank0, independent pavement and241…244 lamp phases; all actual stages and native/Linux observations pass.
- [x] Classic's world buoy uses the actual canal-resolved source. Separate ordinary red/open and Toyland solid green/orange/red bodies preserve a real99/180-pixel source difference.239/240 lamps,250…254 foam and original water remain. Public waypoint navigation, native/Linux observations and stock15.3 reload pass their scopes.
- [ ] Complete all-voxel recreation and production-level visual consistency; every existing/missing world asset and state is required. See `VOXEL_REVIEW.md`.
- [x] Houses28…31 add twelve distinct tall-office/shop/gold-office/theatre volumes, preserving open construction, absent bodies, original recolours and animated marquee lamps. Source footprint/height/facade/dormer corrections, all actual family states and full native/Linux377-volume matrices pass:36 house IDs/504 body bindings/148 ground cases. Fine art and source-ground registration remain WIP.
- [x] Closed wagons add32 volumes/27 original definitions with explicit climate artwork and source-identical cargo aliases. Twelve ordinary consists complete journeys; all69 engine/climate cases are captured. Attached-part focus, rail-gauge contact, axial body overlap and native GL rounding defects are corrected. Full409 native/Linux/core/sync passes9,816 model views and165,376 vehicle poses/304 bindings, including stock15.3 tropical-maglev reload. Source fidelity and full clearances remain WIP.
- [x] Olive-column tree1597 adds seven connected growing/drying/bare volumes, grey forks and olive foliage. Source/street passes refine heights/widths, expose branches and repair a detached late leaf cluster; all actual stages and final native/Linux168 mesh/1,344 voxel-tree views pass. Current416 volumes/8 tree families; fine source art and54 remaining tree families stay open.
- [x] Eight Toyland cargo families add sixteen real empty/loaded volumes for24 engines, bringing original road bindings to88/88 (102/256 vehicles,365 volumes). Source passes shorten the shared nose, open the cola shell and correct dominant colours; all engines are captured. Full native/Linux8,760 model/114,240 vehicle views plus focused final cola checks pass. Public sugar/cola production, delivery, full-empty saves, depot traversal and stock sugar reload are verified; other cargo services, source proportions and final fidelity remain WIP.
- [x] Eighteen Arctic/tropical road definitions add thirty-three food/paper/copper/water/fruit/rubber volumes, including explicit food rear-panel climate overrides and genuine open/loaded states. All21 actual climate/engine captures, stock15.3 tropical round-trip and full native/Linux8,376 model views/88,128 vehicle poses pass. Current349 volumes/78 vehicle bindings (64/88 road); source dimensions, real cargo services, clearances and final fidelity remain WIP.
- [x] Fourteen open-cargo road definitions add twenty-eight empty/loaded coal/grain/timber/ore/steel volumes, with connected real loads, company straps and upright hollow coils. All engines are captured; later coal trucks have actual production/delivery/full-empty/depot evidence and stock15.3 round-trip. Current316 volumes/60 vehicle bindings, with7,584 model and65,280 vehicle views passing native/Linux/core/sync. Directional dimensions, remaining cargo services and final fidelity stay WIP.
- [x] House26's four suburban layouts and house27's two flat families add eighteen volumes, preserving ground-owned construction, empty bodies, actual site/shell/completed states and original aliases. Source passes correct orientation, five-storey facades, plan/roof/wall heights and palettes. All actual variant/family states and full native6,912-view plus Linux targeted checks pass. Current288 volumes/32 houses/448 body bindings/140 ground cases; fine art, gardens and registration remain WIP.
- [x] Old-house24's four distinct variants and cottage25 add five volumes, retaining finished first bodies versus the genuinely empty cottage first state. Identical bare soil is shared; original mature gardens stay separately selected. Source palette/height/contact corrections, actual variants/stages and native/Linux checks pass. Current270 volumes,30 houses/420 body bindings/136 ground cases; fine art, garden geometry and source registration remain WIP.
- [x] All six dock sections have twelve ordinary/Toyland voxel volumes, original shore/water separation, level joined decks, supported piles/railings and source lamp/foam cycles. Source review trims buried bank piles and corrects lamp placement. Native/Linux288 mesh/512 joined cases, all actual sections/climates, held mooring views and stock15.3 round-trip pass their scopes. Current265 volumes; ground-raster/fine fidelity and complete clearance remain WIP.
- [x] Both ship-depot orientations now have four connected voxel sections and independent original water. Full footprints, open entrances, joined roofs and all-six-ship swept clearance pass;256 joined company/picking/water-ownership views and actual native service traversals pass. Linux misses an instantaneous visit but passes a new normal held-stop/restart fixture after stock15.3 round-trip. Current253 volumes; source96×63 bounds match, finer roof/paint and one-pixel registration remain WIP.
- [x] Six ship families bind all11 original ship definitions204…214, with explicitly authored flared hulls, open holds, supported cabins/derricks/captains/fan hardware and source-permitted cargo aliases. Public-NoAI ordinary/Toyland fleets move and visit both docks; stock15.3 re-save/current Linux reload passes. Current249 volumes/46 vehicle definitions. Source dimensions, waterway clearances, actual cargo/effects and final approval remain open; ship-depot billboard geometry is next.
- [x] Both original four-tile stadium families add eight stand/eight permanent pitch volumes. Ground-only first stages, original source/custom fallback, full footprints/field-line joins, opaque floor picking and227…231/241…244 crowd/scoreboard cycles are retained. Actual stages/climates, native/Linux exact rendering and stock15.3 round-trip pass. Current243 volumes,28/110 houses and8 house grounds; fine source/ground fidelity and final approval remain open.
- [x] Houses15…19 add fifteen source-specific construction/completed volumes: stucco shops, recolourable mansard offices, twin-core modular office, warehouse/ramp and rooflight office. Original early-state differences, grounded contacts and open construction have regressions; all actual stages observed in ordinary1950/1990 worlds. Current227 volumes,20/110 houses and296 bindings;5,448 model views pass. Fine geometry/materials, source-ground raster phase and all final approvals remain open.
- [x] Breadth-first Pass 1 strategy recorded in `VOXEL_PASSES.md`. Four bus and eighteen closed-cargo road bodies bind31 additional engine definitions; public-NoAI moving fleets, stock15.3 round-trip and Linux reload pass. Current35/256 vehicle definitions; source dimensions, actual cargo/clearance and final fidelity remain open.
- [x] Rail/electric/mono/maglev depots add twelve directional bodies, four full-tile weather floors and independent wire; open lanes, original source relocation, running voxel rails and invisible-floor ownership checked. Current5/6 families; tram, all-context clearance and final source approval remain.
- [x] Both cactus and both reviewed tropical palm families add28 connected lifecycle volumes. Source sizing, grounded roots, distinct palettes/white feet, dying structures and all actual states reviewed. Current7/62 tree families and212 total volumes;14 cactus native bounds agree, remaining palm one-pixel bounds/fine art stay WIP. Complete catalogue-wide Pass 1 remains unfinished.
- [x] Editable authored voxel operations, palette-only materials, shared meshes, hidden-face removal and crack-free merged boundaries; first mature house bindings 1, 2 and 3.
- [x] Compact triangulation preserves physical edge samples; eight volumes use 62,564 rather than 70,468 triangles. Old/new galleries match 41,574,400 RGBA pixels, including street and neighbour views.
- [x] Two hollow voxel hangars, L-shaped terminal and two control-tower variants bound to airport tiles 20/22/24/43/47; real commuter/country-airport fixture, source-guided later passes and four-sided orbit/street/category-context reviews. Eight total volume models pass 192 palette/view/reference checks.
- [x] All source frames of the five vanilla animated airport definitions: twelve-frame radar variants 31/51/52 and four-frame flags 39/73. Each variant completes an observed live cycle in public-NoAI fixtures; the expanded 36-volume catalogue passes 864 strict rendering comparisons.
- [x] Reusable authored components, bounded baked rotations and explicit per-model detail grids; radar lattice openings refined through repeated orbit/street review. Whole-sequence sprite provenance preserves custom replacements.
- [x] First construction-state volumes for houses 1/2/3: foundations, unfinished masonry and roofing; stage 2 reuses the completed source-matching binding. All twelve house/state bindings exist; 42 total catalogue volumes pass 1,008 strict GPU views.
- [x] Read-only construction lookup finds actual generated-world stages. Scripted zoom is ordered with queued focus/diagnostics; strict requested-zoom checks pass after the ordering correction.
- [x] Steel/brick tall offices, large/snow offices and hip/gable townhouses with separate construction volumes, recessed/window/interior shading, roof grit and baked shadows. Office checkpoint:57 volumes, seven house IDs and112 source-aware bindings; all remain WIP.
- [x] Independent office lift cabin follows the original position; 37 poses /148 views and eight observed live positions pass. Renderer preserves lift state, tile ownership, source provenance and original recolouring.
- [x] Voxel vehicle palette matrix expanded to all16 company colours plus the original crash recolour:1,088 poses compare exact colours against directly mapped upstream table entries, bypassing palette strips/atlas sampling. Cargo bindings, continuous rotation and IDs agree on native Vulkan/Linux GL; actual crash/loading sequences and final fidelity remain open.
- [x] Two-tile hotel7/8, site/shell/completed volumes, actual room openings, roof pavilion/pool/loungers and source framing/shadows. All four stages have actual live captures; occupancy seam regression and32 joined colour/picking views pass. Joined layouts and neighbouring offices have dedicated orbit/street galleries.
- [x] Statue9 and fountain10 with original blank early stages retained. Repeated isolated/street/context/live passes refine the sculpture, basin and fine jet. Hotel/fountain materials use original animated water palette entries; emitted-material observers see five actual colour phases. Civic checkpoint:65 volumes,11 house IDs,160 nonempty bindings,1,560 strict model views and zero final approvals.
- [x] Pond and autumn parks11/12 with voxel lawns, paths, crowns/trunks and baked shadows; original blank stage0 retained. Ellipsoid authoring and material-masked grain preserve curved boundaries. Source/orbit/street/office-neighbour/live passes correct leaf striping and pond/path layout. Park checkpoint:67 volumes,13 house IDs,184 nonempty bindings and1,608 strict model views; no final approvals or standalone-tree voxel coverage.
- [x] Compact office13 with three storeys, source cornice/roof grain, site and open-room shell; later source passes correct glazing proportions and blue-grey cornice colours. Actual brick/white/red/brown variants and construction states captured. Office checkpoint:70 volumes,14 house IDs,200 nonempty bindings and1,680 strict model views; all remain WIP.
- [x] Airport terminal blocks19/23 and round concourse21, source company colours, supports, roof equipment and painted shadows; corrected roof-post scale and chamfer striping. Targeted actual airport-type captures, isolated/street/neighbour and native/Linux checks pass. Terminal checkpoint:73 volumes,13 airport definitions and1,752 strict model views.
- [x] Pier layouts25…28 and radio tower32: raised passages, open lattice, quarter-grid guy wires and original alternating beacon entries239/240. Connected-line authoring and actual palette-index extraction regressions pass. Corrected beacon/water observations supersede earlier shifted-index diagnostics. Current catalogue:78 volumes,18 airport definitions,14 house IDs and1,872 strict model views; zero final approvals.
- [x] First voxel vehicle238/Dinger100 with original company palettes, continuous heading and identical-source empty/loaded bindings. Source-guided wing/pod/gear/highlight refinements,1,896 model views,192 vehicle pose checks, four actual stand views and a6,000-frame operating-aircraft Cab run pass their scoped checks. Current catalogue79 volumes; live loaded/crashed states, precise fidelity and sustained smoothness remain open.
- [x] Shared voxel SH30/SH40 body for engines23/24, source palette/roof/window/running-gear detail and open diamond pantographs. Public-NoAI selected-engine/held-terminus fixtures, actual captures of both engines, stock15.3 round-trip, source/street passes and6,000-frame Cab checks pass. Current101 volumes/2,424 model views and3,264 vehicle palette poses; exact directional fidelity, all clearances/states and sustained smoothness remain open.
- [x] Balogh coal truck123 with separate empty/loaded volumes, original company/grey/coal palettes, six wheels and open tipper. Source/street refinements,4,352 vehicle palette poses and actual0/20–20/20 cargo on one vehicle pass. Public-API cargo snapshots and four-angle paused checks preserve actual amounts; native cargo/Cab6,000-frame runs retain scoped performance evidence.114 total volumes/2,736 general views; directional source fidelity and wider clearance/climate coverage remain open.
- [x] Palette-based voxel running tracks for all four railway systems, shared with tunnel/station/depot/crossing track; material-partition hidden boundaries, slope support and stepped diagonal joins verified.
- [x] Seven authored voxel fence families, terrain-embedded feet, board/gate openings and stepped chain-link wire; all railway layout slots/raised diagonals and orbit/street views included in 828 strict GPU checks. Reproduced coplanar hedge-cap colour conflict fixed; unified gates match partitioned references exactly.
- [x] Authored palette rubble for all 13 common foundation forms, 66 slope/foundation combinations and three detail grids. Soil/contact masks prevent coplanar top caps; diagonal microsteps share a wall light ramp. 1,056 GPU views and real house/road/rail foundation captures pass.
- [ ] Final approval of every voxel model, construction/variant states, all remaining railway details/integration and the remaining airport/world categories.
- [x] Initial authored profiles for 110 house IDs and 62 tree sprite families.
- [x] First standalone voxel tree family1576 with all seven explicit lifecycle volumes, connected roots/branches, original foliage/bark/deep-shadow colours and actual foliage loss. Source-guided scale/grain/crown refinements, street/building-context review and actual captures of every stage pass. Current catalogue86 volumes/2,064 strict model views;168 voxel-tree views and5,460 remaining component-tree views are counted separately. No final approval;61 tree families and later source/LOD/performance work remain.
- [x] Silver-column family1583 with seven states and a distinct short dead form; all seven actual stages captured. Fixed-lens native-scale comparison prompted narrower crowns, occupancy-only colour brushes, branch-revealing gaps and shade refinements in both families. All14 source/model bounds agree in this review view; fine colour/silhouette agreement remains WIP. Current93 volumes/2,232 model views,336 voxel-tree views and60 remaining component families; zero approvals.
- [ ] Drooping-spruce family1590 fidelity review: seven first-pass volumes bring the catalogue to100. Connectivity,2,400 general model views and504 voxel-tree views pass; first refinements improve supports, needle blocks and bare spread. Bough regularity, source detail/bounds, targeted early-stage captures and later context/LOD work remain active.
- [x] Separate bark/foliage or Toyland component charts for all 62 tree families; authored branches, closed palm/leaf volumes, snow materials, seven lifecycle states and three LODs. 5,544 GPU views include every resolved palette binding.
- [x] Initial authored vehicle volume assemblies bound to all 256 vanilla definitions.
- [x] GPU visibility/picking for 7,520 vehicle direction/cargo poses across all climates.
- [x] Renderer-only vehicle position/heading smoothing, directional materials and horizontal shadows/rotors.
- [x] Industry inventory: 175 tile definitions and 700 exported tile/stage reference records.
- [x] First voxel industry tiles2/3: six engine/machinery-house site/frame/completed volumes, source-aware selection, recessed openings, corrugation, shadows and raised piers. Native-scale/street/original-layout passes and64 exact construction views pass. Public-NoAI funded mine provides genuine stages0/1/2/3; stock15.3 round-trip and Linux reload pass. Current107 volumes/2,568 general views; exact source fidelity, other mine members/ground and broader industry coverage remain WIP.
- [x] Winding headgear0/1 adds bare steel, shell and three open-wheel/rope poses. Original-family provenance, connected geometry and128 industry construction/animation views pass. Source-aligned comparison fixes hidden origin/roof-edge errors; all16 mine table records match native bounds/placement, not full pixels. A real NoAI coal route loads20 units, delivers and returns, and native/Linux observe all three actual winding frames.112 volumes/2,688 model views; mine grounds and final fidelity remain open.
- [x] Mine ground0…6 now uses five explicit construction/bare/stockpile volumes. Supported mounds, full playable tile coverage and matching seam height/material tests pass; source palette/street/layout/live passes refine soil and coal.224 ground-layer views, bore-clipping palette regression and real stages0/1/2/3 pass. Source contour/grain/raster precision remains WIP.
- [x] Initial authored profiles for 40 mine, power-station, refinery, offshore, farm, factory, steelworks and sawmill tile definitions.
- [x] Explicit source material crops for curved surfaces; 160 industry views pass GPU visibility/material checks.
- [x] Initial volumetric bridge decks, trusses, supports and flat/sloped heads selected through upstream drawing metadata.
- [x] 832 synthetic bridge assembly views, exact per-component GPU/CPU material comparisons, half-pillar partitioning and transparent picking checks.
- [x] Bridge decks reduced from 2.5 to 0.5 height units, caps buried inside the slab, and clean underside material; 208 overhead GPU checks show no pillar pixels through the deck. A real bus route passes below a minimum-height bridge.
- [x] Actual field-fence and railway-fence lookup/capture markers; source, four-sided street, raised-half-tile and live review tooling.
- [x] Foundation review exports include four orbit/four street views, building/track contexts and independently selected slope/form pairs; all 104 original foundation sprites are exported for source review.
- [x] Fence and foundation palette cells replace the former component texture charts; natural-terrain surfaces still require their own voxel migration.
- [x] Six tunnel portal/interior families, terrain bore clipping, actual hidden tunnel-vehicle rendering and Cab capture hints; 144 GPU views and live bore/state checks.
- [x] Explicit surface/tunnel rails, sleepers and guideways for four vanilla rail systems; 8,240 GPU layout/slope/detail views, reservation materials and instance/reference agreement.
- [x] Far flat straight running sections use fewer longitudinal cells with unchanged gauge, cross-section and head height; diagonals, grades, maglev junctions and close detail retain their fine grid. Subsequent indexing reaches about58 fps in the wide workload; sustained60 remains open.
- [x] Diagonal routes use straight centrelines and face-connected voxel steps, preserving bounded gauge and matching adjoining rail/monorail/maglev endpoints.
- [x] Initial maglev turnout/crossing guide-wall clearances and distance-appropriate fence detail.
- [x] Maglev panel/edge materials and tile-port colour agreement: actual mesh rays reproduce/fix overlapping slab disagreement; corrected compact/reference junction galleries match exactly.
- [x] Initial geometry for all eight vanilla train-station layouts/four rail systems: platforms, furniture, buildings, company paint and paired halls; 128 GPU views and live station capture.
- [x] Initial nine-stage farmland geometry, bound hay stacks, both rock sets and four snow caps; painted detail layers replaced by clean ground, 1,140 GPU views and live hay/partial-snow checks.
- [x] Initial turf blades, small Arctic/tropical stones, five rough-ground layouts and Toyland raised pips; clean substrate materials and terrain/tunnel conformance. Expanded 1,824 ground-detail GPU views pass in each climate.
- [x] Component-only repeating charts and explicit solid materials in JSON assemblies; first individual chimney/roof corrections on industry tiles 8,33,39,43,49, with exact CPU/GPU checks.
- [x] Six signal types with light/semaphore mechanisms and state-aware lamps; contact/messenger wires, droppers, pylons and covered-station hangers. 192 signal cases and 216 catenary views pass.
- [x] Reproducible NoAI electric-rail fixture, with a verified locomotive journey over a bridge, through a tunnel and back from a terminus; no renderer writes to simulation state.
- [x] Optional public-NoAI aircraft fixture verifies actual country-airport service and return to the main airport, retaining rail/bus checks. Ordinary loading orders provide repeatable observation/held-stand views; failed readiness worlds are preserved. Four-angle held-aircraft review and a moving1,800-frame fullscreen Cab run completed; full clearance/vehicle fidelity and smoothness remain open.
- [x] Initial open-bay geometry for six rail/road depot families, with component charts, track ends and interior/roof detail; 96 GPU direction views and real door-clearance checks.
- [x] Road depot family4 is now voxel-based in all four directions, with an independent opaque floor and separate Toyland material variants. Original layered source export, source/street/context passes, actual four-exit public-NoAI fixture and rendered visible/inside/visible truck traversal pass.64 all-company palette views and invisible-floor colour/ownership checks pass. Current128 volumes/3,072 model views; exact fidelity and the other five depot families remain open.
- [x] Four railway crossing systems, warning lamps, tram inlays and state-driven maglev gates; 128 GPU views, clear-roadway checks and an actual live open-to-barred transition.
- [x] Initial bus/truck bay and drive-through stop geometry: shelters, slatted benches, signs, curbs, offices/loading bays and fences; 64 GPU views, lane clearance, company and transparent-picking checks.
- [x] Resolved source-image export and four-orientation GPU model galleries.
- [x] Palette-aware nearest-sampled HighDef/fallback textures, UV bounds and opaque-surface padding.
- [x] House/vehicle/tree inventory distinguishes existing profiles from completed visual review.
- [ ] Complete material-detail and reference-model visual review.
- [ ] Terrain, foundations, water, and vegetation in all climates.
- [ ] All vanilla infrastructure.
- [ ] All vanilla buildings, industries, and animation states.
- [ ] All vanilla vehicles, liveries, cargo states, and effects.
- [ ] NewGRF provenance and placeholders.
- [ ] Complete, validated asset coverage manifest.

## Product identity

- [x] OpenTT3D README, application/window/menu titles, Cab tooltip and menu wordmark.
- [x] Authored SVG application icon, generated PNG/ICO/ICNS assets and SDL icon data.
- [x] `opentt3d` executable name and OpenTT3D bundle/installer/desktop metadata.
- [ ] Native packaged icon/installer checks on every release platform.

## Release gates

- [ ] Matching-version save round trips in both directions.
- [x] One paused vanilla fixture: OpenTT3D -> official OpenTTD 15.3 -> OpenTT3D, including native reload/render.
- [x] Electric-rail fixture re-saved by official 15.3, then reloaded for a moving fullscreen OpenTT3D Cab run with its original AI identity staged.
- [x] Latest vegetation/road-stop save re-saved by official 15.3 and reloaded with renderer, tile-picking and live-bore checks; current toolbar/status regions match stock exactly (254,448 pixels).
- [x] New commuter/country-airport fixture loaded/re-saved by official 15.3 and reloaded with the original AI, 192 voxel comparisons and actual tile-picking checks.
- [x] Normal 1980 large-city construction fixture loaded/re-saved by official15.3, then reloaded with the indexed renderer, actual house4 stage1 capture and tile picking.
- [x] Actual aircraft held-stand fixture re-saved by official15.3 and reloaded on Linux with its staged AI, core/synchronization validation, renderer/picking and aircraft Cab activation.
- [ ] Command replay / simulation-state equivalence.
- [ ] Stock-client / stock-server multiplayer interoperability.
- [ ] UI comparisons and rotated construction interaction checks.
- [ ] Linux x86-64, macOS universal, Windows x86/x64/ARM64 packages.
- [ ] Source and documentation archives, checksums, asset sources and attribution.
- [ ] Native Mac play-through of the packaged release.
- [ ] First complete release published.

## Current development limitations

The 3D renderer is opt-in. World capture now consumes upstream tile and vehicle
drawing decisions, preserving resolved sprite/palette/state choices. It maps
terrain textures onto terrain triangles, and applies the reference artwork to
authored house/tree geometry. Missing volume geometry is displayed as **temporary
reference sprite planes**, logged as incomplete coverage and excluded from the
release gate. These planes are not completed vanilla assets.

The 110/62 profile counts do not establish visual fidelity. All mature tree families
have received an individual gallery/material pass, with authored branch rigs and
separate bark/leaf charts. Crown shapes, material periodicity, all growing/dying
silhouettes and moving LOD transitions still need further review. House construction
states and multi-tile structures remain initial geometry.
Vehicles now have initial volume geometry and direction/cargo bindings, but their
individual silhouettes, running gear, UV layouts and animation/crash states are
not visually approved. Industry/infrastructure geometry, remaining effects and
mod placeholders remain major content work. See [asset review notes](ASSET_REVIEW.md).

Navigation verification exercises the loaded terrain at every camera rotation,
multiple zoom levels and off-centre cursor positions. Broad interactive checks of
construction tools, label selection, secondary windows and cargo overlays remain.
Transparency sorting, foundation/fence detail and junction review, bridge
material/silhouette refinement and general sprite cropping are unfinished.
Foundations, fences, bridges, tunnels and plain railway track now have initial volume
geometry, and train stations now have an initial platform/building/roof pass. Signals
and catenary have state-aware volume geometry and initial live fixture review. Rail/road
depots, crossings and bus/truck stops now have initial component models. Bridge-track
joins, other infrastructure, custom layouts and aqueduct fixtures still need dedicated
work. Station details/transparency ordering, tunnel masonry/material repetition,
rail frogs and switches, and every climate/state require additional visual passes.
Large screenshots are streamed through bounded framebuffer tiles;
whole-map framing and representative giant-world performance still need review.

Frame-level target caching, source-resolution texture LOD, curved-mesh LOD and
terrain/model instancing are implemented. Vulkan avoids interactive full-frame
readback. The bounded atlas uses rectangle packing and relocates recent live texels
without re-decoding every sprite. Capture retries restore sprite-combine state on
exceptions. CPU page storage is reused within the existing 48-page repack peak,
with explicit gutter clearing and repeated colour/ID relocation checks.
Remaining performance work includes long-tail moving-view stalls,
larger maps, additional climates and broad interactive/lifetime coverage.

The current CI definition covers Linux x86-64, macOS arm64 and Windows x86/x64/ARM64
builds. The last full hosted matrix predates the perspective/HighDef work; current
local checks cover macOS ARM64 and Linux ARM64/Mesa. ARM64 Windows is a
cross-compilation check, not a native runtime test.
Release packaging, universal Mac binaries, network compatibility metadata and
multiplayer/replay verification remain release work. Development builds retain
their own network revision identity.

These limitations are **not** the agreed first-release scope. A complete vanilla
asset pack and the compatibility gates above are still required before that release.

See [verification notes](VERIFICATION.md) for commands and the exact extent of testing.
See [performance measurements](PERFORMANCE.md) for the measured bottlenecks and outstanding 60 fps work.

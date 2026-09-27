# Rendering performance work

The release target is smooth **60 fps**, including fullscreen and every exposed
zoom level. This target is **not yet met**.

## Plastic-fountain paired-animation observations

The24-control matrix peaks at3,341,127,376 sampled bytes. Two600-frame live services
average60.016/60.025fps for OpenGL/Vulkan, with4.616/7.440ms p95 work. They retain72/77
intervals over20ms and23.785/22.798ms maximum intervals. Both observe all eight paired
ground/body poses on one unchanged tile. Concurrent package checks, tests and authoring
remain part of the observation environment. These short controls do not establish
sustained arbitrary-world smoothness or long-duration/reload/multiple-viewport memory
acceptance. Source:`breadth-plastic-final-reconciliation.json`.

## Toy-shop supplied-service observations

The26-control matrix peaks at3,396,882,080 sampled bytes. Two600-frame real supplied
factory→shop services average59.994/59.996fps for OpenGL/Vulkan, with4.586/5.197ms p95
work. They retain65/96 intervals over20ms and22.630/22.660ms maximum intervals.
Concurrent authoring remains part of this environment. Sustained arbitrary-world
smoothness and long-duration/reload/multiple-viewport memory acceptance remain open.
Source:`breadth-toy-shop-final-reconciliation.json`.

## Cola-well service observations

The24-control matrix peaks at3,419,262,528 sampled bytes. Two600-frame service runs
average60.001/59.990fps for OpenGL/Vulkan, with4.971/5.357ms p95 work and89/40 intervals
over20ms. Maximum intervals are23.401/22.788ms. Concurrent authoring and package
checks remain part of the observation environment. These short runs verify the
ordinary cargo route, not sustained arbitrary-world smoothness or long-duration
memory acceptance. Source:`breadth-cola-final-reconciliation.json`.

## Battery and harvest-observer regression observations

The28-control matrix peaks at3,240,988,200 sampled bytes. Both9,000-frame battery cycles
average60.003/60.002fps for OpenGL/Vulkan, with4.622/5.169ms p95 work,607/762 intervals
above20ms and23.490/25.571ms maxima. Four9,000-frame timber/cotton regressions also pass
state coverage but retain733/766/916/1,064 intervals above20ms. The longest interval is
71.811ms in cotton Vulkan. Concurrent background authoring and source checks remain
part of this observation environment. These cycles establish actual-state coverage;
isolated sustained arbitrary-world smoothness and long-duration memory remain open.
Source:`breadth-battery-final-reconciliation.json`.

## Sweet-factory service observations

The24-control narrow-hall checkpoint peaks at3,290,664,440 sampled bytes. Two600-frame
cotton-delivery route observations average59.977/60.008fps for OpenGL/Vulkan, with
3.658/5.260ms p95 work. They retain60/34 intervals above20ms and23.811/22.563ms maximum
intervals. Concurrent authoring/package checks and these short observations do not
establish isolated sustained smoothness. Full arbitrary-world performance and
long-duration memory acceptance remain open. Source:`breadth-sweets-accepted-reconciliation.json`.

## Cotton-candy harvest/regrowth observations

The24-control revised-paint matrix peaks at3,260,468,704 sampled bytes. Both9,000-frame
cotton cycles average60.003fps for OpenGL/Vulkan, with4.847/5.282ms p95 work. They still
contain838/681 intervals above20ms,20.898/20.506ms p95 intervals and46.084/81.474ms maxima.
These150-second background observations establish original-state cycle coverage but
retain visible scheduling outliers. Isolated sustained arbitrary-world throughput and
long-duration/reload/multiple-viewport memory acceptance remain open. Earlier first-matrix
and timber-regression timings remain retained. Source:`breadth-cotton-reviewed-reconciliation.json`.

## Diamond mine observations

The24-control upright-hoist matrix peaks at3,229,666,784 sampled bytes. Two600-frame
ordinary diamond-service captures average60.010/60.001fps for OpenGL/Vulkan, with
5.206/5.562ms p95 work. They retain44/92 intervals over20ms and maxima22.939/23.495ms.
These short route observations do not establish sustained arbitrary-world smoothness
or long-duration/reload/multiple-viewport memory acceptance. Evidence:
`breadth-diamond-upright-reconciliation.json`. The preceding leaning-hoist revision's
separate measurements remain with its rejected visual review.

## Software OpenGL clipping correction

Five frozen software/hardware OpenGL/Vulkan correctness controls peak at3,010,547,072
sampled bytes. A three-frame640×480 package observation reports1.578fps in Apple's
CPU OpenGL driver,63.519fps on hardware OpenGL and66.001fps in Vulkan. These short
startup samples establish successful rendering and regression coverage, not sustained
throughput. The wider software landscape also completes its coverage/picking capture.
The homogeneous clip stage is enabled for Apple Software Renderer; full arbitrary-
world60fps and long-duration memory acceptance remain open.

## Arctic/tropical bank observations

The28-control bank matrix peaks at3,464,744,392 sampled bytes. The two600-frame gold
service observations average60.003/60.004fps with5.044/6.461ms p95 work, but retain70/85
intervals above20ms. Concurrent correctness fixtures and separate software-renderer
diagnostics make this a bounded correctness checkpoint, not isolated throughput
acceptance. Source:`breadth-bank2-final-reconciliation.json`.

## Elevated heliport observations

The20 heliport controls peak at2,882,800,808 sampled bytes. Four6,000-frame original
rotor observations average59.576…60.003fps, with5.085…5.510ms p95 work. They still
contain482…796 intervals above20ms and a151.72ms maximum work sample. Ordinary headless
fixture preparation overlaps part of this correctness review; these figures are not
an isolated performance acceptance run. Source:`breadth-heliport-final-reconciliation.json`.

## Hosted release .6 acceptance

The900-frame Linux llvmpipe electric journey passes complete support and collector
observation at1.704fps,941.46ms p95 work and1,014.62ms maximum work. Peak sampled memory
is2,185,838,592bytes. This closes the missed portal-state observation in`.5`; software
rendering is correctness evidence, not desktop-GPU throughput. Both hosted Mac startup
paths now finish, though ARM's software-OpenGL screenshot has unresolved triangular
regions. The tiny three-frame package benchmarks do not measure sustained performance.

## Airport surface observations

The20 airport-surface controls peak at2,928,839,896 sampled bytes. City-animation
OpenGL/Vulkan runs of3,600 frames average60.003/60.000fps with6.152/6.009ms p95 work,
but retain303/251 frame intervals above20ms. The two1,800-frame intercontinental
controls retain164/179 such intervals and a41.03ms maximum Vulkan work sample.
These bounded background observations do not establish smooth arbitrary-world60fps.
Evidence:`build-macos/breadth-airport-edge-final-reconciliation.json`.

## Gold checkpoint observations

Two18,000-frame background gold controls capture the complete original wheel cycle.
OpenGL/Vulkan average60.003/60.002fps, with5.312/6.395ms p95 work and34.74/27.21ms
maximum work. They retain1,558/1,612 frame intervals above20ms and21.064/20.942ms p95
intervals, despite the60fps averages. These300-second runs do not establish smooth
arbitrary-world performance. The24-control matrix peaks at3,411,643,800 sampled bytes.
Evidence:`build-macos/breadth-gold-extended-animation-*` and
`breadth-gold-final-reconciliation.json`.

Hosted`.5`Linux software rendering averages1.01fps in the120-frame electric control.
The original collector exception does not recur, but sparse presentation misses the
intermediate portal state; complete Linux acceptance remains open. Apple-silicon
OpenGL package startup times out while actively executing Apple's software rasterizer;
the default Vulkan package succeeds. Neither result establishes desktop-GPU throughput.

## Collector timing repair controls

The formerly capped analytic vehicle/Cab smoothing now receives full elapsed
presentation time. An injected3,000ms delay reproduces the collector failure before
the change and passes afterward on both backends; those intentionally delayed runs
are correctness evidence only. The injection is removed from the clean build.

Two9,000-frame clean electric-route controls average59.957fps (OpenGL) and59.761fps
(Vulkan), with8.343/8.803ms p95 frame work. They retain52/62 intervals over20ms and
81.78/271.73ms maximum work. These bounded runs do not establish sustained
arbitrary-world60fps. The10-control reconciliation peaks at3,169,832,296 sampled
bytes. Evidence:`build-macos/breadth-collector-repair-reconciliation.json`.

## Copper checkpoint animation controls

Both background6,000-frame copper scenes capture all three original hoist-wheel
poses without altering animation state. OpenGL averages59.887fps with5.542ms p95 work;
Vulkan averages59.946fps with5.526ms p95 work. Their26/17 frame intervals over20ms and
121.28/125.82ms maximum work remain visible limitations. These bounded observations
do not establish sustained arbitrary-world60fps. The24-run matrix peaks at
3,060,075,880 sampled bytes. Evidence:`build-macos/breadth-copper-final-animation-*`.

Iron-ore Linux CI repeats the collector exception during the electric journey after
passing the full scene matrix. Its requested local contact6.1552124 falls below the
roof mount6.625; the original crash save is retained and a paused native replay passes.
The Linux sampler's secondary process-exit race is repaired, but the collector cause
and the elapsed-time hypothesis remain unresolved. The failed journey's sampled peak
is2,177,904,640bytes, below its6GiB guard; no completed journey performance is claimed.

## Iron-ore checkpoint electric-route controls

Both background9,000-frame replays of the actual factory`.16`CI fixture pass
engine26's support and collector observations after the diagnostic rebuild. OpenGL
averages59.930fps with9.744ms p95 work; Vulkan averages59.813fps with10.639ms p95 work.
They still have94/109 frame intervals over20ms and119.26/165.50ms maximum work.
These are successful bounded gameplay controls, not sustained arbitrary-world60fps
acceptance. The24-run ore matrix peaks at3,257,437,472 sampled bytes.

Paused/normal replays and injected350/1,500ms local capture delays also fail to
reproduce the earlier Linux collector exception. The delays are removed from the
published implementation; numerical collector pose inputs are retained in errors.
The elapsed-time-clamp hypothesis remains unproven. Evidence:
`build-macos/breadth-ore-final-collector-*` and `breadth-collector-local-reproduction-audit.json`.

## Automatic model LODs and restored projected trees (September26 follow-up)

The user's new priority permits generated distance LODs and requires restoring the
previous projected-material3D trees if voxel-tree performance remains poor. Four
coarse levels are now generated lazily from the authored cell volumes at factors
2/4/8/16. Occupied blocks survive, majority materials retain palette indices, ties
are deterministic, and outer bounds/ground-contact extrema remain registered.
Nearest-bound projected size keeps close geometry at full detail. Generated meshes
share the1GiB scene-pinned CPU cache and the immutable GPU cache; no separate LOD
artwork is authored. `OPENTT3D_AUTO_LOD=0` selects the original full-detail control.

Matched300-frame title-world tunnel-Cab controls, before the terrain-height change,
use identical frozen executable/artwork/save/camera and disable tunnel scenery culling:

| Geometry | GL fps | Vulkan fps | Vertices/frame | GL/Vulkan p95 work ms |
| --- | ---: | ---: | ---: | ---: |
| Full voxel models/trees | 12.081 | 13.242 | 664,706,778 | 85.970 /79.308 |
| Automatic voxel LODs | 22.714 | 29.499 | 280,773,969 | 47.164 /35.852 |
| Automatic LODs + projected3D trees | 54.891 | 60.017 | 51,668,286 | 20.928 /13.768 |

All six checks pass below6GiB; the maximum sampled footprint is3,338,046,824bytes.
Voxel LODs alone still miss every20ms interval. The projected-tree samples have25/2
intervals over20ms onGL/Vulkan, so their improved averages are not arbitrary-world
smooth60fps proof. Projected3D trees are the default; `OPENTT3D_TREE_STYLE=voxel`
retains the old tree path for controlled diagnostics. The new terrain configuration
has its own subsequent controls rather than being substituted into this comparison.

Evidence: `build-macos/pass2-auto-lod-{validation,performance,hashes}.json` and
`pass2-auto-lod-build/`. Native tests cover thin features, anisotropic/odd-sized grids,
palette preservation, deterministic reduction and exact reconstruction after eviction.

### Doubled-terrain control

The separately frozen `pass2-terrain-docks-build/` repeats the same six300-frame
comparisons with the raised terrain:

| Geometry | GL fps | Vulkan fps | Vertices/frame | GL/Vulkan p95 work ms |
| --- | ---: | ---: | ---: | ---: |
| Full voxel models/trees | 10.133 | 10.771 | 817,034,766 | 104.187 /96.522 |
| Automatic voxel LODs | 22.035 | 28.627 | 286,592,502 | 48.407 /38.297 |
| Automatic LODs + projected3D trees | 48.872 | 60.004 | 56,218,083 | 22.462 /15.368 |

All six pass their6GiB/picking guards; maximum3,411,152,184bytes. Projected-tree
intervals over20ms are42/0. Evidence:`pass2-final-{validation,performance,reconciliation}.json`.
The two separate9,000-frame moving-route attempts fail early on the old maximum
train-grade constraint; they are retained as failures and supply no route performance
claim. The corrected-contact candidate has its own subsequent route verification.

### Published geometry candidate

After the tree-root, terrain-culling and tunnel-bank corrections, the final frozen
`pass2-publish-build/` repeats all six matched300-frame controls:

| Geometry | GL fps | Vulkan fps | Vertices/frame | GL/Vulkan p95 work ms |
| --- | ---: | ---: | ---: | ---: |
| Full voxel models/trees | 10.211 | 10.842 | 812,811,498 | 101.733 /96.440 |
| Automatic voxel LODs | 21.738 | 28.698 | 286,443,852 | 49.194 /37.648 |
| Automatic LODs + projected3D trees | 49.477 | 60.000 | 56,185,929 | 21.686 /13.689 |

All pass the6GiB/picking guards; the maximum sampled footprint is3,408,743,760bytes.
Projected-tree intervals over20ms are154/0. The changed interval distributions across
the retained short samples reinforce that average fps alone is insufficient.
Evidence:`pass2-publish-{hashes,validation,reconciliation,performance}.json`.

The corrected electric23 routes complete9,000 frames/backend with all support/corner/
collector observations and2,702,855,336/2,623,507,456-byte peaks. Their59.558/59.961fps
averages include147/1,100 intervals over20ms. These moving runs are correctness and
bounded-duration memory evidence; no matched moving off-control establishes a speedup.

## Opt-in tunnel-tree occlusion: exact native comparisons (September26)

`OPENTT3D_TUNNEL_SCENERY_CULL=1` retains trees intersecting the whole bore or either
infinite enlarged mouth cone. It applies only inside original opaque tunnel pairs,
away from lining boundaries; all other scene capture retains its normal frustum.
Conservative plane/AABB rejection keeps overhanging volumes and has no draw-distance
limit. The option is disabled by default.

Matched1,247-volume90-frame paused title-world Cab controls:

| Backend | Full fps | Culled fps | Full p95 work ms | Culled p95 work ms |
| --- | ---: | ---: | ---: | ---: |
| OpenGL | 11.400 | 38.107 | 93.665 | 28.229 |
| Vulkan | 12.735 | 40.331 | 83.399 | 26.325 |

Submitted vertices fall664,706,778→197,335,923/frame, entirely from hidden trees.
Mean buffer wait falls66.237→13.311msGL and62.851→13.595msVulkan. All16 paired
screenshots/reference images retain identical RGBA. A further20 same-process
mouth/interior/exit/four-heading/tiltedCab views/backend preserve4,608,000 exact
RGBA/picking pixels and unchanged vehicle state; peak3,636,104,768bytes. Unit tests
exercise every tunnel kind/direction, large origins, crossing boxes and unlimited
far-mouth visibility. Broader actual tunnel/climate/world evidence remains open.
Every measured interval still exceeds20ms; this is not smooth60fps.

Evidence: `build-macos/pass1-tunnel-scenery-validation.json`,
`pass1-tunnel-scenery-exact-performance.json`, `pass1-tunnel-scenery-exact-validation.json`
and their frozen binary/artwork/source hashes. Earlier baselines/failures remain.

The follow-up route matrix passes all ten conventional/electric/monorail/maglev/
Toyland backend cases and both18,000-frame moving-Cab checks. Across the12 runs,
240 tunnel comparison views preserve55,296,000 exact RGBA/picking pixels; peak
sampled memory is2,962,001,184bytes. Moving-Cab rates are57.588fpsGL/59.898fpsVulkan,
with p95 work19.965/9.323ms and892/1,739 frame intervals over20ms. GL's maximum work
is1,067.529ms, so these functional passes do not establish smooth production60fps.
These route timings have no matched off-control and do not establish a speedup.
Evidence: `pass1-tunnel-scenery-route2-{validation,reconciliation}.json`. The initial
paused fixture's failed underground-Cab lookup remains retained separately.

## Linux residency follow-up (September26)

Release`.9`/`d27740297` completes LinuxGL, macOS and all three Windows jobs. Its
LinuxVulkan renderer matrix reaches the unchanged7200-second bound before the
expanded vehicle checks finish. The retained artifact reports4,148,486,144bytes
peak over28,702 samples and no6GiB breach. It completes28,320 authored views,
all pitched train bindings and the243,629-pixel live-tunnel clearance check, but
remains an incomplete/failed full run. Evidence is in
`build-macos/pass1-release9-linux-vulkan-artifact/`; previous memory failures remain.
The subsequent`6539128b4`CI likewise passes LinuxGL/macOS/all Windows builds and
reaches the Vulkan matrix bound without a memory breach:4,164,407,296bytes over
28,707 samples. Its complete artifact is `pass1-public-fixtures-linux-vulkan-artifact/`.

The follow-up keeps the full OpenGL job and separates Vulkan's scene matrix from
four complete vehicle-engine shards0…63/64…127/128…191/192…255. Each job keeps its
7200-second renderer bound,180-minute job bound and6GiB sampled memory guard;
at most three Linux jobs run concurrently. The default local renderer check still
includes every vehicle pose. Sharding addresses diagnostic wall time, not runtime
frame performance, and remote success still requires all five Vulkan jobs.

The new88-run industry construction sweep peaks2,704,411,720bytes; eight electric
corner-route/contact runs peak2,816,019,552bytes. Those fixture-scoped functional
results do not establish smooth dense-Cab performance or all-day interactive limits.
Their9,000-frame averages are49.997…50.085fpsGL and54.006…54.150fpsVulkan, with
3,488…4,140 versus31…41 intervals over20ms. P95 draw-deadline lateness remains
99.001…99.269msGL and97.440…97.668msVulkan. The full per-run performance summary
is `build-macos/pass1-pitch-corner-performance-summary.json`.

## Scene-pinned residency: matched expanded controls pass (September26)

`pass1-cpu-residency-control-validation.json` now records both complete expanded
1,169-volume controls, using the same title save, original full geometry and
7,200-second/6GiB bounds as the preceding failures:

| Backend | Sampled peak bytes | Samples | Result |
| --- | ---: | ---: | --- |
| OpenGL | 5,779,248,360 | 6,395 | Pass |
| Vulkan | 5,359,801,360 | 6,696 | Pass |

Both pass28,056 authored model views,322,048 vehicle poses/592 declared climate/cargo
bindings, pitched support-plane and collector poses,24,528 tree lifecycle views,
the additional rail/bridge/tunnel/foundation/infrastructure checks, forced CPU/GPU
cache retirement/reconstruction and exact4,096,000-pixel world-atlas/picking comparisons.
The CPU surface cache retains immutable vector identities and lossless source runs;
scene copies and asynchronous visibility jobs pin their streams. Its1GiB soft
budget and the512MiB GPU soft budget retain active/in-flight geometry even when
that geometry exceeds a budget. The frozen candidate hashes and prior failures remain.

The final30-frame title-world Cab samples average only12.714/14.058fps onGL/Vulkan,
with p95 work82.845/71.844ms and all30 intervals over20ms. OpenGL records zero mesh
uploads during those measured frames and63.489ms average buffer wait. The memory
regression passes this expanded workload; sustained smooth60fps, interactive
camera/reload/multiple-viewport residency, arbitrary-world limits and Linux follow-up
remain open. Focused industry matrices do not replace those larger reviews.

### Preceding retained-source and GPU-residency failures

`pass1-residency-serialized-validation.json` records complete-workload retries with
unchanged7,200s/6GiB bounds. Vulkan crosses the memory guard at6,489,053,088bytes
over6,679 samples after passing28,056 voxel views and322,048 vehicle poses; OpenGL
crosses at6,463,641,888bytes over229 samples. Both are failures, retained alongside
the earlier incomplete runs. GPU-cache retirement alone is insufficient.

The next candidate stores lossless linear source-cell runs and one shared material
palette. Only meshing and exact unit-cell diagnostics reconstruct a dense grid.
The matched1,169 catalogue uses19,733,848 retained run bytes instead of278,132,924
dense cell bytes, excluding the additional eliminated per-model palette copies.
Native194/194 tests pass, including reconstruction after the original grid is
destroyed, holes, six-face materials, anisotropic transforms, long runs crossing
planes and16-bit material IDs. The ongoing fullGL/Vulkan controls use the frozen
1,169 artwork and the same expanded scene/check selection and memory guard.

A liveVulkan `vmmap` sample at12:22UTC reports5.6GiB physical footprint with4.3GiB
allocated in the default malloc zone,537.3MiB graphics mappings and328.7MiB owned
unmapped graphics. The complete catalogue's11,422,202 triangles alone occupy
2,741,328,480bytes of80-byte CPU vertices; procedural cached geometry adds to this.
Run compression is a bounded reduction, not evidence of a complete-world memory
or smooth-frame-time solution. `pass1-compact-source-vulkan-vmmap.txt` retains the
snapshot. The completedGL control still exceeds6GiB at6,536,140,968bytes over6,233
samples after the full model/vehicle checks. Its pairedVulkan control also fails
at6,528,587,800bytes across6,663 samples. Both completed failure records remain in
`pass1-compact-source-control-validation.json`.
The next uncommitted candidate uses a1GiB soft CPU-surface cache, with scene-copy
and asynchronous-visibility leases, stable vector/GPU-cache identities, and exact
reconstruction from retained cells. All196 native tests pass, including copied-scene
retirement/rebuild and active asynchronous-worker leases. Eight focusedGL/Vulkan
farm/paper/plantation/oil-well runs pass forced retirement/rebuild, source selections,
exact within-backend RGBA/picking and atlas comparisons; maximum sampled memory is
2,501,165,056bytes. The matched1,169 expanded controls subsequently pass as recorded
above; interactive memory/pacing review remains pending. The candidate is frozen in
`pass1-cpu-residency-{control,catalogue}-build`.

## Forest/refinery and synchronous upload retirement:1,169 volumes (September26)

Release`.7` LinuxGL CI36233595585 completes its full native/software-renderer matrix
with5,080,174,592 sampled bytes across22,949 samples. The matching expanded Vulkan
job again crosses6GiB at6,442,815,488bytes. The passing GL workload and failing Vulkan
workload have different selected scene/check sets; they are independent backend
evidence, not a matched cross-backend memory comparison.

The uncommitted mesh-residency candidate releases completed cold GPU storage under
a512MiB soft budget. Vulkan protects in-flight pages and invalidates all cached
slices sharing an evicted page; GL uses deferred object deletion. Active geometry
may exceed the budget. Completed CPU voxel surfaces also relinquish their growth
capacity, including procedural railway/fence/foundation variants. Both native
backends pass four exact forced-retirement/reupload views and transient ownership
checks. Complete-workload and interactive review remain in progress.

`pass1-residency-vulkan-ci` runs the previously failing expanded workload for2,400s
without crossing6GiB:6,290,298,928 sampled bytes across9,328 samples. It passes all
28,056 voxel model views and reaches engine67's added pitch matrix before the harness
timeout. This is a retained **incomplete timed-out run**, not a full pass. The matching
pre-residency pitch workload failed at6,463,543,728bytes. The matched disabled-
retirement control, `pass1-residency-disabled-vulkan-ci`, again crosses the guard at
6,450,419,760bytes after104 samples. The first7,200s retry was interrupted during the
host disk-space incident and has no completed validation manifest. GPU repetitions
are being serialized with the unchanged6GiB guard and7,200s allowance. Sustained frame
pacing, multiple viewports and complete-world CPU cache growth remain open.

The catalogue contains11,422,202 triangles. Both9,000-frame forest production/regrowth
observations pass at approximately60fps with4,372,910,400 /4,214,034,680byte sampled
peaks. Their p95 work is5.154 /5.331ms, but669 /650 presentation intervals exceed20ms.
Other CPU/tooling work was active: these are lifecycle checks, not isolated matched
performance measurements, and they do not establish sustained smooth pacing.

LinuxVulkan CI36228046438 passes the tunnel-root repair and then exceeds the6GiB
guard at6,452,998,144bytes in the expanded catalogue matrix. Synchronous diagnostic
uploads retained all historical near-sized arena allocations. The follow-up retires
obsolete oversized pages after the readback fence and command/descriptor reset,
retaining one largest page plus at most32MiB of small scratch pages. An increasing-
payload exact RGBA/picking regression now retains46,149,632bytes in two pages.
Final refinery/ordering/atlas runs peak4,617,540,264 /4,513,206,856bytes. Complete1,169
nativeGL/Vulkan matrices now pass at5,764,748,664 /5,889,987,864 sampled bytes. Linux
CI36231074379 still exceeds6GiB at6,443,450,368bytes after the live-tunnel check. The
larger matching nativeCI workload also exceeds the guard at6,463,543,728bytes during
live-world review. All failures are retained; upload retirement alone is not a
completeCI or arbitrary-world memory bound.

## Train loading-gauge and silhouette repair:1,133 volumes (September26)

The complete nativeGL/Vulkan matrices pass with sampled peaks6,080,894,760 and
6,103,144,088bytes (5.66/5.68GiB), respectively, below the6GiB guard. Keeping reference
unit diagonals beside occupied/empty silhouette edges fixes the observed one-pixel
AsiaStar mismatch. The catalogue's triangle stream rises from9,527,302 to11,019,410
(15.66%); exactness has a measurable memory cost.

`pass1-train-clearance-perf.json` compares the frozen1,130 control and1,133 repair
sequentially on the same paused128×128 save, engine23 focus at1155,264,16,40° lens,
2560×1600 framebuffer and30 warm-up/1,800 measured frames. No other GPU checks run
concurrently. These are fixture-scoped measurements of the complete repair:

| Backend / zoom | Control → repair fps | Control → repair p95 work | Control → repair sampled bytes |
| --- | --- | --- | --- |
| OpenGL /2 | 60.006 →60.001 | 5.656 →5.538ms | 3,971,338,176 →4,340,256,992 |
| OpenGL /4 | 36.950 →36.732 | 27.340 →27.475ms | 4,074,770,368 →4,450,341,160 |
| Vulkan /2 | 60.002 →60.001 | 6.000 →5.863ms | 3,794,030,432 →4,176,335,024 |
| Vulkan /4 | 39.240 →38.948 | 25.969 →26.186ms | 3,867,676,512 →4,249,489,608 |

The repair adds approximately352…365MiB sampled memory in these matched cases.
Wide-view throughput is0.59%/0.74% lower onGL/Vulkan and remains well below60fps;
nearly every wide-view frame overruns. Close cases retain120…208 presentation
intervals over20ms despite60fps averages and zero work overruns. The correctness
repair is verified; smooth pacing and catalogue-wide throughput remain required.

The incremental1,144 sawmill matrices peak4,355,789,192 /4,124,463,328bytes; this
smaller diagnostic workload does not supersede the complete-catalogue memory peak.

## Aircraft expansion:1,031 volumes (September26)

The catalogue now has8,397,312 occupied cells /8,906,806 triangles. Focused Vulkan
aircraft matrices peak3,648,606,048bytes (normal,664 samples) and3,498,528,512bytes
(Toyland,232 samples), under6GiB. Separate1,800-frame GL helicopter runs each include
actual four-state stop/restart and ground-contact checks, peaking at3.33…3.51GiB.
Their mean60fps /p95 work4.82…5.31ms applies to zoom1 close airport views. They still
record2…6 presentation intervals above20ms, and an earlier held-service run retains
a966ms work spike. The broader zoom3 helicopter world averages32.447fps over3,600
frames (p95 work33.552ms,4,159,803,376-byte peak). Smooth catalogue-wide60fps remains
unproven. All checks use hidden inactive Cocoa windows and approximately250ms memory
sampling; verifier views are correctness evidence, not continuous gameplay bounds.
The completeGL41-engine matrix also passes at3,871,723,480bytes over713 samples.
Its subsequent1,800 close-view frames average60.001fps and5.468ms p95 work, but177
presentation intervals exceed20ms. Low CPU work alone does not establish pacing.

## Full-catalogue diagnostic retention repair (September26 03:37UTC)

`pass1-1002-transient-full-native` completes the entire1,002-volume nativeVulkan
matrix with a4,703,080,960-byte sampled peak (4.38GiB,3,017 samples) below6GiB.
The previous full-matrix failure retained every unmerged reference mesh in static
CPU maps and immutable GPU caches. Call-scoped CPU reference geometry now requests
nonpersistent instanced uploads: GL retires its temporary VAOs/buffers and Vulkan
uses reusable fence-owned frame slices. Persistent authored mesh ownership is unchanged.
An address-reuse regression renders eight changed payloads at identical vector
addresses, comparing exact RGBA/IDs and checking no persistent-cache growth.

This resolves the demonstrated full-verifier retention failure for this workload.
It does not establish arbitrary-map/all-day limits or a readback-pool-only improvement.
Its one paused capture frame is not a sustained performance benchmark. The full
nativeGL follow-up also completes at4,854,550,992bytes /4.52GiB over2,980 samples
(`pass1-1002-transient-gl`), preserving the same matrices and transient-address checks.
Current Linux/core/synchronization and Windows follow-up remain pending.

## Earlier expanded catalogue checkpoint (September26 02:54UTC)

The catalogue has grown from614 to1,002 volumes, with all62 tree families now voxel
bound. Earlier614 wide-view/soak figures below do not bound this larger catalogue.
`pass1-792-full-native` is terminated by the6GiB sampled guard at6,444,948,176bytes.
Focused904 house checks peak5,907,502,696bytes onGL and5,747,054,184bytes onVulkan;
the Vulkan run includes a new per-readback Cocoa autorelease pool. These are different
workloads from the full failure and do not establish a controlled memory improvement.
`pass1-1002-trees-vulkan` completes24,528 lifecycle and20,832 distant views plus atlas
checks at5,603,366,096bytes. This remains fixture-scoped tooling evidence, not an
all-day/multi-viewport or current wide-view performance bound. Full current validation
and the preserved pre-pool executable control are tracked in `VERIFICATION.md`.

The earlier full1,002 run also exceeds6GiB (6,444,292,888bytes), after1584 body/1332
ground checks and before the all-model matrix completes. The pre-pool executable
control fails framing (requested zoom1,measured2.5), so there is still no controlled
readback-pool memory improvement result. The ownership change is not a fix for the
demonstrated complete-verifier catalogue/reference-mesh memory growth.

`pass1-1002-wide-live` completes600 running frames on a newly generated128×128 world
at zoom5/2560×1600 with one visibility worker and opt-in conservative culling:
4,441,821,432-byte peak,30.764001fps,p9550.195375ms,max87.397917ms,599work overruns and
576intervals>20ms. It runs alongside tooling checks, and its map/workload differs from
the historical title-map stress case. It is bounded gameplay evidence only; sustained
smooth60fps, uncontended performance comparisons and current all-day limits remain open.

## Worker experiment and memory incident (September25–26)

Default visibility concurrency is one. `OPENTT3D_VOXEL_CULL_WORKERS=2` enables the
two-worker experiment with stable per-mesh ownership, camera cancellation and
original vertex×instance work balancing. Matched2560×1600 windowed1200-frame runs
measured51.27326fps single versus52.15755fps dual before weighted balancing.
`voxel-worker-balanced-window-6000` subsequently measured57.92705fps Vulkan,
p9520.536958ms,max72.790708ms,3254work overruns/452intervals>20ms at title(200,160),
rotation1,dolly5. It does not reach smooth60fps.

The fullscreen6000-frame pair at3024×1964 measured49.57165/49.49894fps but logged
different focuses (`3277.9993,2870,8` versus`3207.9993,2568,0`), so it is not a
controlled optimization comparison or directly comparable with2704×1756 history.
The dual paused validation also fails its requested zoom; retain that failure.

The subsequent OpenGL `voxel-worker-balanced-gl-window-6000` was killed by the user
after approximately20GB RAM growth. It is an aborted run. September26 bounded
reproductions exceed6GiB within roughly10seconds; sampled macOS footprint includes
compressed/GPU-accounted memory that RSS omits. No sustained memory bound is yet
claimed. `memory-gl-profile-600` / `memory-gl-allocation-stacks` retain heap/VM
profiles. `OPENTT3D_MEMORY_DEBUG=1` adds referenced CPU visibility/worker payload,
indexed-cache and owned GL page/mesh byte counters; shared references are not
additive unique-memory totals. `--memory-limit-mib` makes smoke runs self-terminate
on a sampled budget breach. These are diagnostic runs, not uncontended timing evidence.

### Memory fix: completed native OpenGL run (00:44 UTC September26)

The final `memory-gl-final-6000` completes all6,000 running frames at2560×1600,
title(200,160),rotation1,dolly5 with two workers, the614-volume catalogue and a6GiB
sampled physical-footprint guard. Peak footprint is **6,291,264,864 bytes /5.86GiB**
across922samples over234seconds. After60seconds it ranges5,792.30…5,999.82MiB;
later world states load additional immutable source meshes. The two instance buffers
remain exactly40,436,352bytes, live indexed CPU data stays around793.6MB and current
GL page data around1,055.4MB with approximately64,500current transforms. Historical
transform accumulation is removed. This validates this fixture/duration, not a
universal memory cap for arbitrary maps, multiple viewports or all-day play.

Changes: share immutable packed visibility results rather than copy them across
workers/results/render caches; discard redundant original-index streams; compact
immutable source-vector capacity; retain two GL texture-buffer allocations and update
their contents instead of orphaning the large instance stream every frame; retain
only current indexed transforms; drop indexed intermediates; release canceled camera
results even when workers receive no further work; retire visibility after close
zoom/Cab transitions. Tests verify actual ownership release and changing/returning
frame-slot record counts, palettes, IDs and exact geometry.

Intermediate runs remain failed evidence: CPU-sharing-only exceeds6GiB at30.16s;
stable-upload-only completes600frames but exceeds6GiB at225.19s in its long attempt.
The retained implementation uses no full-GPU-wait diagnostic. Final monitored GL
timing is26.86110fps,p9559.368167ms,max228.951584ms,6,000work overruns/5,999intervals
over20ms. Memory diagnosis has not solved the60fps target. Compare neither this
different-resolution run nor its memory-monitoring overhead as a controlled speedup.

`memory-gl-final-exact-world` verifies resident composition, growing/shrinking frame
buffers and4,096,000 exact world-atlas colour/picking pixels. All16,384,000 RGBA pixels
across its four phases match `memory-gl-final-original-control` with conservative
visibility disabled and the same614-volume catalogue. A576-volume historical GL
capture differs at one bridge pixel per image; a614-volume Vulkan/32bpp capture is
also not the same backend/blitter control. Both attempted comparisons remain recorded.
The preserved pre-memory development executable, rerun with the current catalogue,
original full geometry and matchedGL/40bpp settings, matches all16,384,000 pixels
exactly (`memory-gl-pre-fix-binary-control` / `pre-fix-binary-comparison.json`).
Default one-worker follow-up `memory-gl-default-worker-1200` also completes within
the6GiB guard:1,200frames/55.54seconds,5.74GiB peak,27.89132fps. It includes exact
instance/storage/composition checks. The updated development bundle matches this
final executable; Linux/no-Vulkan post-fix runs remain blocked by the unresponsive
Docker daemon, and all-day/multi-viewport memory bounds remain unverified.

## Rejected predecoded OpenGL lookup (20:26 UTC September25)

A temporary candidate replaced repeated packed-coordinate/normal decoding with a
shared immutable two-vec4 table per unique source vertex. Position, normal and palette
words were preserved exactly; original triangle/instance order, live palettes/IDs,
hardware precision and full geometry stayed intact. It was slower and is removed,
including its temporary `OPENTT3D_GL_DECODED_LOOKUP` switch and candidate-only helpers.

Matched nativeM3Pro/Classic40bpp,2704×1756 fullscreen,title(200,160),rotation1,dolly5,
600 running frames, no concurrent build/render workload:

| Artifact | Preparation | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-gl-packed-lookup-wide-600` | asynchronous control | 28.22097 | 63.88600ms | 346.08033ms | 600 | 585 |
| `voxel-gl-decoded-lookup-wide-600` | asynchronous candidate | 26.53745 | 54.02921ms | 351.72054ms | 600 | 598 |
| `voxel-gl-packed-lookup-sync-wide-600` | synchronous control | 32.27338 | 44.96479ms | 56.36975ms | 600 | 591 |
| `voxel-gl-decoded-lookup-sync-wide-600` | synchronous candidate | 29.50468 | 46.38421ms | 62.76246ms | 600 | 598 |

The second pair excludes background-readiness ambiguity and confirms the regression;
no sustained performance improvement is claimed. Native and Linux GL3.2/GLSL150 with
gpu-shader5 disabled passed16,968 tree views,5,712 distant views and five edited streams.
Both packed-control and full-mesh-control comparisons match all16,384,000 world RGBA
pixels across four atlas phases; picking is independently checked during relocation.
The first Linux attempt was terminated by the outer120-second tool limit; the fresh
`voxel-gl32-decoded-lookup-complete` run completed with a sufficient outer timeout.
All artifacts remain. After restoring the original path, native183/Linux184 CPU tests
pass and `voxel-gl-packed-lookup-restored/rollback-comparison.json` matches all four
control images exactly. The full576 native renderer regression also completed before
the experiment. The latest LaunchServices input audit again reports`front=loginwindow`;
foreground interaction and the smooth60fps target remain open.

## OpenGL conservative visibility and ordered pages (September25)

The exact path is now available under `OPENTT3D_VOXEL_CULL=1` on GL3.2/GLSL150.
Native GL reports4subpixel bits, so its conservative uncertainty retains132.75million
references at the paused wide pose versus about17.26million tree references with
Vulkan's8-bit setting. Indexed GL submits65.38million unique vertices. The reported
hardware precision is respected; original geometry and comparison tolerance remain.

Same nativeM3Pro/Classic40bpp,2704×1756 fullscreen,title(200,160),rotation1,dolly5,
running and no concurrent build/render workload. First four rows force synchronous
preparation; final two exercise actual background preparation:

| Artifact | Frames | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `voxel-gl-visible-wide-600` | 600 | 14.24057 | 108.72600ms | 135.38571ms | 600 | 600 |
| `voxel-gl-indexed-wide-600` (failed reindexing cost) | 600 | 4.62600 | 418.92742ms | 637.91842ms | 600 | 598 |
| `voxel-gl-index-cache-wide-600` | 600 | 14.38541 | 131.62567ms | 195.50471ms | 600 | 596 |
| `voxel-gl-paged-wide-600` | 600 | 32.10381 | 44.36175ms | 54.38833ms | 600 | 590 |
| `voxel-gl-paged-async-wide-6000` | 6000 | 31.53486 | 41.73833ms | 370.28625ms | 6000 | 5990 |
| `voxel-gl-stable-pages-async-wide-6000` | 6000 | 31.94751 | 42.69938ms | 237.86933ms | 6000 | 5841 |

Initial indexing rebuilt every retained corner when a tree changed. Per-transform
index caching removes that waste, but whole-forest buffers still upload217.47MB/frame
on average. Ordered256-instance pages reuse complete subsequences and reduce average
uploads to16.70MB/frame in the paired600-frame run; upload mean14.21→1.19ms, backend
mean50.69→12.17ms. Parent/child pages are separate. Subsequent fragment merging and
redundant-state avoidance bound long-run page proliferation; current palette/ID
records are always fresh. All staged representations retain every reference pixel.

Current Vulkan material-lookup run `voxel-direct-material-async-wide-6000` measures
57.39769fps,p9520.10954ms,max150.13271ms,2838overruns/320long intervals; capture mean
9.44372ms. The change from57.19fps is small and not a smooth60fps claim. Both backends
retain cold-camera/startup spikes and unfinished foreground/hardware coverage.

Linux GL3.2/no-gpu-shader5 and a separate no-Vulkan build complete small-world live
checks at roughly8.3softwarefps, correctness-only. A separate atlas-row-dependent
house pixel is fixed with sprite-local UV bias; cache on/off comparisons and the
original complete-world reference remain exact. See `VERIFICATION.md` for the
retained failures, forced-relocation and page-eviction regressions.

## Sustained asynchronous and temporal batching checkpoint (September25)

Same native2704×1756 wide title pose and full geometry;6,000 running frames,
`OPENTT3D_VOXEL_CULL=1`, background visibility and diagnostic worker logging enabled,
no concurrent build/render workload:

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-cull-current-async-wide-6000` | 54.44876 | 20.75975ms | 128.88217ms | 4700 | 526 |
| `voxel-temporal-batch-async-wide-6000` | 57.18563 | 19.83025ms | 129.72550ms | 2905 | 271 |

Initial wide visibility readiness is about11seconds (one camera generation), with
original full-mesh fallback throughout preparation. The cache then retains18,614,430
of2,567,701,734 combined tree/rail/fence vertices at the diagnostic scene state.
Temporal batching reuses only unchanged per-position mesh/layer hash entries; fresh
instance data and first-capture layer ordering remain. Backend mean4.80996→3.89992ms,
capture mean remains9.74ms. All4,096,000 paused reference pixels and native/Linux/GL
ordering checks agree. Smooth60fps and interactive cold-camera behavior remain unmet.

`voxel-cull-current-cpu-profile/cpu-sample.txt` is a separate five-second steady-state
profile, not the60-frame warm-up measurement in that directory. The sampled process
was terminated afterward. It also motivates bounded source-provenance and recent-
palette lookup caches; those pass full native507 palette/renderer checks, with Linux
validation and an uncontended performance measurement still being audited.

## Triangle coverage and capture follow-up — still below60fps (September25)

Conservative triangle-edge/sample intervals and cached unique-position projections
retain17,264,058 of2,515,792,452 tree vertices at the paused wide pose. Exact complete
world comparisons remain unchanged. Qualified running rails/fences also have a
lossless packed path. Default tree capture now avoids repeated string-map lookup,
duplicate log allocations and unnecessary source-chart fetching; relative child
framing remains source-aware and lazy.

Same2704×1756 nativeM3Pro/Classic40bpp/running title(200,160),rotation1,dolly5,
600frames, no concurrent build/render workload. These later controlled runs force
`OPENTT3D_VOXEL_CULL_SYNC=1`; they do not prove asynchronous camera readiness:

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-direct-tree-capture-wide-600` | 55.77719 | 20.28958ms | 29.15513ms | 472 | 46 |

Mean capture9.68526ms and GPU12.15671ms remain significant. Earlier checkpoints are
33.02308fps after validated static palette templates,37.44571 after triangle sample
coverage and51.07679 after direct tree binding lookup. Source-vertex profiling totals
are pre-cull; retained-stream logs describe actual surviving primitives.

Interactive culling now queues value-only background visibility jobs and renders the
original packed meshes until ready. Stale camera generations cancel, per-transform
results reconcile with live instance sequences, and at most32 missing transforms
are computed synchronously per frame. `voxel-pixel-cull-async-reconciled-wide-600`,
before the latest triangle/capture changes, measures24.47671fps,p95111.50513ms,
max205.75121ms,600overruns/600long intervals. This is a latency failure, not the
synchronous55.78fps result. Cold preparation, moving-camera readiness, GL support,
foreground behavior and sustained smooth60fps remain required. The latest native
input attempt reports `front=loginwindow`; Linux asynchronous small-world core/sync
validation finishes but its software rate is not a hardware performance target.

## Lossless packing and conservative visibility — opt-in (10:05 UTC September25)

`OPENTT3D_VOXEL_PACKED=1` stores qualifying voxel vertices in32 bits, with immutable
per-mesh attribute/normal tables. Every source vertex's20 words must roundtrip exactly;
otherwise the original stream is retained.490/495 models qualify. Signed zeros, normal
bits, palettes, triangle/provoking-vertex order and instance transforms remain exact.
The fast decoder is selected only when every coordinate product is provably exact.
Packing alone saves storage but does not remove the main primitive-processing cost.

`OPENTT3D_VOXEL_CULL=1` also enables camera-local, conservative tree-triangle visibility
at wide orbit scales. Error-expanded bounds retain every possible pixel-centre hit,
all uncertain/near-plane cases and the original primitive/instance order. This is
visibility rejection, not a lower-detail mesh or a distance cutoff. Per-camera CPU
results are cached; three original vertex references plus a local instance reference
fit in64 bits. GPU streams are reused only while their complete transform sequence
matches, and replaced buffers retire behind frame/readback fences.

NativeM3Pro,Classic40bpp,title(200,160),rotation1,2704×1756 fullscreen; no concurrent
build/render workload. Every listed600-frame run has600 or599 work overruns:

| Artifact | FPS | Work p95 | Work max | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: |
| `volume-mesh-control-wide-120` (120frames) | 3.23838 | 310.40388ms | 325.25250ms | 120 |
| `voxel-packed-wide-600` | 3.07909 | 327.50388ms | 1487.33438ms | 600 |
| `voxel-packed-fast-wide-600` | 3.19543 | 313.53296ms | 1489.27908ms | 600 |
| `voxel-packed-normal-control-600` (dolly1) | 53.75371 | 19.38196ms | 20.55888ms | 4 |
| `voxel-packed-fast-normal-600` (dolly1) | 54.07160 | 19.34371ms | 23.84108ms | 6 |
| `voxel-pixel-cull-wide-120` (120frames) | 6.41922 | 183.20575ms | 190.50200ms | 120 |
| `voxel-pixel-cull-compact-wide-600` | 26.01847 | 40.38271ms | 47.87479ms | 600 |
| `voxel-pixel-cull-resident-wide-600` | 31.55791 | 38.85300ms | 66.49675ms | 600 |

The wide paused scene retains51,980,439 of2,515,792,452 tree vertices after conservative
culling. Packing, initial visibility, compact references and resident-stream captures
each match all4,096,000 pixels of `volume-world-reference-wide`. Resident timing still
has capture mean18.32735ms,backend mean7.24696ms and GPU mean30.67417ms. Cold wide-camera
preparation remains approximately17seconds (earlier unoptimized form42seconds), so this
is not yet an acceptable interactive/default path. Smooth60fps, camera-motion latency,
GL/hardware coverage and broader checks remain open.

The native/Linux matrices include2,856 additional distant240×180 views at ordinary
and large origins, including coincident instances with distinct palettes/picking IDs.
Linux giant-world live software rendering times out after2400seconds following its
completed correctness matrices; a fresh128×128 Toyland run completes12 measured frames
plus warm-up under core/synchronization validation. Its rate is not a hardware target.

Ray/plane follow-ups remain experimental: exact FMA wrappers retain the earlier
prototype images while avoiding Metal's non-inlined precision arithmetic. Diagnostic
120-frame wide results are17.16414fps ray and20.84598fps edge-corrected axis planes.
The naive plane path reaches35.05273fps but fails exact edge tests; do not count that
as a usable result. The corrected planes still have whole-world discrepancies.
An unmerged-tree control independently differs from the existing compact mesh by21
wide-world pixels. That pre-existing discrepancy does not relax the optimization
comparison or supply visual approval. All failed evidence remains.

## Full-cell volume investigation — opt-in, unsuccessful so far (06:17 UTC September25)

`OPENTT3D_VOXEL_VOLUMES=1` enables an experimental Vulkan path for compatible opaque
tree instances. It retains all authored cells and six original palette faces, using
a guarded36-vertex proxy and cell traversal. Full meshes remain the default/reference
and the fallback for incompatible transforms, transparency and near-plane/eye
intersections. No geometry, draw distance or comparison tolerance is reduced.

The native2,856 mesh and16,968 lifecycle/palette/scale matrices now pass after fixing
analytic-boundary guard coverage, fused position reconstruction and approximate shader
division at subpixel edges. Broader correctness remains unresolved: Linux's lime04
case changes one colour pixel; the full paused world changes176/4,096,000 pixels from
the mesh control. Front-proxy traversal changes one further pixel from the earlier
prototype. These variants are not visually approved or suitable for default use.

Short diagnostic profiles use the same nativeM3Pro,Classic40bpp,running title world
at(200,160),rotation1,dolly5,2704×1756 fullscreen,120frames and no concurrent build or
render workload. They assess feasibility while the exactness defects stay open:

| Artifact | FPS | Work p95 | Work max |
| --- | ---: | ---: | ---: |
| `volume-mesh-control-wide-120` | 3.23838 | 310.40388ms | 325.25250ms |
| `volume-diagnostic-wide-120` | 0.26068 | 7594.41263ms | 8107.46088ms |
| `volume-bounded-wide-120` | 0.56367 | 1912.84867ms | 3351.86900ms |
| `volume-front-proxy-wide-120` | 1.13410 | 937.95829ms | 1003.73913ms |

Every run has120 work overruns and120 intervals above20ms. Conservative plane-candidate
rejection and a remaining-depth bound preserve all4,096,000 pixels of the unbounded
prototype; they do not fix its176 baseline differences. Front proxies permit a
conservative depth output and retain full meshes when the near plane intersects the
proxy. Fragment traversal/raster emulation remains much slower than the already slow
mesh control. Continue investigating; do not claim the throughput defect resolved.

## 494-volume regression — urgent unresolved tree throughput (September25)

The nine new Toyland voxel families expose excessive submitted geometry at wide
views. Native M3 Pro,Classic40bpp,40° lens,unlimited distance,600 running frames and
no concurrent build/render workload. The actual fullscreen backing size is now
**3024×1964**, rather than the earlier2704×1756; these are not paired speedup claims.
Wide uses title(200,160),rotation1,dolly5; normal uses the same scene atdolly1.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-494-wide-vulkan-600` | 3.16757 | 341.93471ms | 1469.50583ms | 600 | 600 |
| `pass1-494-wide-opengl-600` | 3.07975 | 608.13488ms | 1569.55371ms | 600 | 600 |
| `pass1-494-normal-vulkan-600` | 37.30188 | 28.26788ms | 39.91608ms | 598 | 597 |
| `pass1-494-normal-opengl-600` | 37.66635 | 42.55050ms | 49.21454ms | 545 | 545 |

The wide Vulkan capture contains a mean**2,520,949,512 tree source vertices**, versus
about20.58million before those families were voxel-bound. These are captured source
counts before indexed vertex reuse. GPU mean314.16769ms and buffer-wait mean284.45999ms
dominate; capture mean23.12211ms, backend mean3.53743ms, mesh-upload mean0.06191ms and
zero readback/repack do not explain the main cost. The cache holds7,433,085 source /
2,884,436 stored vertices in59 buffers,245,598,092 used bytes, reused by the instances.

This is a major open performance defect, not a successful production checkpoint.
Correctness/coverage gains do not offset it. Next performance work must address
full-quality voxel submission/visibility/topology cost while preserving source
geometry, picking, draw distance and the strict comparisons.

A static-unlit-palette vertex shortcut was tried without removing any geometry.
`pass1-palette-static-after-vulkan` differs by39 paused RGB pixels from its control;
it is rejected. The unqualified candidate captures1280×800 versus its2560×1600
control after a display backing change, so that comparison is invalid and the
candidate is also removed. Both experiments and reports are retained; regenerated
shaders restore the prior exact path. No performance success is claimed for them.

The cinema/buoy palette observations ran alongside correctness work and are not
controlled performance measurements. The final LaunchServices input probe passes
32 cycles/four fullscreen transitions, but its one-frame menu measurement establishes
readiness only. Earlier foreground and long-submit failures remain relevant.

## 416-volume / stable-order checkpoint (2026-09-25, 00:57 UTC)

Native M3 Pro, Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance.
Wide is the running title world at(200,160),rotation1,dolly5,600 frames. Cab uses
the actual public electric/tropical-maglev consists,6,000 frames and a secondary
viewport. These measurements have no concurrent build/render workload.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-416-wide-vulkan-600` baseline | 51.20688 | 20.44533ms | 28.79196ms | 600 | 92 |
| `pass1-416-wide-opengl-600` baseline | 45.83082 | 24.53000ms | 31.72133ms | 600 | 600 |
| `pass1-416-zero-yaw-wide-vulkan-600` experiment | 52.57029 | 19.62154ms | 27.60925ms | 600 | 10 |
| `pass1-416-zero-yaw-wide-opengl-600` rejected experiment | 44.83206 | 27.83883ms | 32.82183ms | 600 | 600 |
| `pass1-416-stable-order-wide-vulkan-600` current | 52.45036 | 19.99913ms | 28.05779ms | 600 | 31 |
| `pass1-416-stable-order-wide-opengl-600` current | 45.61511 | 27.18792ms | 31.40263ms | 600 | 600 |
| `pass1-416-electric-consist-cab-6000` Vulkan, before ordering change | 60.00233 | 9.35404ms | 38.33058ms | 35 | 19 |
| `pass1-416-maglev-consist-cab-6000` GL, before ordering change | 59.94947 | 13.29679ms | 79.64563ms | 109 | 24 |
| `pass1-416-final-electric-cab-6000` Vulkan, current | 60.00240 | 9.44350ms | 36.67188ms | 25 | 13 |
| `pass1-416-final-maglev-cab-6000` GL, current | 59.93020 | 10.55796ms | 75.86554ms | 128 | 23 |

Vulkan retains the zero-heading rotation shortcut; GL's slower experiment is removed.
Repeated paused32bpp captures initially vary by3/7 pixels even after restoring the
same GL code. Independent CPU/GPU probes reproduce allocation-address-dependent
coplanar colour/picking. First-captured mesh order within each parent/child layer
fixes that defect; current repeated images match4,096,000 RGB pixels per backend.
This correction is required for determinism, not claimed as a throughput improvement.
Full renderer validation remains separate from these bounded performance runs.
The final two Cab runs wait for the Linux validation process to exit before
measurement. Their different operating traces and visible depot/forest context
remain scoped evidence; near60fps averages do not establish smooth frame times.

The Vulkan baseline spends11.15295ms mean/11.42746ms p95 in capture,4.56379ms backend
p95 and1.03363ms buffer-wait p95; the scene includes34,673,850 running-rail and
15,473,160 fence vertices. GL maglev buffer-wait p95 is6.42858ms,max16.00958ms. Its
Cab locomotive87 remains legacy art; reference food100 is an attached voxel wagon.
The two Cab traces differ and are not a paired backend comparison or cargo-delivery
proof. All work overruns/spikes, historical foreground/long-submit failures and the
unmet wide60 target remain recorded. The earlier native input run passes32 focus/
capture cycles/four fullscreen transitions, but the later00:36UTC app-bundle attempt
finds `front=loginwindow`. Its failure and the separate successful one-frame bundle
readiness capture do not establish sustained foreground or current input approval.

## Toyland-road/365-volume cargo checkpoint (2026-09-24, 20:02 UTC)

NativeM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance, actual
public2050 sugar174/cola177 service Cab and secondary view. No concurrent build/render
workload. Both6,000-frame runs observe real0/17–17/17 and rendered depot entry/exit.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-toy-sugar-cargo-cab-6000` Vulkan | 60.00316 | 9.07575ms | 17.91129ms | 1 | 0 |
| `pass1-toy-cola-cargo-cab-6000` GL | 60.00240 | 9.68908ms | 20.37433ms | 1 | 1 |

These different service traces are scoped evidence, not a paired backend comparison.
Their good averages do not resolve the wide52.42672fps, foreground-input or earlier
long-submit failures. Complete performance approval remains open.

## Climate-road/349-volume checkpoint (2026-09-24, 19:14 UTC)

NativeM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance, actual
public2050 fleet Cab/secondary view. No concurrent build/render workload. Each run
follows vehicle0: Arctic paper161 or tropical rubber173, with actual binding capture.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-climate-arctic-cab-vulkan-6000` | 60.00240 | 9.58442ms | 26.72654ms | 29 | 11 |
| `pass1-climate-tropic-cab-opengl-6000` | 60.00240 | 7.99792ms | 23.47163ms | 9 | 4 |

The climates/fleets differ; these are scoped operating traces, not a paired backend
comparison or cargo-delivery proof. Retain all spikes, the wide52.42672fps checkpoint,
foreground-input failure and earlier long-submit stalls. Complete performance
approval remains open despite these near60fps averages.

## Open-road/316-volume cargo checkpoint (2026-09-24, 17:49 UTC)

NativeM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance, actual
coal-service Cab/secondary view. No concurrent build/render workload. Both6,000-frame
runs observe original empty/full cargo and rendered depot entry/exit on vehicle0.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-coal-uhl-live-cargo-cab-6000` Vulkan | 60.00240 | 9.18054ms | 35.06146ms | 27 | 10 |
| `pass1-coal-dw-live-cargo-cab-6000` GL | 60.00266 | 9.22708ms | 52.43067ms | 26 | 16 |

These use different operating engines/routes in normal2050 fixtures, not identical
simulation traces. Actual0/25–25/25 and0/28–28/28 are retained in the logs. Averages
do not erase the remaining spikes, wide52.42672fps checkpoint, foreground-input
failure or earlier long-submit stalls. Complete performance approval remains open.

## Residential/288-volume checkpoint (2026-09-24, 16:49 UTC)

NativeM3Pro,Vulkan,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance;
ordinary1950 city, actual house27/variant2,dolly1. No concurrent build/review.
`pass1-288-residential-city-1800`:60.00600fps,p955.74738ms,max6.66021ms,zero work
overruns/intervals>20ms. This is a scoped city result; wide and earlier foreground/
long-submit failures remain open. New-world and fullscreen-menu one-frame warm-up
captures establish readiness only. `pass1-288-native-input-recheck` still reports
`front=loginwindow`, so no new foreground-input/performance approval is claimed.

## Dock/265-volume checkpoint (2026-09-24, 15:09 UTC)

NativeM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance; no concurrent
build/review. Lamp views use actual dock4/5,dolly1. Wide is title(200,160),rotation1,
dolly5. The6,000-frame harbour Cab follows hovercraft208 and observes depot traversal.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-docks-lamp-foam-x-live-1800` Vulkan | 60.00241 | 5.56142ms | 35.99379ms | 1 | 1 |
| `pass1-docks-lamp-foam-y-live-1800` GL | 60.00462 | 5.80833ms | 11.80750ms | 0 | 0 |
| `pass1-265-wide-vulkan-600` | 52.42672 | 19.87517ms | 28.85075ms | 600 | 19 |
| `pass1-docks-complete-harbour-cab-6000` GL | 60.00240 | 9.73696ms | 54.52192ms | 26 | 13 |

Linux GL palette observation passes at16.94852fps,p9563.71783ms,max76.60725ms with1800
overruns/long intervals; this is software correctness evidence. Running traces are
not identical. Native averages retain all spikes, the wide60fps failure and earlier
foreground/long-submit defects. Complete performance approval remains open.

## Ship-depot/253-volume service checkpoint (2026-09-24, 14:29 UTC)

NativeM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance; no concurrent
build/review during these6,000-frame runs. Actual freighter212/axis0 and hovercraft208/
axis1 complete non-halting depot traversal with their Cab and secondary viewports.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-ship-depot-x-cab-traversal-6000` Vulkan | 60.00169 | 9.91088ms | 36.15783ms | 11 | 6 |
| `pass1-ship-depot-y-cab-traversal-6000` GL | 60.00280 | 9.55008ms | 26.76467ms | 6 | 2 |

Linux GL `pass1-ship-depot-y-stock-traversal` renders correctly but misses the brief
service state at5.66590fps,p95253.65ms. The subsequent ordinary held-stop Vulkan/core/
sync route passes traversal at5.94531fps,p95174.21979ms,max333.86196ms,1800overruns/
long intervals. These software runs and the concurrent native road-observer regression
are correctness evidence only. Scoped native averages retain all spikes; wide60,
foreground and earlier long-submit problems remain unresolved.

## Ships/249-volume checkpoint (2026-09-24, 13:39 UTC)

NativeM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance. Runs below
had no concurrent build/review. Ship Cab follows actual vehicle0 in each public
fixture: ordinary freighter212 or Toyland cargo214, with its secondary window.
Wide remains title(200,160),rotation1,dolly5; these are not identical simulation traces.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-249-guarded-wide-600` Vulkan | 53.33277 | 19.42442ms | 28.21125ms | 600 | 9 |
| `pass1-ship-cab-vulkan-6000` | 60.00279 | 8.98833ms | 35.59479ms | 8 | 7 |
| `pass1-toy-ship-cab-opengl-6000` | 60.00352 | 8.86854ms | 18.17788ms | 3 | 0 |

Correct cell-reference colour boundaries require unit guard strips around coplanar
colour changes. On the initial249-volume pack, actual triangles rose1,212,258→1,484,900
while the greedy rectangle count and occupied geometry stayed unchanged. Current
ship refinements bring triangles to1,487,012. Wide throughput remains below60fps;
the guarded-mesh result does not establish a controlled speedup or final approval.
The Vulkan Cab maximum includes27.38346ms buffer waiting. Scoped averages retain all
spikes and the earlier foreground/one-second-submit failures. Ship-depot sprite
panels visible in both Cab captures remain a missing asset, not completed geometry.

## Stadium/243-volume checkpoint (2026-09-24, 11:20 UTC)

NativeM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens/unlimited distance; no concurrent
build/review during these measurements. Stadiums use actual primary20/32,dolly0.
Wide remains title(200,160),rotation1,dolly5; running traces are not identical.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-stadium-gridiron-live-1800` Vulkan | 59.99915 | 6.06088ms | 6.75792ms | 0 | 0 |
| `pass1-stadium-soccer-live-1800` GL | 60.00241 | 5.41933ms | 8.89388ms | 0 | 0 |
| `pass1-243-wide-vulkan-600` | 52.70264 | 19.60867ms | 28.87583ms | 600 | 12 |
| `pass1-243-ground-mask-wide-600` Vulkan | 53.73545 | 19.23383ms | 27.70142ms | 600 | 4 |
| `pass1-243-wide-opengl-600` | 46.69611 | 25.99688ms | 31.50608ms | 600 | 591 |

Stadium animation observers see all five actual crowd phases and all four applicable
scoreboard phases. Permanent voxel grounds preserve full tile coverage, original
clipping and independent ownership. The first wide capture p95 was11.649ms; immutable
ground-binding membership now skips variant/source work for unrelated houses and
terrain neighbours. Scoped exact ground/state/join/picking checks pass afterwards.
The small measured recovery does not establish60fps or complete performance approval.

Linux GL `pass1-stadium-live-palette` passes actual palette observation at17.414fps,
p9560.169ms,max296.421ms,600overruns/long intervals. It ran on llvmpipe alongside native
verification and is correctness evidence only. Earlier foreground/Cab and long-submit
failures remain in the work queue.

## Breadth-first212-volume checkpoint (2026-09-24, 08:59 UTC)

M3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens and unlimited distance. Wide uses
the existing title(200,160),rotation1,dolly5. Measurements ran without concurrent
builds/reviews. These remain running-scene checkpoints, not identical simulation traces.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pass1-212-wide-vulkan-600` (rejected broad precision) | 36.21779 | 28.76367ms | 38.91483ms | 600 | 599 |
| `pass1-212-wide-cpu-rounding-600` (final Vulkan) | 54.40975 | 19.02704ms | 27.82092ms | 600 | 4 |
| `pass1-212-wide-opengl-600` | 47.65098 | 26.49663ms | 29.92004ms | 600 | 506 |
| `pass1-212-cargo-fleet-cab-cpu-rounding-6000` (final Vulkan) | 60.00214 | 8.87996ms | 23.41763ms | 17 | 3 |

The vehicle-reference mismatch was CPU FMA contraction, not a need to slow every GPU
position calculation. Broad `precise` propagation in the diagnostic Vulkan shader
increased GPU mean to27.606ms and buffer-wait mean to9.883ms, while capture p95 stayed
about10.88ms. That experiment was removed. The original GPU shader plus separately
rounded CPU reference products passes the full exact model/vehicle/tree matrices and
recovers the earlier wide performance range. Instance layout/detail/distance are intact.

The final Cab follows actual vehicle0/engine155 in the public temperate cargo fleet,
including its secondary vehicle window. Its averages do not erase17 overruns, three
long intervals, the wide60fps failure or earlier foreground/one-second-submit defects.
The earlier `pass1-212-cargo-fleet-cab-6000` used the rejected precision shader and is
historical only:60.00165fps,p959.13071ms,max30.79158ms,14overruns/7long intervals.
No complete performance or release approval.

## Power-station animation and145-volume checkpoint (2026-09-24)

All native runs below useM3Pro,Classic/40bpp,2704×1756 fullscreen,40° lens and unlimited
distance. The fixed power-station view is actual tile(52,34),dolly0,rotation0,pitch30.
Both6,000-frame runs observe all six original spark frames on one unchanged tile.

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-power-sparks-fixed-view-vulkan-6000` | 60.00240 | 5.30371ms | 8.52696ms | 0 | 0 |
| `voxel-power-sparks-opengl-6000` | 60.00179 | 5.33371ms | 18.34621ms | 1 | 0 |
| `voxel-145-wide-vulkan-600` | 54.80344 | 18.86204ms | 28.13042ms | 600 | 2 |
| `voxel-145-wide-opengl-600` | 47.38036 | 26.37796ms | 29.74083ms | 600 | 550 |

Wide uses the same title setup,(200,160),rotation1,dolly5. Explicit child layers fix
parent/arc compositing without changing geometry, distance or shader layout. These
are measured scene checkpoints, not complete sustained/foreground/hardware approval.

`voxel-power-sparks-live-6000` is a retained failed calibration run: actual yaw0.04241,
pitch37.64285,dolly−0.598 differ from the requested0/30/0. All actual spark frames were
observed, but its59.411fps is not the calibrated scene result. Work max1,028.65575ms
includes1,024.506542ms in queue submission; the earlier long-submit problem remains
unresolved. Fixed-view harness checks now reject yaw/pitch drift as well as dolly drift.

Earlier136-volume `voxel-power-mine-cab-6000` observes cargo/depot traversal at60.00240fps,
p956.170916ms,max21.824333ms,one overrun/long interval. Its secondary-window framing is
wider than previous Cab artifacts, so it is not a controlled speedup. Linux GL
`voxel-power-sparks-live-validation` passes renderer/state checks at18.535fps on software
rendering; it ran alongside native gallery work and is correctness evidence only.

## Ground conformance extension (2026-09-24, 00:51 UTC)

Uniform half-unit terrain edges removed raster gaps but increased wide work:
`voxel-ground-aligned-wide-vulkan-600`,48.319fps,p9521.944ms,max31.866ms,
600overruns/506intervals>20ms. The final neighbour-aware path uses half-unit samples
only at voxel/rough Toyland contacts and whole edges for ordinary terrain. It keeps
the same map coverage/height, geometry detail,40° lens and unlimited distance.

131-volume nativeM3Pro,Classic/40bpp,2704×1756 fullscreen; no concurrent build:

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-ground-final-wide-vulkan-600` | 54.726 | 18.847ms | 27.364ms | 600 | 2 |
| `voxel-ground-final-wide-opengl-600` | 45.672 | 26.796ms | 31.376ms | 600 | 600 |
| `voxel-extension-final-cab-vulkan-6000` | 60.00240 | 9.67692ms | 31.20667ms | 1 | 1 |
| `voxel-extension-final-cab-opengl-6000` | 60.00256 | 9.22421ms | 24.46275ms | 8 | 6 |

Wide uses title(200,160),rotation1,dolly5. Cab uses the ordinary recurring depot/coal
route, actual vehicle0 and secondary window; both cargo/depot observations pass.
These are matched setup checkpoints, not identical running simulation traces.
Wide60, remaining Cab spikes, earlier foreground/long-submit failures and hardware
coverage stay unresolved. The seam correction is not full performance approval.

## Catalogue growth and voxel-tree lookup control (2026-09-23, 22:41 UTC)

Final128-volume Cab/secondary checks on the recurring depot route retain the
remaining spikes. `voxel-final-depot-cab-opengl-6000`:60.00280fps,p959.77775ms,
max28.69479ms,10work overruns/7intervals>20ms. The Vulkan counterpart:
60.00239fps,p959.46183ms,max27.54413ms,33overruns/11long intervals. Both observe
actual0/20–20/20 cargo and visible/inside/visible depot traversal. These are successful
state observations and incomplete smoothness results, not full60fps approval.

The128-volume wide-title recheck showed CPU capture overhead: Vulkan45.987fps and
GL39.445fps, both600/600 work overruns/long intervals. Rail/fence counts are unchanged;
new depot geometry increases the road contribution. CPU capture, rather than GPU
time, was the main change. Repeated string/tuple voxel-tree membership searches now
use immutable seven-state masks, with original-sprite provenance invalidated by the
existing texture generation. `OPENTT3D_VOXEL_TREE_LOOKUP_CACHE=0` keeps the control.

Same title setup,(200,160),rotation1,dolly5,2704×1756,Classic/40bpp,unlimited distance:

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-tree-lookup-control-vulkan-600` | 43.589 | 23.468ms | 31.803ms | 600 | 600 |
| `voxel-tree-lookup-wide-vulkan-600` | 56.584 | 18.462ms | 28.272ms | 597 | 3 |
| `voxel-tree-lookup-control-opengl-600` | 40.531 | 25.478ms | 33.910ms | 600 | 600 |
| `voxel-tree-lookup-wide-opengl-600` | 49.510 | 25.378ms | 28.687ms | 600 | 185 |

Paired Vulkan capture p95 falls16.523→10.009ms. All4,096,000 paused RGB screenshot
pixels match and tree/picking checks pass. Running worlds advance at different rates;
these are matched setup measurements, not identical traces. Wide60, foreground and
the previous long queue-submit stalls remain unresolved.

`voxel-mine-complete-scene-6000` includes the new stockpiles, actual winding animation
and cargo observations: Vulkan60.00241fps,p956.01925ms,max7.69217ms,zero overruns/long
intervals. `voxel-road-depot-traversal-6000` adds actual visible/inside/visible depot
traversal:60.00240fps,p955.695ms,max8.95429ms,zero overruns/long intervals. Both are
6,000-frame fullscreen scene passes; neither establishes the complete performance goal.

## Actual coal-truck cargo and Cab (2026-09-23, 20:23 UTC)

Both6,000-frame native runs use2704×1756 fullscreen,Classic/40bpp,original simulation,
fixed40° lens and unlimited distance. They observe actual0/20 and20/20 cargo on truck0.

| Artifact | Backend/view | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-coal-truck-live-cargo-6000` | Vulkan, fixed loading-stop view | 60.00240 | 5.48621ms | 8.29654ms | 0 | 0 |
| `voxel-coal-truck-cab-opengl-6000` | GL, actual Cab/secondary viewport | 60.00163 | 8.97546ms | 16.73117ms | 1 | 0 |

The GL overrun is retained; these scenes do not resolve the previous wide-map,
foreground or long queue-submit cases. Linux GL cargo validation averages23.331fps
at1280×800 on software rendering,2,400 frames; it is correctness evidence only.

## Operating voxel mine scene (2026-09-23, 19:21 UTC)

`voxel-mine-animation-service-6000`: an ordinary funded coal mine with a working
truck/power-station route, original simulation and all three observed winding-wheel
frames. Native Vulkan/M3 Pro,Classic/40bpp,2704×1756 fullscreen,dolly0,fixed40° lens,
unlimited distance.6,000 frames: **60.00213fps**,work p95 **5.85267ms**,max **8.03904ms**,
**zero work overruns and zero intervals>20ms**. This establishes the measured scene's
smooth run; it does not resolve the older wide-map, foreground or driver-stall failures.
The matching Linux core/sync animation check is correctness evidence only: llvmpipe
averages8.878fps at1280×800,2,400 frames,all work/interval limits exceeded.

## SH30 operating fixture checkpoint (2026-09-23, 16:09 UTC)

`voxel-sh30-cab-6000`: the new public-NoAI engine23 fixture, actual Cab and secondary
vehicle viewport, native Vulkan/M3 Pro, Classic/40bpp,2704×1756 fullscreen and
unlimited distance. **60.00239fps**,work p95 **9.18613ms**,max **88.53458ms**,
**16work overruns /10intervals>20ms**. This is a different, slower locomotive/route
workload from the earlier default-electric and aircraft fixtures, not a controlled
speedup. Source-detail work preserves geometry distance and simulation behaviour;
the average still does not establish sustained smoothness or foreground completion.

## Palette-resource stalls and opacity passes (2026-09-23, 12:41 UTC)

The wide GL CPU sample found828/1,780 main-thread samples in the tiny world-palette
upload (825waiting in `finishResource`). Two fence-retired palette textures avoid
overwriting a texture still sampled by the prior world. A follow-up sample found
634samples in the equivalent UI-palette upload. The original UI driver now retains
full revisions across partial updates, uses frame-local palette textures and includes
the hardware cursor in consumer retirement. Counters `palette_upload_ms` and
`ui_palette_upload_ms` distinguish these costs from general submission/presentation.

The remaining GL path submitted opaque instances again in the translucent pass,
only to discard all their fragments. Shared-mesh pass partitioning removes that
redundant work. A reproduced Linux GL/Vulkan opacity-boundary error is corrected by
retaining unpartitioned order for whole mesh groups near0.99; shader alpha values,
cutoff and exact image comparisons are unchanged. See `VERIFICATION.md` for controls.

Same wide saved-title setup, M3 Pro, Classic/40bpp,2704×1756 fullscreen,(200,160),
rotation1/dolly5,unlimited distance;600running frames each:

| Artifact | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `gl-resident-bounded-wide-600` | 22.035 | 62.130ms | 71.464ms | 600 | 600 |
| `gl-frame-palette-wide-600` | 28.432 | 50.321ms | 60.882ms | 600 | 527 |
| `gl-ui-palette-wide-600` | 28.572 | 40.312ms | 60.089ms | 600 | 590 |
| **`gl-opacity-safe-wide-600`** | **50.834** | **25.762ms** | **28.495ms** | **600** | **178** |
| `vulkan-opacity-safe-wide-600` | 57.953 | 18.337ms | 27.460ms | 510 | 1 |

World-palette upload p95 fell to0.0105ms in the UI-ring checkpoint; presentation p95
fell16.687→1.181ms, exposing the remaining GPU wait/submission cost. The final split
preserves source geometry/materials and skips only otherwise-discarded instance
passes. Running-world content/timing varies with achieved frame rate; these are
matched setup checkpoints, not pixel-identical simulation traces. Wide60 remains open.

`gl-palette-opacity-cab-6000`, same operating aircraft4/secondary viewport,
2704×1756 fullscreen: **60.00255fps**,work p95 **9.60479ms**,max **37.70467ms**,
**16overruns /8intervals>20ms**. This improves the original CPU-composited40.151fps
case but still does not establish sustained smoothness. Foreground availability,
Windows/hardware coverage, cold capture/upload and original driver-stall cases remain.

## OpenGL resident composition checkpoint (2026-09-23, 11:36 UTC)

Interactive GL no longer reads entire viewport colour/ID images to the CPU and then
uploads their CPU-composited replacements. Original world targets and independent
IDs remain resident; original UI/palette shaders compose clipped regions on the GPU.
Only explicit screenshots/reference checks and requested picking pixels read back.
Cross-context presentation fences protect Cocoa texture reuse; an additional two-frame
completion ring prevents an unbounded GPU backlog from masquerading as fast CPU ticks.
Use `OPENTT3D_GL_PRESENTATION=0` / smoke `--readback-presentation` for a control.

M3 Pro, native OpenGL4.1 Metal, Classic/40bpp, fixed lens/unlimited distance:

| Artifact | Frames / size | FPS | Work p95 | Work max | Overruns | Intervals >20ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `gl-resident-airport-control-600` | 600 /2560×1600 | 60.196 | 17.274ms | 18.277ms | 74 | 0 |
| `gl-resident-airport-600` | 600 /2560×1600 | 60.002 | 6.241ms | 9.405ms | 0 | 0 |
| `gl-resident-aircraft-cab-control-6000` | 6000 /2704×1756 fullscreen | 40.151 | 30.635ms | 87.158ms | 6000 | 5687 |
| `gl-resident-aircraft-cab-6000` (before queue bound) | 6000 /2704×1756 fullscreen | 60.002 | 9.521ms | 28.511ms | 19 | 10 |
| **`gl-resident-bounded-cab-6000`** | 6000 /2704×1756 fullscreen | **59.948** | **10.003ms** | **40.045ms** | **63** | **34** |

Airport controls use the same held-aircraft save, radio32 focus, rotation1/dolly−1,
and identical submitted-vertex summary (mean538,207.52). Readback p95 falls11.161→0ms,
CPU composition3.152→0ms. The Cab uses aircraft4 and an independent vehicle-window
viewport. Its CPU control costs18.553ms readback and3.842ms composition at p95;
both are zero throughout the resident benchmark. Dynamic route/capture sequences
can differ because the slow control advances more simulation time over6,000frames.

Use the **bounded** result for current sustained evidence, not the earlier unbounded
measurement. Cold capture peaks15.607ms, mesh indexing6.709ms (inside upload7.060ms),
buffer/fence wait18.108ms and presentation16.391ms. Remaining63overruns mean smooth60
is still not achieved. No geometry/detail/draw-distance restriction was introduced.

Exact composition regression checks154,300 RGBA pixels including partial-alpha UI;
full-screen CPU/resident pairs match8,192,000 RGB pixels across both blitters. These
prove image correctness, not layer-display cadence. GL screenshots capture the GPU
composition texture before the hardware cursor. The native input probe saw
`loginwindow`; an earlier OpenChamber desktop query does not prove the full run was
foreground. Wide-world, foreground, Windows/hardware and cold-creation work remain.

The follow-up **`gl-resident-bounded-wide-600`** uses the running title at(200,160),
rotation1/dolly5,2704×1756 fullscreen. It still fails badly: **22.035fps**,work
p95 **62.130ms**,max71.464ms,600overruns/600intervals>20ms. GL backend submission
p95 is47.057ms (mean32.119),capture11.020ms,buffer wait0.714ms; readback/CPU
composition stay zero. Removing the copies does not resolve this wide-map
submission/geometry bottleneck. Vulkan's earlier58.204fps is a separate backend
checkpoint, not proof that the fallback meets the wide target.

## First voxel-aircraft flight checkpoint (2026-09-23)

`voxel-aircraft-cab-6000` uses the public-NoAI operating fixture, aircraft4/engine238,
now with its voxel body, actual Cab plus secondary viewport,2704×1756 fullscreen,
Classic/40bpp, M3 Pro/MoltenVK and unlimited distance. **60.002fps**,work p95
**9.417ms**,max **35.523ms**, **24work overruns /15intervals>20ms**. GPU p95
15.245ms/max34.872ms; resource wait peaks26.578ms, capture14.100ms and upload5.639ms
(indexing4.545ms).828 cached meshes/25buffers use101,214,972bytes,1,969,860source /
1,223,425stored vertices. Average60 does not establish sustained smoothness.

`voxel-aircraft-final-wing-opengl` is a different short airport workload at2560×1600,
300running frames:60.009fps,p9517.231ms,max18.710ms,31overruns/zerointervals>20ms.
It is not a controlled improvement over the earlier48.27fps pier workload. Revisit
the latter's full-image readback/CPU-composition bottleneck with matched controls.

## Hotel/civic and camera-precision checkpoint (2026-09-23)

The new public-NoAI aircraft route adds `voxel-aircraft-city-cab-1800`: aircraft4,
engine238, actual Cab plus secondary viewport,2704×1756 fullscreen, Classic/40bpp,
M3 Pro/MoltenVK and unlimited distance. **60.004fps**,work p95 **9.495ms**,max
**23.924ms**,five work overruns and two intervals>20ms. Its route, loading, altitude
and camera workload differ from the train fixture. It is operating-aircraft evidence,
not a controlled speedup or a sustained/hardware-complete60fps result.

The later airport-detail check `voxel-piers-refined-opengl`,2560×1600 windowed,
Classic/40bpp,300 running frames, still fails at **48.274fps**,work p95 **21.946ms**,
max23.358ms,300overruns and287intervals>20ms. Readback alone is **13.995ms p95** and
CPU composition **3.221ms p95**; mesh indexing/upload are zero at p95. This confirms
that the fallback presentation bottleneck remains after the new voxel details.
`voxel-radio-palette-corrected` is a short Vulkan correctness/animation workload
(300frames,60.013fps,p955.471ms,zerooverruns), not a sustained or all-hardware pass.

`hotel-precision-cab-6000` rechecks the same saved commuter-airport train0/secondary
viewport, Classic/40bpp, M3 Pro/MoltenVK,2704×1756 fullscreen and unlimited distance.
It averages **60.003fps**,work p95 **9.450ms**,maximum **67.048ms**, **16** work
overruns and **five** intervals>20ms. Cold capture peaks38.594ms, indexing19.860ms
(included in upload21.918ms), resource wait22.471ms and GPU29.151ms. Cache:
677meshes/18buffers,71,511,656 used bytes,1,262,100 source /869,940 stored vertices.
Source/stored vertex counts match the prior indexed Cab snapshot.

The desktop query returned **OpenChamber immediately before** this run. A subsequent
menu/input probe reported `loginwindow`, so the complete interval's foreground state
is not established. This is another measured checkpoint, not closure of the earlier
51.26fps foreground failure, historical queue stalls or sustained smoothness target.

Short actual city/palette checks,2560×1600 windowed,300frames:

| Artifact | Backend | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `voxel-civic-refined-review` | Vulkan | 59.987 | 5.633 ms | 6.153 ms | 0 | 0 |
| `voxel-hotel-water-native-opengl` | OpenGL | 60.334 | 19.024 ms | 23.795 ms | 61 | 10 |

The GL average masks repeated missed frame budgets. These workloads differ in
camera/content from the Cab and wide title. Linux llvmpipe water runs are correctness
checks, not hardware performance evidence. Model/camera work preserves the fixed
lens and original palette animation; no draw-distance restriction was introduced.

## Exact vertex indexing checkpoint (2026-09-23)

Immutable meshes now share bit-identical vertices, retaining all20 words of each
80-byte vertex and original triangle order. Palette/normal/UV/shadow seams and flat
provoking data are preserved. Vulkan and GL use16-bit indices when possible,32-bit
otherwise, and the original stream when indexing would not reduce storage. Set
`OPENTT3D_INDEXED_MESHES=0` at startup for an unindexed control. Vulkan stores vertex
and index slices in the same pooled or oversized buffer. `mesh_index_ms` measures
cold deduplication (also included in the inclusive mesh-upload timing); `mesh_cache`
reports indexed mesh count, source/stored vertices and index bytes.

Same wide workload as below: M3 Pro/MoltenVK, Classic/40bpp,2704×1756 fullscreen,
running title at(200,160),rotation1,zoom5,unlimited distance, desktop `loginwindow`.
The Cab uses the commuter-airport fixture, train0 and secondary viewport.

| Artifact | Frames | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `indexed-wide-control-600` (disabled) | 600 | 38.152 | 27.326 ms | 33.752 ms | 600 | 599 |
| `indexed-wide-600` (32-bit) | 600 | 57.497 | 18.414 ms | 26.927 ms | 556 | 1 |
| `indexed-short-wide-600` (16/32-bit) | 600 | 58.109 | 18.196 ms | 25.758 ms | 502 | 2 |
| `indexed-cull-wide-600` | 600 | 58.204 | 18.212 ms | 27.433 ms | 502 | 2 |
| `indexed-palette-fast-wide-600` (rejected shader) | 600 | 56.059 | 18.999 ms | 27.483 ms | 592 | 2 |
| `indexed-cab-6000` | 6000 | 60.002 | 9.290 ms | 38.017 ms | 34 | 20 |

The final wide cache holds1,269 meshes in34 buffers: **140,461,904 used /
142,606,336 capacity bytes**,1,208 indexed meshes, **3,851,007 source /1,659,809
stored vertices** and7,672,128 index bytes. The disabled control holds1,281 meshes
in75 buffers,311,897,040 used bytes and3,898,713 source/stored vertices. Running
content/cache sets differ slightly; these are workload checkpoints, not identical
static-memory attribution. Within the indexed snapshot, stored vertices fall56.9%.
Submitted triangle/index counts are unchanged. The paired static gallery matches
**592 images /252,057,600 RGBA pixels** exactly before the later brick-office art edit.

Palette-only batches also use raster backface culling, equivalent to their existing
fragment discard. Mixed sprite overlays retain unculled rendering. Its measured
standalone gain is negligible. A translation-only palette vertex-shader branch
passed correctness but ran slower; it was reverted in both backends and embedded
shaders regenerated. The current shader retains the original transform path.

The Cab cache holds677 meshes/18 buffers, **71,511,632 used bytes**,442 indexed
meshes and1,262,100 source /869,940 stored vertices. Cold indexing peaks at9.422ms;
GPU duration peaks34.221ms. Wide indexing peaks2.658ms,p950.075ms. Neither the near60
wide result nor the average60 Cab result establishes sustained smoothness. Foreground
51.26fps, historical queue-submit stalls, GL readback and the full hardware/zoom
matrix remain unresolved. Continue source-faithful geometry and cold-creation work.

## Foundation and distant-transport checkpoint (2026-09-23)

M3 Pro/MoltenVK, Classic/40bpp, 2704×1756 fullscreen, unlimited distance. The Cab
uses the same commuter-airport fixture/train0/secondary viewport; the wide workload
uses the running title at(200,160), rotation1, dolly5. The desktop is `loginwindow`.

| Artifact | Frames | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `voxel-foundation-cab-6000` | 6000 | 60.002 | 8.76 ms | 41.55 ms | 21 | 9 |
| `voxel-foundation-wide-600` | 600 | 35.761 | 29.19 ms | 35.48 ms | 600 | 600 |
| `voxel-foundation-wide-census` | 600 | 35.775 | 29.04 ms | 35.97 ms | 600 | 599 |
| `voxel-rail-distant-wide-600` | 600 | 37.779 | 27.80 ms | 34.02 ms | 600 | 599 |
| `voxel-transport-component-census` | 300 | 38.156 | 27.49 ms | 35.67 ms | 300 | 299 |

The Cab still has cold capture/upload and later resource waits: maximum capture
26.25ms, upload9.05ms, buffer wait28.44ms, GPU40.29ms. Its676 meshes occupy
**99,719,520 bytes in24 buffers**, versus97,638,240 before voxel foundations. The
average60fps does not establish sustained smoothness or resolve foreground failures.

The wide failure is predominantly GPU-bound: the first run submits **77.7M vertices**,
GPU p95 **29.11ms**, buffer-wait p95 **13.78ms**, capture p95 **8.85ms**. No interactive
readback or atlas repack occurs. Ownership counters in the follow-up attribute
**51.55M** vertices to railway tiles and19.55M to tree tiles; foundations contribute
only **0.266M** across owners. Tile ownership is not an exclusive component taxonomy:
rail tiles also contain fences, signals, ground and other structures.

Far flat straight tracks now use one-unit longitudinal cells, retaining the exact
quarter-unit gauge/cross-section and eighth-unit height grid. Graded/diagonal runs,
maglev junctions and closer detail keep their fine lattice. This reduces rail-owned
work to about **48.08M** and gives the modest improvement above, but remains far from
the target. Running-map timing/content can vary, so these are workload checkpoints,
not an isolated claim that every geometry difference comes from one change.

Benchmark reports now include `captured_vertices_by_owner`,
`captured_foundation_vertices`, `captured_fence_vertices` and
`captured_running_rail_vertices`. The last300-frame census measures **34.46M direct
running-track vertices**, **13.84M fence vertices**, **0.266M foundation vertices**
and about19.2M tree-owned vertices. Direct track counts exclude track embedded inside
other component assemblies. Ownership scanning runs only during a benchmark; no
simulation state is changed. Further mesh reuse/indexing and genuinely economical
distant transport/vegetation geometry remain priorities alongside cold creation,
foreground timing, the historical driver stall and GL readback.

## Voxel fence and gate consolidation checkpoint (2026-09-23)

Same saved commuter-airport fixture, moving train0 plus secondary viewport,
2704×1756 fullscreen, Classic/40bpp, unlimited distance, M3 Pro/MoltenVK:

| Artifact | Frames | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `voxel-fence-cab-sustained-6000` | 6000 | 60.003 | 9.32 ms | 32.34 ms | 3 | 3 |
| `voxel-fence-unified-cab-6000` | 6000 | 60.003 | 9.39 ms | 34.39 ms | 3 | 3 |

The foreground is again **`loginwindow`**, confirmed immediately after these runs.
They do not resolve or supersede the earlier available-desktop51.26fps failure.
The final run's three overruns occur consecutively during cold capture:14.63/27.04/
22.91ms capture and10.62/15.51/16.15MB uploaded. Normal capture p95 is1.00ms; no
interactive readback or atlas repack occurs. These remain actual visible-workload
spikes, not a sustained smoothness pass. Later frame-resource/driver stalls and the
GL presentation bottleneck still require separate investigation.

Both runs retain676meshes in23buffers: **97,638,240 used /97,665,024 capacity bytes**.
This is more memory than the earlier pre-voxel-fence fixture (about75MB), so broad
cache/geometry work remains. Gate consolidation makes no measurable difference to
this particular fixture's resident mesh total; no whole-scene speedup is claimed.

The isolated flat-gate audit in `voxel-fence-final-mesh-audit/run.log` measures the
actual local improvement: four edges use **4 instead of8 instances**, **39,960 vs
41,748 close vertices**, and **24,576 vs26,688 farther vertices** (about4.3%/7.9%
less vertex storage). One shared palette volume avoids the second full-volume build;
sloped railway sprite aliases also share their identical slope-keyed edge mesh.
Exact comparisons against partitioned geometry pass after correcting a genuine
coplanar cap-colour conflict. This local saving does not close the performance gate.

## Later available-desktop Cab failure (2026-09-22 evening)

After the native input probe passed on the available desktop,
`voxel-evening-cab-sustained-6000` rechecked the moving train/secondary viewport at
2704×1756 fullscreen, Classic/40bpp and unlimited distance. It measured **51.260 fps**,
work p95 **29.68 ms**, maximum **135.67 ms**, **3,508** work overruns and **1,953**
intervals above20 ms. Capture p95 is5.55 ms, presentation-upload p95 5.04 ms,
GPU duration p95 20.20 ms; the largest upload/presentation episode is68.42/74.61 ms.
The cache holds678 meshes in18 buffers (74,870,880 used bytes). These are later
desktop/runtime conditions and expanded content; the result establishes an open
performance failure, not a controlled attribution to one change. It remains a
priority alongside the earlier queue-submission stalls and GL readback bottleneck.

## Animated-airport checkpoint (2026-09-22)

Native M3 Pro, **2560×1600 windowed**, running city/country or larger airport review
fixtures, 600 frames. These are short isometric animation workloads, not the moving
Cab or all-zoom release matrix:

| Artifact | Backend | FPS | Work p95 | Work max | Work overruns |
| --- | --- | ---: | ---: | ---: | ---: |
| `voxel-radar-open-lattice-review` | Vulkan | 59.993 | 5.66 ms | 6.23 ms | 0 |
| `voxel-international-animation` | Vulkan | 60.002 | 5.58 ms | 6.38 ms | 0 |
| `voxel-intercontinental-animation` | Vulkan | 60.002 | 5.78 ms | 6.42 ms | 0 |
| `voxel-open-lattice-stock-reload` | OpenGL | 49.689 | 21.08 ms | 22.83 ms | 600 |

The GL reload spends **13.78 ms p95 in readback**, plus **3.10 ms in CPU composition**;
backend work including readback is14.90 ms p95. Mesh uploads are zero at p95. This
isolates a costly fallback presentation path, not a problem solved by the compact
voxel meshes. The Vulkan runs have no >20 ms intervals, but previous sustained Cab
failures and active-desktop/hardware coverage remain open. Linux llvmpipe animation
checks are correctness evidence (about1.07 fps), not hardware performance results.

## Voxel railway/airport checkpoint (2026-09-22)

M3 Pro/MoltenVK, **2704×1756 fullscreen**, Classic/40bpp, moving train 0 plus its
secondary viewport in `voxel-airport-fixture`, unlimited distance:

| Artifact | Frames | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `voxel-rail-cab-performance-600` | 600 | 60.007 | 10.60 ms | 41.44 ms | 2 | 2 |
| `voxel-rail-cab-bounded-mesh-600` | 600 | 59.998 | 9.12 ms | 15.62 ms | 0 | 0 |
| `voxel-rail-cab-sustained-6000` | 6000 | 60.002 | 9.06 ms | 33.31 ms | 25 | 12 |
| `voxel-compact-cab-sustained-6000` | 6000 | 60.002 | 9.17 ms | 39.61 ms | 30 | 11 |

The first run exposes cold capture/upload/resource waits. Voxel face scans now
restrict work to each material partition's occupied bounds while checking occlusion
against the complete grid. Electrified/conventional running meshes share a cache
entry. The later short run passes, but the longer run still exposes a cold frame
(11.35 ms capture, 12.01 MB uploaded) and later resource waits without new uploads.
Maximum buffer wait is **26.14 ms**, GPU duration **36.21 ms** and queue submission
**2.86 ms**. This run does not reproduce the historical one-second submission stall,
and does not prove it fixed. Sustained smoothness remains open.

The long run holds **675 meshes /18 buffers**, **72,594,720 used /75,497,472 capacity
bytes**. Broad all-layout GPU verification deliberately caches many more variants
(roughly 600 MB in the current validation run); this is not representative of that
moving fixture and remains a cache/memory optimization opportunity. The foreground
menu probe again reports the locked login window, so active manual-input performance
is not established by these measurements.

The compact-triangulation follow-up reduces the eight authored building volumes
from 70,468 to 62,564 triangles (11.2%) and also compacts railway material partitions.
Colour/shape-edge samples remain intact; exact old/new gallery comparisons pass.
This is a geometry reduction, **not a sustained-frame-time pass**. The later run
uses the same saved commuter-airport map with the expanded model catalogue; it holds
676 meshes, 74,588,640 used bytes in 18 buffers. Its cold frame includes 16.63 ms capture,
14.44 ms resource wait and 14.33 MB uploads. Later resource waits still occur without
new uploads; maximum wait 25.53 ms, GPU 35.79 ms, submission 5.14 ms. The larger content
and timing differences prevent treating this as a controlled overall speedup.

## Classic low-bridge Cab checkpoint

The current baseline is **OpenGFX2 Classic 0.8.1**. Earlier HighDef measurements below
retain their original artwork/workload scope. The new public-NoAI fixture adds an
observed bus journey under the minimum-height bridge; source pixels use native or
coarser levels and diagonal rail sweeps are now straight sections.

M3 Pro/MoltenVK, **2704×1756 fullscreen**, 40bpp, bus 3 in Cab with secondary viewport,
unlimited distance, 600 measured frames per run:

| Artifact | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `classic-underpass-cab-600` | 60.002 | 9.12 ms | 14.85 ms | 0 | 0 |
| `classic-underpass-material-final-600` | 60.002 | 8.69 ms | 13.89 ms | 0 | 0 |

The actual Cab passage and final underside material were inspected. These short
new-fixture runs do not resolve the earlier long queue-submission stalls or replace
the full moving/all-zoom/all-climate/hardware performance matrix.

## Shared GPU mesh storage and foreground checkpoint

Vulkan's immutable mesh cache now suballocates aligned slices from append-only
**4 MiB pages**, with larger dedicated pages for oversized meshes. Existing slices
retain their offsets through growth and remain alive until device-idle teardown.
The CPU mesh/instance data and draw order are preserved. The moving train fixture
holds **675 meshes in 13 buffers**, rather than 675 separate allocations: **52,389,600
bytes used / 54,525,952 bytes reserved**. Broad Linux GPU verification holds **3,602
meshes in 64 buffers**, including the explicit oversized-mesh regression.

Reports now include `mesh_upload_ms`, upload counts/bytes, `mesh_cache` usage, and
separate acquisition, UI-upload, queue-submit and queue-present timings. The A/B
control `OPENTT3D_MESH_POOL=0` uses individual buffers; `mesh_cache.pooled` records
the selected mode. Its exact-colour/picking verification also passes.

The native desktop became available again: `mesh-pool-native-input` passes all
32 focus/capture cycles and four fullscreen transitions. The following new runs
are therefore a later desktop-condition checkpoint, rather than a claim of a
like-for-like speedup over the earlier locked-desktop measurements. M3 Pro/MoltenVK,
**2704×1756 fullscreen**, 40bpp, moving train and secondary viewport, unlimited distance:

| Artifact | Frames | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mesh-pool-electric-cab-6000` | 6000 | 59.399 | 10.23 ms | 1048.25 ms | 11 | 5 |
| `mesh-pool-presentation-cab-6000` | 6000 | 59.418 | 10.20 ms | 1015.39 ms | 7 | 4 |
| `mesh-unpooled-control-cab-6000` | 6000 | 59.371 | 9.97 ms | 1014.93 ms | 31 | 19 |

The finer timing isolates the long stall to **vkQueueSubmit**: **1011.24 ms** in the
pooled run and **1006.70 ms** in the unpooled control. Neither stalled frame uploads
a new mesh. Removing pooling does not eliminate this submission stall; the driver/
presentation investigation remains open, along with occasional cold capture and
frame-resource waits. Allocation-count improvement is not a smoothness pass.

`mesh-pool-driver-profile/cpu-sample.txt` records a native 5 ms sampling pass. It
confirms that MoltenVK performs deferred `CAMetalLayer.nextDrawable` acquisition
inside queue submission. That diagnostic run did **not** reproduce the one-second
submission wait: its maximum was instead **137.23 ms**, including **133.14 ms** in
UI upload. Sampling changes timing, so it neither establishes the root cause of the
one-second stall nor replaces the uninstrumented results above.

`mesh-pool-wide-600` rechecks the paused title view at **(64,64), rotation 1, zoom 5**,
32bpp: **60.293 fps**, work p95 **15.675 ms**, max **16.613 ms**, zero work overruns or
>20 ms intervals. Longer moving/foreground and all-climate/hardware coverage remain.

## Turf and exact mip-family cache checkpoint

The latest terrain pass adds solid turf/pebbles/rough-ground details and adjusts
their projected-detail thresholds. Mature crop rows retain growth height at middle
distance without rendering unresolved stems or hidden internal caps. Cab diagnostics
showed sprite 1545 decoded separately at texture zooms 0…5, even though the upstream
loader already resolves all of them. Retaining the exact mip family within the
existing nominal 96 MiB source budget removes those repeated decodes.

M3 Pro/MoltenVK, **2704×1756 fullscreen**, 40bpp, latest NoAI traffic fixture, moving
Cab plus secondary viewport, unlimited distance:

| Artifact | Frames | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `clear-surface-crop-lod-cab` | 1800 | 60.002 | 10.17 ms | 21.81 ms | 5 | 3 |
| `mip-family-electric-cab-1800` | 1800 | 60.002 | 9.65 ms | 16.18 ms | 0 | 0 |
| `mip-family-bus-cab-1800` | 1800 | 60.002 | 9.70 ms | 14.81 ms | 0 | 0 |
| `mip-family-electric-cab-6000` | 6000 | 59.950 | 9.67 ms | 54.73 ms | 42 | 24 |
| `inactive-poll-electric-cab-6000` | 6000 | 60.002 | 7.41 ms | 23.50 ms | 1 | 1 |

The 1,800-frame train run reduces maximum source decoding from **8.06 ms to 2.23 ms**;
99% of measured frames have no source decode. No atlas repacks/readback occur.
The bus run also observes an actual same-tile crossing transition.

The longer train run is the important unresolved result. It exposes intermittent
presentation delays (maximum **43.29 ms**), frame-resource waits (**26.51 ms**) and
an unclassified main-loop delay (frame 1592), with GPU maximum **33.21 ms**. These
are not source-decoding stalls, and the successful shorter runs do not supersede
them. More sustained presentation profiling and broader hardware coverage remain.

A further input-loop review removed the WindowServer mouse-position query while
the application is inactive; the queried point was discarded immediately anyway.
The 6,000-frame follow-up retains one early capture/upload/resource-wait spike,
but maximum presentation time is **2.02 ms**, work p99 **8.19 ms**, source decode
maximum **1.55 ms**, and maximum frame-resource wait **6.28 ms**. This is a useful
improvement, not a claim that the sustained gate is closed. These native runs were
made while the foreground-input probe reported the locked login window; active
interactive playtesting and other release hardware remain required.

`clear-mips-wide-final-600` rechecks the paused (64,64), rotation-1, zoom-5 view:
**60.022 fps**, work p95 **14.94 ms**, max **15.26 ms**, zero work overruns or >20 ms
intervals. The all-dolly matrix in the preceding tree checkpoint below predates
the turf/mip-cache changes and retains its recorded scope.

## Component trees and profile-guided CPU checkpoint

All runs in this section use M3 Pro/MoltenVK, **2704×1756 fullscreen**, unlimited
distance and the new 62-family component tree pack. A paused title view centred at
**(64,64), rotation 1, zoom 5**, was measured for 600 frames after each change:

| Artifact | Vertices | FPS | Work p95 | Work >16.67 ms | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `tree-title-wide-600` | 35.52M | 53.335 | 19.89 ms | 600 | 27 |
| `tree-title-wide-lod-600` | 23.06M | 54.883 | 19.46 ms | 600 | 3 |
| `tree-title-hashed-cursor-600` | 23.06M | 60.064 | 14.62 ms | 0 | 0 |

Tree LOD switches at 12/32 projected pixels and drops unresolved twigs/ribs. It
retains actual volume geometry at unlimited distance. A five-second native CPU
sample (`tree-title-cpu-profile/cpu-sample.txt`) then found two avoidable costs:
AppKit was reinstalling the arrow cursor on every inactive poll, rebuilding its
accessibility images, and instance staging was doing ordered-map lookup for every
record. Cursor release is now idempotent; hash lookup and sorting only distinct
active meshes preserve the original draw order. Final work max **15.34 ms**,
GPU p95 **12.48 ms**, no atlas repack or readback. This view differs from the older
running (200,160) wide benchmark below.

### Running title: all exposed dolly levels

`tree-running-zoom-{level}` uses **(200,160), rotation 1**, 300 measured frames per
level, with the simulation running. Every level averages **59.99–60.05 fps**, and
there are **zero intervals above 20 ms** across all 3,600 frames.

| Dolly | Work p95 | Work max | Work overruns |
| ---: | ---: | ---: | ---: |
| −6 | 5.40 ms | 5.96 ms | 0 |
| −5 | 5.28 ms | 6.92 ms | 0 |
| −4 | 4.88 ms | 6.12 ms | 0 |
| −3 | 4.90 ms | 7.06 ms | 0 |
| −2 | 5.53 ms | 8.14 ms | 0 |
| −1 | 5.54 ms | 5.87 ms | 0 |
| 0 | 6.29 ms | 6.76 ms | 0 |
| 1 | 7.35 ms | 8.86 ms | 0 |
| 2 | 7.33 ms | 9.66 ms | 0 |
| 3 | 9.84 ms | 11.86 ms | 0 |
| 4 | 12.17 ms | 15.38 ms | 0 |
| 5 | 14.68 ms | 16.87 ms | 1 |

`tree-low-pitch-600` exercises the released 3° orbit, **60.002 fps**, work p95
**5.88 ms**, maximum **8.95 ms**, zero work overruns or >20 ms intervals.

### Moving Cab: tails still present

The latest public-NoAI fixture, 40bpp, moving vehicles and two viewports:

| Artifact | Frames | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `tree-electric-cab-1800` | 1800 | 60.002 | 9.28 ms | 29.75 ms | 7 | 3 |
| `tree-bus-cab-1200` | 1200 | 60.003 | 9.08 ms | 22.93 ms | 1 | 1 |

The train run peaks at **10.77M vertices**, source decode **8.75 ms**, GPU frame
**31.88 ms** and frame-resource wait **22.76 ms**. Both cold-source work and occasional
GPU-heavy views still produce stalls, despite the normal frame headroom. No atlas
repacks or interactive readback occurred. These results do not close the complete
smooth-frame-time gate or the broader map/climate/hardware matrix.

## Volume road-stop Cab checkpoint

`build-macos/road-stop-bus-cab-1200` adds modeled bus/truck stops to the active
crossing layout. M3 Pro/MoltenVK, **2704×1756 fullscreen**, 1,200 moving-bus frames,
two viewports, unlimited distance, an observed same-tile crossing state change.

- **60.001 fps**; work p95 **9.54 ms**, p99 **10.69 ms**, max **17.98 ms**.
- **1/1200** work overrun, **zero** intervals over 20 ms.
- GPU p95 **9.62 ms**, p99 **12.44 ms**; mean **2.46M**, max **4.61M vertices**.
- Five atlas pages, no repacks or interactive readback. Maximum source decode
  **7.64 ms**, maximum capture **9.50 ms**. Cold-source work remains a spike source.
- The actual Cab screenshot was inspected: canopy tops/undersides, posts, curbs
  and slatted seats now have volume. Unfinished vegetation/materials are still visible.

## Active crossing and bus-Cab checkpoint

The newer NoAI layout has a bus route across the active railway between stations.
Both runs below use M3 Pro/MoltenVK, **2704×1756 fullscreen**, 1,200 frames, a moving
bus and secondary viewport, unlimited distance, latest depots/crossings and material
refinements. Five atlas pages, no repacks or interactive readback; mean **2.40M**
vertices and maximum **4.51M**.

| Artifact | FPS | Work p95 | Work max | Work overruns | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `active-crossing-bus-cab` | 60.002 | 10.60 ms | 19.41 ms | 1 | 0 |
| `crossing-transition-trace` | 59.999 | 9.12 ms | 21.03 ms | 1 | 1 |

The second run adds a bounded diagnostic proving one actual crossing changes state.
Its worst decode is **9.30 ms**, maximum capture **11.17 ms**, and GPU p95 **9.53 ms**.
Rare cold-source stalls remain. The Cab screenshot clearly exposes remaining flat
bus-stop shelters and unfinished tree materials; those require the next art pass.

## Electric railway and station checkpoint

`build-macos/electric-rail-cab-1800`: M3 Pro/MoltenVK, **2704×1756 fullscreen**,
1,800 frames, unlimited distance, moving electric locomotive and secondary viewport.
Includes the latest stations/roof hangers, signal mechanisms/catenary, ground details,
component materials and tile picking. This is a new authored NoAI review layout,
not a like-for-like comparison with the earlier dense title-map workload.

- **60.003 fps**; work p95 **9.81 ms**, p99 **10.66 ms**, max **32.71 ms**.
- **3/1800** work overruns; **2** intervals over 20 ms.
- GPU p95 **11.11 ms**, p99 **12.16 ms**, max **33.03 ms**.
- Mean capture **0.57 ms**, max **10.85 ms**; maximum buffer wait **22.12 ms**.
- Five atlas pages, no repacks, zero interactive readback. Source decode max **7.44 ms**.
- Mean **1.57M vertices**, maximum **4.79M**, two viewport passes.
- The actual presentation was inspected inside the electric tunnel with its exit
  visible. The save had first been re-saved by official OpenTTD 15.3.

This fixture passes average refresh but still has rare stalls. It does not settle
the earlier dense-wide/cold-atlas findings or the full zoom/climate/hardware matrix.
The Linux/Xvfb llvmpipe validation journey is correctness evidence, not native
performance evidence (its software-rendered 120-frame run averaged about 4.31 fps).

## Tunnel/track and fixed-lens checkpoint

These runs include the fixed 40° world lens, new fences/foundations, tunnel interiors
and 3D plain track. M3 Pro/MoltenVK, **2704×1756 fullscreen**, running title fixture,
unlimited draw distance. Prior matrices below predate this content and lens.
These measurements precede the subsequent station and raised-ground-detail passes.

- `build-macos/rail-tunnel-cab-1800`: starts following an actual underground road
  vehicle, then follows its exit and outside travel with a secondary viewport.
  **60.001 fps**, work p95 **14.95 ms**, p99 **15.85 ms**, max **45.60 ms**.
  **9/1800** work overruns and **2** intervals above 20 ms. The worst frame includes
  a **15.48 ms atlas repack** and **10.79 ms backend** work. This run precedes the
  fence-LOD and instance-staging changes below.

The same wide view (`--center 200 160 --zoom 5 --rotation 1`) was remeasured for
600 frames after each optimization:

| Checkpoint | Mean vertices | FPS | Work p95 | Work >16.67 ms | Intervals >20 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rail-wide-600` | 20.69 million | 56.735 | 19.09 ms | 600 | 3 |
| `rail-wide-fence-lod-600` | 12.60 million | 57.414 | 18.87 ms | 599 | 1 |
| `rail-wide-pooled-600` | 12.60 million | 60.055 | 17.48 ms | 260 | 0 |

Far fence variants drop subpixel diamond-wire faces and simplify crown sections,
while retaining volume posts/rails and the original close geometry. This reduces
submitted geometry by about **39%** without a distance cutoff. CPU capture remains
about **8.22 ms** in this view. Reusable count/prefix/scatter instance staging removes
per-mesh temporary record vectors and stream recopying; mean backend time drops
from **3.57 ms to 2.62 ms**, with stable submission ordering and exact GPU checks.

Average refresh recovery does **not** close the smooth-frame-time gate: 260/600 work
samples still exceed budget, moving-view repacks still stall, and all camera levels,
climates, complete content and release hardware still need sustained measurements.

## Bridge geometry checkpoint

After the 40-industry material expansion and initial volumetric bridge integration,
the running title fixture was measured again on M3 Pro/MoltenVK. The display now
reports **2704×1756 fullscreen**, so this is not a like-for-like speed comparison
with the 3024×1964 checkpoint below. Draw distance remains unlimited.

| Zoom | Work p95 | GPU p95 | Work overruns |
| ---: | ---: | ---: | ---: |
| −3 | 5.56 ms | 3.03 ms | 0 |
| −2 | 5.69 ms | 3.62 ms | 0 |
| −1 | 5.86 ms | 4.61 ms | 0 |
| 0 | 5.66 ms | 6.47 ms | 0 |
| 1 | 7.03 ms | 7.85 ms | 0 |
| 2 | 7.14 ms | 10.09 ms | 0 |
| 3 | 7.21 ms | 8.80 ms | 0 |
| 4 | 10.75 ms | 6.37 ms | 0 |
| 5 | 12.74 ms | 12.23 ms | 0 |

Each run contains 300 measured frames after warm-up, averages about 60 fps, and
has no interval above 20 ms. Artifacts: `build-macos/bridge-zoom-{level}/`.

`build-macos/bridge-cab-1800/` contains the 1800-frame moving Cab run with 40bpp
animation and a secondary viewport: **60.004 fps**, work p95 **11.08 ms**, p99
**13.27 ms**, maximum **36.38 ms**. **8/1800** work samples exceed 16.67 ms and
**6 intervals** exceed 20 ms. The slow-frame records identify four repacks
(12–16 ms each) and a later burst of source decoding (up to 10.12 ms).
Smooth moving-camera frame times and complete-content performance remain open.

### Reused atlas storage

The next pass reuses CPU atlas-page buffers across compaction and page eviction.
It retains the existing source-plus-destination repack high-water storage, bounded
by **48 CPU pages / 288 MiB**, instead of repeatedly allocating/zeroing/freeing it.
GPU residency remains 24 pages; the decoded-source cache remains 96 MiB. Texture
rectangles overwrite their texels and clear/copy their gutters before upload;
three consecutive GPU relocation checks preserve colour and picking exactly.

`build-macos/bridge-cab-pooled-1800/`, at the same 2704×1756 size, reports
**60.011 fps**, work p95 **11.26 ms**, p99 **13.64 ms**, maximum **32.23 ms**.
The four repacks take **12.38, 14.15, 7.60 and 12.48 ms**. There are still
**7/1800** work overruns and **7 intervals** above 20 ms; source decoding still
reaches **10.09 ms**. This reduces allocation churn but does not close the
smooth-frame-time gate. The fixed-view matrix above predates this storage-only pass.

## Unlimited-distance and tilt update

The fixed first-person distance cutoff is removed rather than increased. Geometry,
terrain, labels and picking use the full map/view frustum; the projection has no
far plane. This makes the moving Cab substantially heavier than earlier results.

Earlier fixed-camera matrix, running title fixture, Vulkan/M3 Pro,
**3024×1964 fullscreen**, 300 measured frames per integer zoom:

| Zoom | Work p95 | GPU p95 | Work overruns |
| ---: | ---: | ---: | ---: |
| −3 | 5.43 ms | 3.64 ms | 0 |
| −2 | 6.18 ms | 4.33 ms | 0 |
| −1 | 6.09 ms | 5.05 ms | 0 |
| 0 | 6.56 ms | 5.41 ms | 0 |
| 1 | 5.63 ms | 4.98 ms | 0 |
| 2 | 6.94 ms | 8.84 ms | 0 |
| 3 | 8.70 ms | 10.20 ms | 0 |
| 4 | 15.15 ms | 8.79 ms | 0 |
| 5 | 13.93 ms | 7.19 ms | 0 |

Artifacts: `build-macos/unlimited-zoom-{level}/`. Each averages about 60 fps and
has no interval above 20 ms. The 600-frame 3°-pitch orbit run in
`orbit-low-pitch-perf/` reports **60.002 fps**, work p95 **7.73 ms**, maximum
**8.88 ms**, with no work-budget overruns.
These measurements precede the subsequent industry-material expansion; final
complete-content performance must still be measured after the asset work.

### Unlimited moving Cab: still open

`build-macos/cab-unlimited-fast-repack/` measures 1800 frames with 40bpp animation,
the moving Cab and a secondary vehicle viewport: **60.027 fps** average, work
p95 **14.47 ms**, p99 **16.86 ms**, maximum **32.90 ms**. **22/1800** work samples
exceed 16.67 ms and **11 intervals** exceed 20 ms. These outliers are not hidden by
the average; complete smooth-frame-time coverage is unfinished.

- Initial unlimited Cab measurement (`cab-unlimited-perf-1800`) was **59.08 fps**,
  with **275/1800** work overruns and a **118.80 ms** maximum.
- Frame reuse now compares the actual 3D camera rather than legacy follow-scroll
  coordinates, cutting duplicate rendering from up to four passes to two.
- A separate bounded **96 MiB** LRU source cache retains decoded/padded textures
  across GPU-atlas eviction; company palette variants share source pixels.
- Repacking uses height-sorted shelves, then seeds the normal rectangle allocator
  with its empty areas. This avoids quadratic general packing for a bulk rebuild.
- An incremental free-area reclamation experiment (`cab-unlimited-reclaim`) made
  allocation fragmentation and stalls worse; that implementation was removed.
  It is not the current algorithm or a passing performance result.

Reports now include texture-decode and atlas-repack timings. Removing the remaining
loading/compaction tails, scaling to larger maps and complete-content play-throughs
remain active work. Earlier performance sections retain their original limited-
distance configuration and must not be treated as unlimited-Cab evidence.

## Vehicle geometry update: 3024×1964

The current display backing size is **3024×1964**. After adding directional
vehicle geometry and sprite-local atlas sampling, the running title fixture was
measured again for 300 frames per integer zoom:

| Zoom | Work p95 | GPU p95 | Work samples over 16.67 ms |
| ---: | ---: | ---: | ---: |
| −3 | 5.37 ms | 3.24 ms | 0 |
| −2 | 5.95 ms | 4.25 ms | 0 |
| −1 | 5.51 ms | 4.92 ms | 0 |
| 0 | 5.76 ms | 5.94 ms | 0 |
| 1 | 7.52 ms | 6.25 ms | 0 |
| 2 | 7.03 ms | 9.08 ms | 0 |
| 3 | 8.72 ms | 9.53 ms | 0 |
| 4 | 13.21 ms | 7.96 ms | 0 |
| 5 | 14.50 ms | 6.93 ms | 0 |

All average **59.98–60.01 fps**. Valid artifacts:
`build-macos/vehicle-zoom--{3,2,1}/`, `vehicle-zoom-0/` and
`vehicle-zoom-dpi-{1..5}/`. The original `vehicle-zoom-1` run is invalid zoom-1
evidence: the harness caught GUI/DPI scaling changing its zoom to zero. The 3D
camera is now independent of that legacy integer-zoom adjustment.

`build-macos/vehicle-cab-long-local-uv/` is the latest 1800-frame running Cab test
with 40bpp animation and overlapping viewports: **60.000 fps**, work p95 **10.64 ms**,
p99 **12.34 ms**, maximum **22.39 ms**. Four work samples exceed 16.67 ms and two
intervals exceed 20 ms. The 600-frame `vehicle-fullscreen-cab` check had no work
overruns, illustrating why the longer test is needed. Rare moving-view tails and
complete-content/hardware coverage remain open.

## Current Vulkan results

Apple M3 Pro, MoltenVK 1.4.2, running `media/baseset/opntitle.dat`, **2704×1756
fullscreen**, 60 Hz requested, 30 warm-up frames followed by 300 measured frames
per integer zoom. All runs average approximately **60 fps**, with **zero work
samples above 16.67 ms and zero intervals above 20 ms** in this fixed-camera matrix.

| Effective zoom | Frame work p95 | GPU frame p95 |
| ---: | ---: | ---: |
| −3 | 5.47 ms | 4.97 ms |
| −2 | 5.55 ms | 5.09 ms |
| −1 | 4.93 ms | 4.30 ms |
| 0 | 5.82 ms | 7.10 ms |
| 1 | 6.31 ms | 10.23 ms |
| 2 | 6.45 ms | 9.20 ms |
| 3 | 7.27 ms | 8.53 ms |
| 4 | 9.47 ms | 6.43 ms |
| 5 | 12.11 ms | 6.61 ms |

Artifacts: `build-macos/vulkan-zoom-matrix-{0..5}/benchmark.json` and
`build-macos/vulkan-zoom-signed--{1..3}/benchmark.json`. The earlier negative-zoom
`vulkan-zoom-matrix--*` runs are invalid: console parsing rejected signed values
and left the camera at zoom 3. Both parsing and the harness's zoom assertion are fixed.
A separate 600-frame rotated zoom-5 run also reports 60 fps with no budget overruns:
`build-macos/vulkan-fullscreen-rotated-z5/`.

### Moving first-person view: remaining frame-time tails

Latest 1800-frame fullscreen run with a moving train, secondary viewports, 40bpp
palette animation and normal game UI:
`build-macos/vulkan-cab-live-atlas-1800/benchmark.json`.

- **60.002 fps** average; frame work mean **7.49 ms**, p95 **10.68 ms**, p99 **13.23 ms**.
- GPU timestamp p95 **8.49 ms**, p99 **10.47 ms**; no interactive full-image readback.
- **5/1800** work samples exceed 16.67 ms; **one interval exceeds 20 ms**, maximum
  **21.86 ms**. Smooth-frame-time coverage is therefore still an open release gate.
- Earlier moving-view repacks produced 80–102 ms stalls. Rectangle packing,
  retaining only recently used texels during relocation and bounded dirty uploads
  substantially reduced them. Exception-safe restoration also fixed a retry
  assertion inside a sprite-combine block.

The backend now uses persistent immutable terrain/model meshes, GPU instance
records, conservative frustum culling, distance-appropriate curved-mesh
tessellation, reusable CPU capture storage, GPU world/UI composition, and
one-pixel picking readback. A widest-zoom intermediate run submitted 32.7M
vertices at 35 fps; LOD reduced this to 10.6M, and terrain instancing reduced
capture time from 22.7 ms to roughly 6.3 ms, bringing that fixture to 60 fps.

The fixed-camera matrix predates the final atlas-packing refinements. Broader
maps/climates, continuous camera motion, release hardware and longer play-throughs
remain to be measured. Artwork remains incomplete, so the matrix is not a final
complete-content performance certification.

## Measured baseline

Apple M3 Pro, macOS 26.6.2, OpenGL 4.1; title-game fixture, paused, 2560×1600
backing resolution, requested refresh rate 60, 120 measured frames after 30 warm-up
frames. Artifact: `build-macos/perf-before-camera/benchmark.json`.

| Measurement | Mean | p95 |
| --- | ---: | ---: |
| Frame work | 41.24 ms | 45.40 ms |
| Scene capture | 14.45 ms | 14.76 ms |
| Backend, including readback | 20.53 ms | 24.56 ms |
| GPU readback | 12.48 ms | 16.53 ms |
| CPU pixel composition | 2.99 ms | 3.18 ms |

Measured throughput: **24.24 fps**. Geometry submitted: **1,551,930 vertices/frame**.
All 120 measured frames exceeded the 16.67 ms work budget. This predates the
calibrated pinhole camera and the corrected instant-centre smoke command, so use
the recorded fixture/view for historical context rather than treating it as an
identical-view comparison with newer captures.

### Historical dense-view fullscreen baseline

`build-macos/perf-borderless-fullscreen/benchmark.json` measures the running title
fixture after the camera/control changes, explicitly centred on tile 64,64:

- **2704×1756**, confirmed fullscreen, effective zoom 1, 60 measured frames.
- **9.28 fps**; mean frame work **107.69 ms**, p95 **112.52 ms**.
- Capture **52.70 ms**, backend including readback **48.18 ms**, readback
  **20.73 ms**, CPU composition **3.47 ms**.
- Approximately **5.71 million vertices/frame**. Every measured frame misses
  the 16.67 ms budget.

This is a denser, different view than the earlier baseline, not a controlled
before/after speed comparison. It establishes the scale of work still required.
`perf-fullscreen-before-vulkan` did **not** stay in fullscreen and
`perf-fullscreen-settled` timed out waiting for it; neither is valid fullscreen
evidence. Cocoa now uses synchronous borderless fullscreen for game-controlled
entry, restoring window style/frame and application presentation options on exit.
The harness waits for the requested mode and a stable backing size, then captures
the screenshot after measurement rather than during the transition.

The historical interactive path rebuilt geometry, uploaded it, read back full colour
and ID buffers, and copied colour back into the CPU UI framebuffer each frame.
This describes the historical OpenGL path. The Vulkan implementation above removes
interactive full-image readback and adds shared meshes, instancing and LOD.

## Vulkan runtime

MoltenVK **v1.4.2** is pinned by SHA-256 in `upstream.json` and fetched into the
build directory by `tools/opentt3d/fetch_vulkan.py`. No host-wide Vulkan installation
is required. The native probe successfully reports:

```
Apple M3 Pro: Vulkan 1.1.357, graphics=yes, texture=16384, array layers=2048
```

The game now has a native `cocoa-vulkan` backend and an SDL `sdl-vulkan` backend.
Both pass scene and live-presentation checks; the container also runs Khronos
core/synchronization validation. OpenGL remains available as a fallback.

When directly linking MoltenVK, `VK_KHR_portability_enumeration` may be absent
because it is a loader extension. Query supported instance extensions rather than
unconditionally enabling it. The probe does this.

```sh
python3 tools/opentt3d/fetch_vulkan.py build-macos/vulkan
clang++ -std=c++20 tools/opentt3d/vulkan_probe.cpp \
  -Ibuild-macos/vulkan/MoltenVK/MoltenVK/include \
  -Lbuild-macos/vulkan/MoltenVK/MoltenVK/dylib/macOS -lMoltenVK \
  -Wl,-rpath,@executable_path/vulkan/MoltenVK/MoltenVK/dylib/macOS \
  -o build-macos/vulkan-probe
MVK_CONFIG_LOG_LEVEL=1 build-macos/vulkan-probe
```

## Repeatable measurements

Use fresh output directories and run benchmarks without a concurrent build.
`benchmark.json` records actual backing resolution, fullscreen state, effective
zoom, view coordinates, API/device, interval/work percentiles and hot-path costs.
Vulkan GPU timestamps are consumed after normal frame-fence completion, two frames
later, without a profiling-only wait. CPU work, GPU execution and draw-loop
intervals are distinct measurements. Reports also include buffer/game-lock waits,
inclusive window drawing, presentation time and individual slow-frame records.

```sh
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --output build-macos/benchmark-windowed --backend vulkan --savegame media/baseset/opntitle.dat \
  --zoom 1 --running --benchmark-frames 240 --timeout 180
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --output build-macos/benchmark-fullscreen --backend vulkan --savegame media/baseset/opntitle.dat \
  --fullscreen --zoom 1 --running --benchmark-frames 240 --timeout 180
```

Repeat for effective zooms -3 through 5, near/far dense towns, infrastructure,
moving fleets, continuous orbit, first-person following, and overlapping vehicle
windows. Inspect p95/p99 and sustained frame intervals, not just average fps. Mesa
software rendering is a correctness test, not evidence of hardware performance.

# Model quality ledger

The target is **every runtime asset genuinely 3D, detailed and consistent, with
every model at least 8/10**. It is not yet met. A model count, successful build or
source export does not establish visual quality or whole-world coverage.

`MODEL_RATINGS.csv` records every compiled voxel model, retained reference profile,
permitted active tree profile and procedural family. Missing original object/HQ
layers and lock walls are listed individually, including climate and state. The
JSON report also retains the original family/state inventory and intentional body
and climate absences; absent bodies do not excuse raised artwork in ground layers.
Procedural families still need expansion/review of every slope, layout and state.
Uncatalogued disasters and river variants remain explicit coverage gaps.

## Individual unbound lock study rejections

`reviews/20261003/lock-studies-rejected/` retains all 48 original wall-owner studies
separately: 28 structural rejections at 5/10, twenty provisional 6/10, zero approvals
and six false acceptance checks per model. Front architectural profiles and obscured
lamp panes are explicit defects. The lamp-opening candidate invalidates eight prior
reviews. All 48 native pairs match, but eight street views fail strict renderer
equality by one pixel each; native equality cannot replace the wider rejection.

The unbound lock + rejected HQ scope has 1,963 models/2,978 ledger entries, with
189 individual records in the first freeze or 181 current/eight stale records after
the lamp edit. It remains separate from canonical 1,831-model assets and `.42`.
Required-eight still fails; no runtime lock substitution or inherited approval.

## Original water states remain in both quality scopes

`reviews/20261003/water-quality-scope/` retains 544 separate original wall/water/
conditional bank states: 192 missing structural lock owners, 96 independent water
owners, sixteen default slope/climate surfaces and 240 unresolved river-bank/climate
selectors. Conditional absence does not license an invented bank, and static IDs
or live source captures do not establish model fidelity or animation coverage.

The unchanged 1,831-model/canonical-review scope has 2,846 ledger entries and 57
individual records; the separately rejected 1,915-model HQ scope has 2,930/141.
Both required-eight checks correctly fail, with zero approvals and four coverage
gaps. Working asset 247 and isolated committed-artwork/compiler asset 231 tests
pass. Matching inventories, reports and LF CSVs are hash-bound; no runtime artwork,
bindings, canonical reviews or `.42` package changes.

## October 3 — rejected larger HQs; original water inventory

`reviews/20261003/hq-larger-rejected/` retains84 individually inspected prototype
owners, each bound to exact artwork and its own source/native/four-orbit/four-street
sheet:73 provisional6/10 and11 structural rejections5/10. Missing large-east walls,
foreign Toyland gate/tower fragments, coarse architecture/paint and absent natural
size2…4/all-climate world/state evidence prevent approval. All six acceptance checks
remain false. The separately merged1,915-model working ledger has2,578 entries/141
individual records and zero8/10 approvals; required-eight correctly fails. The
source/compiler/test copies in this review directory are quarantined snapshots,
not runtime asset changes. Recommended`.42`remains its immutable1,831-model release.

`reviews/20261003/water-original-sources/` preserves208 exact paired original lock/
water images from eight quiet exact-tag `.42` runs. The new read-only source inventory
retains48 default lock wall layers, four slopes, sixty unresolved custom river edge
offsets and original absent-bank semantics. Working assets235 and independently
isolated committed-artwork assets219 pass. Neither static sources nor tests establish
live feature selection, 3D lock/river coverage, ship clearance or visual ratings.

## Rating rules

- **1:** missing structural coverage or original sprite fallback.
- **3–5:** conservative structural screening only; not a visual judgement.
- **6–7:** individually inspected, with remaining defects or acceptance gaps.
- **8:** individual source, orbit, street, world, state and consistency checks pass.
- **9–10:** stronger individually evidenced fidelity and detail.

Unreviewed artwork cannot receive 8. An 8-or-higher entry requires all six checks,
no unresolved defects and SHA-256 hashes for every evidence file. Cell placement,
dimensions and all six palette faces are fingerprinted independently of material
ID renumbering. Edited models or overwritten evidence invalidate prior ratings.
Quick-pass ratings do not confer final original-art visual approval.

## October 3 HQ owner review

The current1,831-model catalogue adds32 individually inspected original ground
owners for HQ sizes0/1/four climates. Each has its own registered source/native,
four orbit and four street views, exact cell/six-face fingerprint and immutable
portable-sheet hash. All score6/10: coarse source grain/roof/masonry/checker detail,
natural upgraded-world evidence, wider backend differences and owner LOD review
remain explicit defects. The north cottage/turret/flag now retain their source
owner without shrinking the disjoint joined compound; absent bodies stay absent.

The2,494-entry ledger retains57 individual reviews:40 at6/10 and17 at7/10.
Other scores are1×276,3×183,4×159 and5×1,819, including32 newly bound source-state
instances that do not inherit their model's score. All1,799 preceding authored
models/material faces/bindings stay exact. Forty owner/joined sheets and eight
natural size0 world captures are retained in`reviews/20261003/hq-source-owner-planes/`.
Native-source and state/world consistency are not approved;`--require-eight`
still fails. The historical25-review/1,799-model figures below describe the prior
increment and the immutable recommended`.40`, not this newer working catalogue.

## Reproduce against the exact reviewed build

```sh
python3 tools/assets/inventory.py \
  --catalogue build-macos/baseset/opentt3d-voxels.json \
  --output build-macos/current-original-state-inventory.json
python3 tools/assets/quality_audit.py \
  --catalogue build-macos/baseset/opentt3d-voxels.json \
  --inventory build-macos/current-original-state-inventory.json \
  --output build-macos/current-model-quality.json \
  --csv opentt3d/MODEL_RATINGS.csv --require-eight
```

The final command deliberately fails while coverage or ratings remain incomplete.
`assets/3d/quality_reviews.json` holds individual review decisions, not automatic
promotions. The native `renderer3d voxel-overview [prefix]` command, exposed by
`smoke.py --gallery-voxel-overview`, produces smaller orbit/street previews while
retaining the registered source-scale studies and full joined context. Previews
support catalogue breadth; they are not enough by themselves to approve detail.

## October 3 consistency pass

Road-stop slabs now sample the original full-tile road chart at the same native
texture scale as adjoining roads, rather than repeating a tiny crop. Both bank
cupolas are centred on their joined roofs and partitioned across the original
tile owners. Twelve authored canal-edge volumes retain the original side/convex/
concave selection and independent animated water.

The first canal integration passed isolated galleries but did **not** reach the
live world: Classic resolves its dikes to dynamic base-set IDs. Those controls
remain preserved. The corrected selector recognises audited original provenance
without claiming coverage for custom replacement graphics; the harness now
requires explicit live dike evidence. The resolved climate soil strips retain
their original pixels, palette animation and registration beneath XYZ masonry.
That palette-specific partition is limited to the reviewed Classic set; alternate
base sets, RGB artwork and custom/partial families retain their complete source.
An ordinary dry island exposes all twelve original edge variants in every climate
and both backends, while actual ships still complete both dock calls. This does
not establish full fleet-volume clearance or source/artwork approval. Lock walls
remain uncovered; detailed all-angle/native canal fidelity remains under review.

The first **25 individual reviews** are retained with portable image evidence in
`reviews/20261003/`: seventeen at7/10 and eight at6/10. Five corrected object
candidates add13 supported-climate bindings, without claiming HQ coverage or
promoting their original source-state instances. The current2,462-entry ledger
has scores1×308,3×183,4×159,5×1,787,6×8 and7×17. Scores below6 are conservative
screening/missing-coverage entries, not individual aesthetic inspection. No entry
has been promoted to8. Full catalogue capture coverage is1,799 native studies and
14,392 orbit/street views in57 sheets, plus joined contexts. Exact prior model/face
fingerprints allow reuse of preserved captures; availability is not approval.
Strict bank backend comparisons retain24 differing wider views/3,152 pixels in
each200-view climate set and zero native differences. Those failed exact-equality
reports remain evidence, not hidden tolerances or passed quality checks.

Four source sheets/climate sets and the flat/sloped, real-town-action and landmark
worlds support the five object reviews. Shape/pose/source-paint and wider backend
defects remain explicit. Every supported beacon/lamp control observes all four
unmodified original palette phases from one object; fallback controls preserve
complete source families. These technical gates do not grant8/10 acceptance.

The desktop release`.40`is independently audited and recommended. Its1,799-model
catalogue includes the road/canal/bank increment and five original object volumes,
but not the newer two-stage HQ candidates. Publication does not change the25
individual sub-eight reviews or grant complete artwork/state/performance approval.

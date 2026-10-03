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

The desktop release`.39`is independently audited and recommended. Its1,794-model
catalogue includes the road/canal/bank increment, not the later object candidates.

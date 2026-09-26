# OpenTT3D development preview: source-correct industry climate layers

The expanded climate audit compares **323 original layer pairs /623,286 RGBA
pixels**. It identifies missing snowy Arctic forest variants and independently
painted climate grounds while confirming which existing body aliases are valid.

## Corrections

- Arctic forest16/17 retains its supplied snowy body and ground until independent
  voxel variants are authored. Temperate pine artwork cannot stand in for snow.
- Industry soil3924 and oil-well ground2173 retain the active climate's supplied
  layer outside temperate. Their voxel bodies retain independent ownership where
  the original body is unchanged.
- The existing Arctic farm correction remains. Inventory reports these missing
  climate variants explicitly, and diagnostic native/joined exports respect scope.
- All107 compared coal/power/refinery/oil-well body pairs and all32 food-processing
  pairs are byte-identical.153 of the323 total layer pairs differ; original imagery,
  hashes and previous invalid-alias evidence remain preserved.

## Verification

- **198 native tests** and the presentation-boundary check pass. The unchanged
  artwork catalogue retains its117 passing compiler/schema tests.
- New public Arctic/tropical well fixtures complete all four construction snapshots.
- All six climate/backend industry matrices pass:3,320 views in temperate and2,168
  in Arctic/tropical, rejecting144 unsupported climate-layer bindings while keeping
  the unchanged voxel well body above the supplied climate ground.
- All eight actual Arctic forest stage captures pass with supplied snowy artwork
  and no temperate voxel alias. Source/context sheets were inspected.
- Maximum sampled memory across these focused matrices is **2,651,393,264bytes**.

### Follow-up on the same renderer/artwork

All ten tunnel railtype/Toyland backend cases and both18,000-frame moving-Cab runs
pass. Their240 tunnel comparisons preserve55,296,000 exact RGBA/picking pixels;
peak sampled memory is2,962,001,184bytes. Moving-Cab rates average57.588/59.898fps,
but missed deadlines and a1.07-secondGL work stall remain; smooth60fps is not met.
The tunnel-tree filter stays opt-in. Current Linux/shardedCI remains unfinished.

This remains a **1,247-volume development source prerelease with zero final visual
approvals**. Catalogue completion, fine source fidelity, independent Arctic art,
cross-backend differences, production memory and smooth60fps remain unfinished.
The previous tunnel-tree optimization remains opt-in; remoteCI shards are pending.

# OpenTT3D development preview: climate correction and tunnel visibility controls

This corrective source prerelease retains **1,247 authored volumes** and **zero final
visual approvals**. Full catalogue coverage, fidelity and smooth60fps remain unfinished.

## Included progress

- Corrected an invalid Arctic farm alias:40/44 source layers differ from temperate,
  including a different farmhouse structure. The renderer now keeps supplied Arctic
  ground/body artwork until independent voxel variants exist. Legacy profiles cannot
  silently substitute the temperate structure either. Inventory records the missing
  Arctic coverage, and the eight earlier Arctic captures are explicitly revoked as
  source-fidelity evidence.
- Linux Vulkan verification now requires one complete scene job and four disjoint
  vehicle-engine jobs covering0…255. Every climate/cargo/livery/heading/pitch/rotor
  comparison remains required. The ordinary local verifier still runs everything.
- An **opt-in** tunnel-tree filter conservatively retains the bore and both infinite
  mouth cones. Matched native dense-Cab samples improve from11.40/12.73 to38.11/40.33fps
  onGL/Vulkan while preserving exact images. It is disabled by default.

## Verified evidence

- **198 native tests,117 artwork/compiler tests and9 harness tests** pass.
- Both local scene-scope controls pass, including full model/tree/industry checks,
  selected complete train/helicopter matrices and exact world-atlas/picking.
- All16 farm-state reruns pass; actual Arctic capture has no temperate voxel bindings,
  and both backend verifiers reject all44 unsupported climate-layer bindings.
- Both backends pass20 actual tunnel mouth/interior/exit/four-heading/tiltedCab views,
  each comparing4,608,000 exact RGBA/picking pixels with full capture. Vehicle gameplay
  state is unchanged; peak sampled memory is3,636,104,768bytes.
- All20 loaded-route train support observations now pass. Both backends observe all
  six oil-well pump bodies and helicopter254's120 oil-rig deck-support corners plus
  every original rotor state and stopped-to-running transition.

## Open work

Current industry coverage is54/175 body definitions plus58 grounds, with farm33…38
temperate-only. Airports cover21/74 definitions plus3 independent grounds. Complete
climate/state/catalogue coverage, source-painted fidelity, swept-rotor clearances,
cross-backend pixel differences, arbitrary-world memory and all-day interactive
performance remain open. The new remote Linux shards have not yet completed.
Even the improved tunnel sample still has every frame interval above20ms.

The work window continues through **2026-09-26 19:00:00 UTC**.

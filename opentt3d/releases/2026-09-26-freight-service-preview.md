# OpenTT3D development source preview — freight service verification

This incomplete source prerelease retains the **1,169-volume** forest/refinery
catalogue and adds ordinary public-NoAI freight-service fixtures. Final visual
approvals remain zero; complete artwork and production performance remain unfinished.

## Verified progress

- A real bubble truck supplies the Toyland fizzy-drinks factory. Wagon52 loads25/25
  units, unloads at an accepting town and returns. Both hidden native renderers
  capture its actual full/empty bindings and pass exact atlas/picking checks.
- Five freight routes cover conventional steam, electric, monorail, maglev and
  Toyland service. Each crosses a real bridge and tunnel both fully loaded and empty,
  delivers accepted cargo and returns. Construction, orders and save/load use public
  APIs without changes to simulation or its random-number stream.
- The frozen1,169-volume full nativeGL/Vulkan matrices each complete28,056 model
  views,322,048 vehicle poses,10,880 collector poses,384 rotor poses and exact
  world-atlas/picking. Sampled peaks are5.37/5.49GiB, below the6GiB guard.
- The fixture harness passes8 tests and the134-file presentation-boundary check.

## Continuing work

The larger LinuxVulkan CI workload still exceeds6GiB; its tunnel-root check passes.
A matching native workload reproduces the memory failure. Train slope/contact and
complete contextual clearances are under review. Remaining industry, airport, tram
depot and infrastructure coverage, source-painted fidelity, all-day memory and
sustained smooth60fps remain open. See the detailed verification/performance ledgers.

# OpenTT3D development source preview — forest and refinery

This incomplete source prerelease contains **1,169 explicitly authored voxel
volumes**, adding six forest and nineteen refinery volumes. Industry coverage is
**21/175 body definitions with24 independent grounds**. All256 original vehicles,
110 house definitions and62 tree families retain their existing bindings. Final
visual approvals remain zero.

## Verified progress

- Forest16/17 preserves four nine-pine growth volumes, felled logs/stumps and
  independent full-tile litter. Both native backends observe one unchanged industry
  tile dispatch wood, show completed logs and pass through every original regrowth
  stage during9,000 running frames. The real forest-to-sawmill service loads20units,
  delivers and returns using ordinary public NoAI commands.
- Refinery18…23 adds hollow steel vessels, pipe/cross-braced process frames, three
  flare platforms, the completed flame, cooler and L-shaped office. All24 real
  construction-state body/ground selections pass. Construction soil and completed
  paving retain separate ownership; occupied footprints stay inside their tiles.
- Both backends pass144 forest /456 refinery mesh views,1,352 industry views and
  exact4,096,000-pixel world-atlas/picking checks. Native190/190, asset/compiler108/108
  and harness8/8 tests pass, together with the presentation-boundary check.
- Native source exports now include complete tall/overhanging industry silhouettes
  and explicit tile-origin registration sidecars. Source and street review findings
  remain recorded for later structural/material fidelity work.
- LinuxVulkan confirms the earlier tree-root tunnel repair:243,629 unobstructed
  lining pixels and unchanged vehicle state. Its later full catalogue matrix hits
  the6GiB guard. A follow-up fence-safe upload-retirement change passes increasing
  transient-payload, exact rendering and immutable-cache ownership checks natively;
  complete1,169 native and Linux memory validation remains in progress.

## Continuing work

Catalogue-wide coverage, source-painted shading, final proportions and all-angle
fidelity remain unfinished. Oil-rig/remaining industries, airports, tram depots and
other infrastructure still need voxel coverage. Train slope/curve wheel contact,
contextual clearances, fizzy-drinks supply/delivery, remaining actual-state checks,
Linux renderer completion, Windows runtime and portable packaging remain open.
The forest runs average60fps but retain650…669 presentation intervals over20ms;
sustained smooth arbitrary-world60fps and all-day memory are not established.

Checks use hidden inactive macOS windows and the6GiB sampled-memory guard. Source
art is manually inspected; geometry is explicitly authored, never generated from
images. See `VERIFICATION.md`, `VOXEL_REVIEW.md`, `VOXEL_PASSES.md` and `PERFORMANCE.md`.

# Larger-HQ 3D world review

The three larger-HQ sizes were rendered in actual saved worlds:

- size 2: medium ground/body owners and joined 2x2 compound.
- size 3: large owners.
- size 4: huge owners.

Each native Vulkan run retained a real `smoke-state.sav`, ordered console
acknowledgements, the exact synchronous save-success line and a 1280x960 world
screenshot. The logs observe all four HQ parts and the separate body owners.
The model changes are bound; the joined buildings are coherent in the world.

## Important limit

The HQ stage was set in the isolated fixture by a temporary review-only console
command (`debug_hq_frame`), which is **not** part of the committed command set.
These saves therefore prove 3D owner placement/rendering at each stage, not a
naturally selected company-score size. Natural size 2-4 selection remains an
open runtime gate.

The joined-world review accepts the 76 larger-HQ models and 84 owner instances at
9/10 for visible structure, placement, source ownership and joined consistency.
The previous isolated-owner 6/10 findings remain in git history. Natural company-
score stage selection remains an open runtime gate; it is not inferred from the
forced fixture.

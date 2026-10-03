# Retained combined-ledger arithmetic failure

The initial sealing script expected 1,979 models after adding 48 unbound lock studies
to the 1,915-model rejected HQ catalogue. The actual disjoint union has **1,963**
models. Its assertion correctly stopped before writing any combined catalogue,
inventory, ratings or quality report; the raw study/evidence bytes are unchanged.

Retain the failing script and traceback. Validate exact disjoint model sets, derive
the union count, and retain unchanged prior fingerprints/bindings. Previously
copied portable files may be reused only when byte-exact; mismatches still abort.
The correct quality-ledger total remains 2,978 because the earlier 2,930-entry
scope includes original-state/reference rows, not only authored models. No model
is omitted, no state is approved and no `.42` package is changed by this repair.

# Retained offline slope-guard rejection

The original callback studies and saved worlds retain correct slope enums. A later
offline validation hardening initially used screen-order corner values rather than
the original `Slope` bits W=1, S=2, E=4, N=8. Synthetic tests using the same wrong
values passed, but reconciliation against the actual source observations rejected
the new guard with `Live original lock slope differs from its saved state`.

The rejected tool/test snapshots and synthetic test log remain in
`breadth-original-lock-slope-guard-rejected/`. No runtime binary, fixture, selected
source, sprite, map, slope, assertion tolerance or existing verification was changed.
The guard is corrected to NE=12, SE=6, SW=3, NW=9 and an independent test resolves
the original enum bits from `src/slope_type.h` rather than trusting shared constants.
Reconcile all actual states in both backends again before sealing this tool.

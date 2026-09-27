# Original-aircraft review fixture

`fixture_aircraft.py` runs a headless dedicated game with a normal NoAI company.
The AI builds two intercontinental airports and selected original aircraft, assigns
normal orders, observes each aircraft's first destination service, then releases it.
The saved world contains ordinary operating aircraft and can be opened interactively
or with `smoke.py --background --ai-dir <fixture>/ai --reference-vehicle <engine>`.

The manifest requires positive observed speed, completed destination service and all
aircraft outside their hangars. Loaded/empty artwork equality, all-angle geometry,
company/crash palettes, source dimensions and airport/Cab clearance require separate
renderer reviews. The fixture uses public settings and NoAI commands only.

For helicopter stop/restart review use `--service-hold-ticks 256`. The saved AI keeps
the first full-load service order, waits256 ordinary ticks after reload, then clears
that order's full-load flag. This gives the simulation enough dwell time to stop its
rotor before normal departure. Stage that fixture's own `ai/` directory on reload;
`smoke.py --running --verify-helicopter-rotor <engine> --benchmark-frames 3600`
requires all four actually captured source states on one helicopter.

For the original elevated heliport, use `--airport-type 6 --destination-airport-type 2`
with a climate-compatible helicopter. The origin helidepot supplies the hangar and
the destination's original landing datum remains 60 units above its terrain. For
example, `--first-engine 254 --last-engine 254 --service-hold-ticks 256` retains an
ordinary held destination service for skid/deck contact and rotor restart review.

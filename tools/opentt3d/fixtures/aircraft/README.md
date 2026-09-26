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

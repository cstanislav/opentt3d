# Public ship-catalogue fixture

The driver creates an isolated2050,128×128 world with normal never-expire-vehicles
and construction-rate settings. The NoAI script borrows funds, levels a clear site,
lowers a canal bed, builds the canal through public commands, builds two sloped-bank
docks and a two-tile ship depot, and operates each selected climate-available ship.

```sh
python3 tools/opentt3d/fixture_ship.py \
  --build-dir build-macos --output build-macos/my-ship-review \
  --climate temperate --first-engine 204 --last-engine 214
```

Use a fresh output directory. Readiness requires every selected ship to move at
positive speed at least eight tiles from its depot and actually enter loading state
near **both** docks. Temporary ordinary full-load orders hold each first arrival
long enough to observe; the script then restores ordinary orders. This avoids
missing empty-station visits between observation ticks. It never sets cargo, vehicle,
construction, map or save-format state bytes.

`fixture.json` records actual engine/vehicle IDs, peak speeds, dock observations,
harbour coordinates and water height. The paused save is `save/ship-catalogue.sav`.
Reload with this fixture's own AI directory so its saved identity/built flag is retained:

```sh
python3 tools/opentt3d/smoke.py \
  --build-dir build-macos --output build-macos/my-ship-capture \
  --savegame build-macos/my-ship-review/save/ship-catalogue.sav \
  --ai-dir build-macos/my-ship-review/ai --reference-vehicle 204
```

For recurring depot-entry/exit observation, add `--depot-service`. `--depot-axis 0|1`
selects the normal orientation at construction time. The optional third order is an
ordinary non-halting depot visit, so it repeats after the two dock calls. It changes
neither hidden-state handling nor movement simulation. `fixture.json` records both
choices. For example, use engine212 on axis0 and hovercraft208 on axis1, then reload:

```sh
python3 tools/opentt3d/smoke.py \
  --build-dir build-macos --output build-macos/my-ship-depot-traversal \
  --savegame build-macos/my-ship-review/save/ship-catalogue.sav \
  --ai-dir build-macos/my-ship-review/ai --reference-ship-depot 0 \
  --first-person 0 --verify-depot-traversal 0 --running --benchmark-frames 6000
```

The renderer observer requires a visible ship, its original hidden/depot state with
actual voxel depot emission, and its visible departure. It never sends depot orders.
Slow software rendering can miss a non-halting service visit between captured frames.
For repeatable observation there, create a new fixture with `--depot-service
--depot-hold-ticks 64`: the normal order stops the ship, then the NoAI script waits
64 ticks and uses `AIVehicle.StartStopVehicle` to resume it. This ordinary stop/restart
loop is restored on reload; it never writes hidden-state bytes or extends a renderer
state artificially. Retain the original missed-observation artifacts separately.
The asset regression separately checks both axis joins and the swept cross-sections
of all six original ship bodies in both travel directions.

The harbour proves operation and dock arrival, not cargo production/delivery or all
bridge/lock/depot clearances. Its first failed variants and failed-world saves are
retained for diagnosis. Unavailable engines in the chosen climate are not fabricated.

`--all-dock-directions` adds normal north/south-bank docks and records `extra_docks`.
These additional structures provide the other original bank/water orientations for
artwork capture; the service still visits the original west/east pair.
`--dock-hold` retains the final full-load order after observing that arrival, giving
a real paused mooring state. Use one selected engine for an uncluttered view. It is
separate from recurring depot service; no cargo is created and no state bytes are set.

## Original buoy waypoint review

`fixture_ship.py --buoy-waypoint` adds a public `AIMarine.BuildBuoy` marker and an
ordinary waypoint order after the two dock calls. Readiness requires each selected
ship to occupy the actual buoy tile at positive speed after its waypoint order has
become active. The manifest records the tile and each `buoy_visited` observation.
This option cannot be combined with `--dock-hold`, which would prevent reaching the
later order. Reload with the fixture's own `ai/`; AI version6 preserves normal saves.
Use `smoke.py --reference-buoy --verify-buoy-beacon --running --benchmark-frames 600
--blitter 40bpp-anim` for actual voxel capture and original lamp/foam palette phases.

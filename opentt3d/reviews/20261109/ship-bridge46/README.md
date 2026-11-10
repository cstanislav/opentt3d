# `.46` real bridge ship-clearance fixture

This review adds a real, public-command road bridge across the existing canal
harbour and records ships crossing and holding beneath its span. It does not
alter simulation, construction, map, save-format or renderer bytes; the bridge,
buoys, docks, depot and vehicles are all built by ordinary NoAI commands.

## Fixture construction

`fixture_ship.py --bridge` builds a **Tubular road bridge** with
`AIBridge.BuildBridge(AIVehicle.VT_ROAD, ...)` after the canal is dug:

- north bridge head `(x+15,y+1)` and south bridge head `(x+15,y+15)`;
- the span crosses the east-west canal perpendicularly, so a ship travelling
  west/east passes under the deck instead of following it;
- both bridge heads and both approach-road tiles are on the untouched flat
  plateau outside the lowered canal rectangle;
- an ordinary buoy at `(x+15,y+7)` is placed below the span, and every ship
  receives a normal waypoint order for it;
- readiness requires the ship to be observed at positive speed in the bridge
  row and within two tiles of the under-span buoy, with `bridge_under_span`
  recorded individually.

`fixture_ship.py --bridge --bridge-hold --bridge-hold-engine <engine>` then
waits until that selected ship is inside the span and issues the ordinary
`AIVehicle.StartStopVehicle` command. The saved world keeps the ship under the
bridge for a low-angle renderer review.

## Direct runs

All four climates used engines `204…214` and completed both docks plus the
under-bridge buoy:

| climate | bridge head | buoy | engines under span |
| --- | --- | --- | --- |
| temperate | `(55,25)` / tile `3255` | `(55,31)` / tile `4023` | 204,205,206,207,208,211,212 |
| arctic | `(39,25)` / tile `3239` | `(39,31)` / tile `4007` | 204,205,206,207,208,211,212 |
| tropic | `(71,25)` / tile `3271` | `(71,31)` / tile `4039` | 204,205,206,207,208,211,212 |
| toyland | `(55,25)` / tile `3255` | `(55,31)` / tile `4023` | 209,210,213,214 |

Every listed engine has `bridge_under_span: true` and `bridge_min_distance`
`0` or `1`; the union covers all eleven ship definitions `204…214`. Raw
fixtures, saves, scripts, AI and logs are under `climates/`.

## Held hull reviews

`held/<engine>/` contains an independent single-engine world where that hull was
held under the span at tile `4023` `(55,31)`. All eleven runs have
`bridge_held: true` and preserve the actual engine and held tile.

`views/<engine>.png` is the saved world captured by `smoke.py` with
`--reference-bridge --zoom -1 --orbit-drag 1 -200`, which lowers the camera to
about 14.6° pitch. The bridge renderer reports 61 volumetric bridge parts in
those views (72 in the wider bridge capture `bridge-view/`). Visual inspection
of all eleven images shows the hull and its masts/cranes below the deck and
between the support columns; no ship geometry is above the deck. The four
rotations for engine208 are retained under `views/held-208-rotations/`.

This closes a real **bridge navigation and held visual-clearance** control for
all eleven ship definitions in the four climates. It is one heading per hull
and this one road-bridge type; a complete all-heading/all-bridge-type swept
matrix is not claimed.

The saved worlds are deterministic `2050` worlds with `vehicle_breakdowns=0`;
the fixture does not write cargo, vehicle, construction, map or save-format
state bytes.

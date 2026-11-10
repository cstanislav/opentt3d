# `.46` short-span bridge ship-clearance fixture

This review completes the **vanilla road-bridge type matrix** for the bridge
ship control. The wide-harbour fixture covers the six types that support the
15-tile crossing; this fixture covers the seven remaining types on a real
2- or 3-tile-wide canal.

## Construction

`fixture_ship_short.py` uses an ordinary public-NoAI company. It levels a
30×20 plateau, builds the exact requested road bridge on the flat site, then
digs the narrow canal beneath the completed bridge. Sloped west/east banks
receive the same ordinary `SLOPE_NE`/`SLOPE_SW` dock orientations as the wide
harbour. A water depot and an under-bridge buoy are then added, and engine204
runs between the two docks and through that buoy. Readiness requires positive
movement, both dock calls and a direct under-span observation; `--bridge-hold`
stops the ship below the deck for the saved view.

## Covered types

| type | width | bridge | bridge parts in view | under span | held |
| --- | --- | --- | --- | --- | --- |
| 1 | 2 | Concrete road bridge | 10 | yes | yes |
| 2 | 2 | Steel girder road bridge | 10 | yes | yes |
| 9 | 2 | Steel girder road bridge | 10 | yes | yes |
| 3 | 3 | Reinforced concrete suspension road bridge | 14 | yes | yes |
| 6 | 3 | Steel cantilever road bridge | 12 | yes | yes |
| 7 | 3 | Steel cantilever road bridge | 12 | yes | yes |
| 8 | 3 | Steel cantilever road bridge | 12 | yes | yes |

Each type directory retains `fixture.json`, the actual save, AI/scripts, the
fixture log and a low-pitch `view/` renderer log/result/screenshot. The
screenshots show engine204 below the deck; the buoy is an ordinary in-world
marker and the bridge deck remains above the ship.

Together with `../ship-bridge46/`, this covers **all 13 vanilla road-bridge
types** (types 0, 4, 5, 10, 11 and 12 on the 15-tile harbour; types 1, 2, 3, 6,
7, 8 and 9 on the narrow canal). The wide-harbour control exercises all eleven
ship definitions; this short-span control uses engine204. Heading coverage is
still the ordinary east/west route under a north/south bridge, not an
all-heading sweep.

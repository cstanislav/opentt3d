# Short-span bridge ship fixture

This fixture tests the vanilla bridge types that cannot span the 15-tile
harbour crossing used by `fixtures/ship`.

The NoAI company levels a 30×20 plateau, builds a real short road bridge on the
still-flat site, digs a **2- or 3-tile-wide** canal beneath the existing span,
adds ordinary sloped-bank docks and a water depot, places an under-bridge buoy,
and runs selected ships between the docks and through the buoy. The bank tiles
receive the same `SLOPE_NE`/`SLOPE_SW` dock orientations as the retained wide
harbour. Readiness requires both dock calls, positive speed and a direct
under-span observation; `--bridge-hold` stops the selected ship below the
bridge for a saved low-angle view.

Use `--canal-width 2` for the concrete/girder types and width 3 for the longer
cantilever types. The retained matrix covers all seven remaining vanilla road
bridge types; the wide-harbour fixture covers the six 15-tile types.

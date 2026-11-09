# `.46` ship fixture controls

The direct fixture uses a natural temperate dock layout and Vulkan/native
public-NoAI ship commands. The original seven ships (engines 204–212) each
visited both main docks three times, with actual peak speeds and a saved world
(`fixture.json`, `save/ship-catalogue.sav`).

The **expanded** control adds the two ordinary off-axis docks (four dock
orientations), a real navigation buoy, a dry dike island inside the harbour and
a recurring depot-service order. All seven ships again visited both loading
docks three times and passed within four tiles of the actual buoy; the dike
island and depot are present in `expanded/save/ship-catalogue.sav`. The 3D view
of that saved world shows all seven ships, four docks and the buoy, with 64
picking samples and a synchronous save.

The earlier exact-tile buoy control is retained as
`expanded/rejected-exact-buoy-timeout.log`: all ships had already docked and
moved, but the observer required equality with the buoy tile and timed out.
That observation method was rejected; the model/world was not changed to make
the test pass. The corrected control samples normal proximity to the buoy.

This does **not** prove bridge/swept-clearance for every ship hull at every
heading, nor all 23 ship source sprites in every climate. Those remain separate.

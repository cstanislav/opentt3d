# Public road-family review fixture

`fixture_road.py` creates an isolated2050,128×128 world using normal game settings
and public NoAI commands. It borrows funds, levels a buildable site, builds a road
loop/depot and separate bus/truck stops, buys the climate-available engines in the
requested inclusive range, and gives each vehicle two ordinary orders.

```sh
python3 tools/opentt3d/fixture_road.py \
  --build-dir build-macos --output build-macos/my-road-review \
  --climate toyland --first-engine 129 --last-engine 203
```

Use a fresh output directory. The normal `never_expire_vehicles` setting exposes old
and new vanilla models together. Readiness requires **every selected available
vehicle** to leave the depot, travel at least four tiles from it and reach positive
speed. `fixture.json` records actual engine/vehicle IDs and peak speeds; the paused
world is `save/road-catalogue.sav`. Failures retain logs and, when possible, a failed
world save. The script never writes map, cargo, vehicle or save-format state bytes.

Reload with the fixture's own AI directory:

```sh
python3 tools/opentt3d/smoke.py \
  --build-dir build-macos --output build-macos/my-road-capture \
  --savegame build-macos/my-road-review/save/road-catalogue.sav \
  --ai-dir build-macos/my-road-review/ai --reference-vehicle 129
```

The AI saves its `built` flag and does not rebuild on reload. A fleet can contain
unconverted models; presence in the fixture is not voxel coverage. Movement readiness
does not establish cargo loading/delivery, every road/depot transition or clearance.
Those require separate gameplay observations. Use `--verify-voxel-poses ENGINE` for
synthetic company/crash/cargo/heading comparisons and `--reference-vehicle ENGINE`
for read-only location plus actual voxel emission.

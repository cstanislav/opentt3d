# Industry construction fixture

Run from the repository root with a built game and the pinned Classic base set:

```sh
python3 tools/opentt3d/fixture_industry.py --build-dir build-macos \
  --output build-macos/mine-construction-review --industry 0
```

This isolated world (temperate/1970 by default, selectable with `--climate`/`--year`) enables the ordinary manual-primary-industry
construction setting. A NoAI company takes an ordinary loan, levels a buildable
site and funds the requested industry through public commands. Original type0 is
the coal mine. Other requested types must be available/buildable in this climate.

The harness pauses and saves at0,16,30 and44 calendar days after funding. The AI
does not read or alter construction bytes. Review must independently establish
the actual stage in each save, for example:

```sh
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --output build-macos/mine-construction-stage1 --backend vulkan \
  --savegame build-macos/mine-construction-review/save/industry-day-16.sav \
  --ai-dir build-macos/mine-construction-review/ai \
  --reference-industry 2 1 --verify-industries --verify-tile-picking --brief
```

Always retain the fixture's own `ai/` directory with its saves. Reloaded scripts
remain idle rather than funding another industry. `fixture.json` records actual
industry/type/location, elapsed days and script ticks; these are observations,
not a substitute for the renderer's actual construction-state checks. Failed
worlds/logs are retained separately. The same saves can be opened by stock15.3.

## Actual coal service and winding animation

Add `--coal-service` for type0. After the four snapshots, the AI funds a power
station, builds a normal road/depot/two truck stops and requires the delivery
catchment to accept at least8/8 coal. An available coal truck must load real cargo,
deliver it and return before `save/industry-service.sav` is accepted. The manifest
records its engine, cargo, station IDs, peak load/speed and actual acceptance.

Use `--truck-engine 124 --year 2050` or engine125 to review later coal trucks. A
selected engine enables the normal never-expire setting, but NoAI still requires
that exact engine to be available and carry the mine's real coal. The harness checks
the observed engine ID and actual capacity; current124/125 fixtures load25/28 units,
deliver and return. The default automatic1970 selection is retained when no engine
is specified. Stage the corresponding fixture's own AI directory on every reload.

```sh
python3 tools/opentt3d/fixture_industry.py --build-dir build-macos \
  --output build-macos/mine-service-review --coal-service --timeout 420
python3 tools/opentt3d/smoke.py --build-dir build-macos \
  --output build-macos/mine-service-animation --backend vulkan \
  --savegame build-macos/mine-service-review/save/industry-service.sav \
  --ai-dir build-macos/mine-service-review/ai --reference-industry 2 3 \
  --running --verify-industry-animation 1 --benchmark-frames 6000 \
  --fullscreen --blitter 40bpp-anim --timeout 300 --brief
```

The renderer observes distinct original sprites on one actual tile. It does not
set animation frames or force production. The duplicate fourth original table
slot is not counted as another attainable animation frame.

Use `--cargo-snapshots` with `--coal-service` to also save
`industry-cargo-full.sav` and `industry-cargo-empty.sav`. These retain the actual
truck at capacity and after delivery. Review them with `--reference-vehicle 123
--reference-cargo full` or `--reference-cargo empty`; the smoke harness checks the
live amount and matching emitted voxel state, rather than trusting the save name.
For a running check, `--verify-voxel-cargo 123 --running --benchmark-frames 6000`
requires both actual amounts on one rendered vehicle without changing its cargo.

`--depot-directions` requires a coal or generic cargo service. It clears only trees on the
isolated buildable review site using public demolition commands, builds all four
road-depot exits and checks their actual front tiles. The truck's ordinary orders
then include depot maintenance on every delivery loop. An explicit entry/stop/exit
is also required before readiness. `fixture.json` records the verified exits.

Review each with `--reference-voxel-depot 4 --reference-depot-direction 0`…`3`.
For rendered traversal, use `--verify-depot-traversal 0 --running
--benchmark-frames 6000`: the observer requires a visible vehicle, its real in-depot
state while that voxel depot is drawn, then the visible vehicle again. It issues no
orders and never changes vehicle state. Slower software rendering may need the full
observation window; a shorter run without all events is not a pass.

## Other original cargo and climates

`--cargo-service --destination-industry N` selects another real producer/acceptor
pair. For example, this normal Toyland route carries sugar from type36 to type27:

```sh
python3 tools/opentt3d/fixture_industry.py --build-dir build-macos \
  --output build-macos/toy-sugar-service-review --climate toyland --industry 36 \
  --cargo-service --destination-industry 27 --truck-engine 174 --year 2050 \
  --cargo-snapshots --depot-directions --timeout 480
```

The selected engine must be available and carry a cargo actually produced by the
funded source. The destination must accept that cargo. Public tile queries locate
the actual south edge of each industry so small producers and differently shaped
factories have adjacent, in-catchment stops rather than fixed coal-layout coordinates.
Pickup production, delivery acceptance, actual loading/delivery/return and optional
depot entry/exit are required. No cargo, production, construction or map state is set.
Generic results use `cargo_service`; the existing `--coal-service` command retains
its `coal_service` manifest key and default coal-mine/power-station selection.

Current sugar174 and cola177 (`--industry 29 --destination-industry 33`) fixtures
each observe0/17 and17/17, accepted delivery, return and all four depot exits. A
new default-climate coal123 regression observes0/20 and20/20 after the generalized
layout selection. These are scoped service checks, not evidence for every cargo.

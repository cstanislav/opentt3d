# Original wagon consist fixture

For an ordinary train-breakdown emitter, add`--vehicle-breakdowns 2 --wait-breakdown`
to a moving, non-cargo fixture. After the verified return journey, NoAI only observes
the original scheduled failure while the train is still moving and saves that state.
It never assigns breakdowns/effects, changes reliability or servicing, or draws RNG.
Difficulty0 remains the default for all existing fixtures. Keep the matching`ai/`
directory with the save. Use`--low-effect-id`for a normal released pool slot before the
train; read the actual emitter from`fixture.json`and audit captured countdowns with
`tools/opentt3d/breakdown_smoke_cycle.py`. The smoke artwork may still be staged.

From the repository root, with the built game and pinned Classic base set:

```sh
python3 tools/opentt3d/fixture_train.py --build-dir build-macos \
  --output build-macos/train-catalogue-review --climate temperate --rail-type 1 \
  --locomotive 23 --first-engine 27 --last-engine 53 --hold
```

A normal2050/never-expire world uses public NoAI loans, terrain levelling, rail,
depot/station construction, vehicle building, wagon attachment and orders. The AI
selects only original available wagons in the requested range that can run on the
selected railtype. Each attachment is checked through the public consist engine
list. The whole train must move at positive speed to the far station and return.
Optional `--hold` uses a normal stop command after that verified journey.

Railtypes are0 conventional,1 electric,2 monorail,3 maglev. Use0 for Arctic/tropical/
Toyland conventional locomotives; original electric locomotives are temperate-only.
Regular wagons occupy27…53, monorail57…83 and maglev89…115. A range can contain
unconverted artwork; that does not count as voxel coverage.

`fixture.json` records actual locomotive, attached wagon IDs/positions, speed and
journey/held observations. Reload `save/train-catalogue.sav` with this fixture's own
`ai/`. A loaded script stays idle while the ordinary train orders continue. Failed
worlds/logs are preserved. This is movement/coupling evidence, not cargo delivery,
all-curve/slope/bridge clearance or source-fidelity approval.

Add `--clearance-route` to replace part of the straight corridor with an actual
eight-tile bridge, its original ramps, and a tunnel constructed through a raised
hill. Both structures must be observed on the normal outbound/return journey.
This works with all four climates and original railtypes. The saved manifest records
the portal offsets and traversal observations. It supplies the route for subsequent
voxel contact/clearance/Cab review; the AI's journey observation alone does not verify
rendered geometry. Use a separate fixture for `--cargo-source` industry service.

For actual open-wagon cargo review, select a single wagon and add a producing/
accepting industry pair, for example `--first-engine 29 --last-engine 29
--cargo-source 0 --cargo-destination 1` for coal to a power station. The AI funds
the original industries beside the stations, checks real station coverage and
acceptance, orders full loading, observes accepted delivery and requires a return.
The harness saves both `save/train-cargo-full.sav` and `save/train-cargo-empty.sav`
before saving the operating fixture. Production, cargo packets and vehicle state
come entirely from ordinary settings, public NoAI construction and normal orders.
Use the saved fixture's own `ai/` and `smoke.py --reference-vehicle <wagon>
--reference-cargo full` or `empty` to check the actual renderer selection separately.

# Custom river-source NewGRF fixture

This is the first natural custom river-source control for the `.46` renderer.
It uses the GPL-2.0
[River Addon for OpenGFX2 'TropicalGrass'](https://github.com/zyliety/River-Addon-for-OpenGFX2-TropicalGrass)
release `V1.0.0` (`source.grf`, SHA-256 in `SHA256SUMS`), not a synthetic hook or
forced sprite selector.

## Survey and world

`survey/fixture.json` records a normal generated temperate world (seed `271828`,
three rivers): **380 original river tiles**, every original slope code
`0, 3, 6, 9, 12`, and acknowledged ordinary `start_ai`/`pause`/`save` commands.
The NewGRF is active in the save and was loaded by the actual game
(`GRFInfo: Loaded GRFv8 set 52495645`); the save and every command
acknowledgement are retained.

## Native render

The extracted post-change build was loaded with the saved world and the staged
GRF, Vulkan, rotation 1, 800×600, `OPENTT3D_EXPORT_WATER_SOURCES=1`. The run
retained **1,156 source-selector observations**:

- **380/380** `CF_RIVER_SLOPE` selectors are the custom ground source;
- **776** `CF_RIVER_EDGE` observations resolve to the custom GRF;
- all **twelve** flat bank offsets `0…11` of the custom base `11446` occur, plus
  the source's rivermouth/rapids offsets;
- every observed `source_file` is the custom GRF, and the exact selected PAM
  bytes are retained for representative ground and bank sources.

The view contains **351 of the 380** surveyed river tiles with a drawn edge.
The remaining 29 tiles have no edge draw at all; no absent `CF_RIVER_EDGE` base
row was emitted and no 3D bank was invented for them. Zero-source absence with
this particular GRF is therefore a structural no-draw state, not a claimed
feature-absence matrix.

This GRF supplies bank artwork and **ANIM river-rapids entries**; the source
contains animated sprites, but their individual phase frames were not separately
observed in this natural run. `source-audit.json` records the exact source
inspection and explicitly leaves phase approval open. The survey's 29 river
tiles without an edge draw are structural no-draw absence; no 3D bank is
invented for them. Because this source supplies a bank for every drawn edge, a
zero-feature base absence is not applicable. The custom bank source is retained
as the original native surface; it is not promoted to a new authored 3D asset.

The run's title-world save completed synchronously with nine acknowledged
console commands, and `run.log` contains no unmodelled-reference report.
`render/river-selectors.json` retains the selector provenance and
`render/source-images/` retains representative exact source PAMs.

## Reproduction

The fixture now accepts a real NewGRF directory and activates it in the isolated
config. The render used `--newgrf-dir` with `-X` intentionally omitted so the
staged working-directory GRF is scanned; all other isolation flags and the
normal RNG/simulation path remain unchanged.

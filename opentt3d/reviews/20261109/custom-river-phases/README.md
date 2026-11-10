# Custom river rapid phase semantics

The custom river source review recorded **64 `ANIM` river-rapids sprite
entries** and left their “individual phase frames” open. This follow-up resolves
what those flags mean from the supplied NML and the exact selected PAM
metadata.

`ANIM` in the source is the 32bpp **palette-animation** flag. It marks pixels
whose remap indices belong to the engine's animated palette range; it does not
create a sequence of source sprites or a per-tile animation callback. The
engine's global palette animation supplies the water phases: the source uses
palette range `227…254`, with the normal five-step dark-water cycle and
fifteen-step glitter-water cycle.

The selected `CF_RIVER_SLOPE` source `11338` (tile `(83,123)`, offset `2`) is a
`64×39` PAM from the custom GRF. Of its **1,280 opaque pixels**, **1,242** use
animated indices:

| palette index | pixels |
| --- | --- |
| 245 | 205 |
| 246 | 339 |
| 247 | 238 |
| 248 | 244 |
| 249 | 216 |

`phase-semantics.json` records the exact source provenance, dimensions,
registration and counts. The engine references are `src/gfx_type.h`
(`PALETTE_ANIM_START=227`, `PALETTE_ANIM_SIZE=28`), `src/palette.cpp`
(`DoPaletteAnimations`) and `src/blitter/32bpp_sse2.cpp` (`has_anim` when a
source remap index is at least 227).

This makes the earlier “individual phase frame” wording inapplicable to this
source: there are no discrete per-sprite rapid frames to observe. It does not
claim a captured renderer palette phase; that remains a separate runtime
control. The source bytes and selector observations remain in
`../custom-river-source/`.

# Retained projection-arithmetic study — not a repair

The two new native controls build and freeze explicit column products/ordered sums
in both vertex shaders, without changing artwork, camera inputs, precision masks or
acceptance tolerances. Native 213 tests pass. Both 432-image per-backend comparisons
against the first frozen study are **pixel-exact**, but the same eight cross-backend
silhouette pixels still disagree. Forcing OpenGL software clipping likewise leaves
both disagreeing pixels in its eighteen-image targeted control.

These results reject both hypotheses as repairs; they do not prove the remaining
cause or approve hardware raster differences. The diagnostic binary, modified shader
sources, compile log, raw captures, strict comparisons and manifests remain retained.
Remove only this agent's two experimental shader edits from the working source,
check exact restored source hashes, and rebuild the original runtime. No `.42`
binary/package/tag, geometry or existing review evidence is overwritten. Strict
renderer acceptance remains open; native equality cannot stand in for it.

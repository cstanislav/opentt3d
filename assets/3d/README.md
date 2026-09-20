# Authored model sources

These JSON files are the editable source artwork. Each part's proportions,
position, silhouette, and material are explicitly authored using the cited
OpenGFX sprite sheets as visual references. `tools/assets/compile_models.py`
triangulates those authored modelling operations; it does not read sprite images
or infer geometry from textures.

Units match OpenTTD: a tile is 16 × 16 world units and one terrain height level
is 8 units. Buildings use a tile-local origin; vehicles are centred and face +X.
Models use solid palette-reference materials for the initial geometry pass.

The pack is **incomplete**. The manifest distinguishes reference models from
development placeholders. A reference model is not yet a claim of finished
artwork: visual matching, material detail, and state coverage need review.

## Attribution and license

Model geometry and assembly: OpenTT3D contributors, 2026, GPL-2.0-only.
Visual references: OpenGFX 8.0, OpenGFX contributors, GPL-2.0-only.

The authoritative reference revision is
`e68bd9b7cb60305aa98c687b6836e0e0b08e2847` in
https://github.com/OpenTTD/OpenGFX. Each model lists its reference paths. Original
per-sprite credits are in OpenGFX's `docs/authoroverview.csv`, available at that
revision. The compiled model library is distributed together with these sources.

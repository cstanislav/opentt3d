# Disaster vehicle 3D prototypes — diagnostic, not accepted

The original 15 disaster subtypes cover 23 source sprites (3901..3923). A first
diagnostic pass authored nine simple 3D bodies, bound them, added a renderer
branch and spawned seven air/subtypes in an actual saved world. The prototypes
render, but the joined screenshot shows coarse flat silhouettes, weak source
paint and incomplete shadow/submarine coverage. They are **not** accepted at
9/10 and are not part of the production catalogue.

`prototype.patch` preserves the exact experimental source changes;
`authored-disaster-models.json` preserves the nine model/binding definitions;
`source-sprites/` retains the original PAM/PNG references; `native-vulkan/`
retains the actual save, acknowledgements, logs and screenshot. The patch was
reverted before committing the diagnostic record.

The production runtime remains on the all-9 authored ledger; the disaster
family is still the remaining uncatalogued runtime gap. A future pass needs
source-faithful blimp/UFO/jet/helicopter/submarine hulls, shadows, rotor states,
firing/crashing variants and actual water/climate variants before any binding.

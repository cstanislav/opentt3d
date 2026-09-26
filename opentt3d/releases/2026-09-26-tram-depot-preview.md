# OpenTT3D development preview: tram-depot coverage

The last missing depot family gains **12 provisional volumes**: four buildings,
four oriented concrete/embedded-rail floors and four independent contact-wire sets.
The catalogue reaches **1,326 volumes**, with voxel bindings for **all six depot
families and24 exit directions**.

- Open vehicle bays, recessed side glazing, folded roofs, paired company-colour
  insulators and supported roof transformers follow the original depot structure.
- The four source climates share identical tram-depot layers; models are reused only
  after the40-layer audit confirms pixels and registration. Each direction uses its
  original source palette.
- Building transparency/invisibility preserves opaque flooring and running rails;
  catenary retains its independent control. The renderer now recognizes the original
  tram sprite offset when selecting the voxel assembly.
- Public NoAI fixtures build all four exits and an operating tram route. A tiny,
  fixture-only NewGRF enables a test bus on tram tracks and changes no sprites;
  production gameplay and vehicle availability retain upstream behavior.

The native200-test suite,125 asset/compiler/schema checks and nine harness checks
pass. All46 final OpenGL/Vulkan/background app-bundle controls pass, including32
actual climate/exit selections and four visible/inside/visible depot traversals.
Peak sampled memory is2,676,313,088bytes. The bounded3,600-frame tram scenes hold60fps;
arbitrary-world sustained performance remains open.
Semantic hashes preserve all1,314 previous volumes. Source, street and actual
world views have been inspected. Detailed roof/transformer/insulator artwork,
catalogue-wide fidelity, packaging and sustained smooth60fps remain unfinished,
with **zero final visual approvals**.

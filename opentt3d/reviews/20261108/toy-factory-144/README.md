# Toyland factory 144 completed state

The title-world fallback exposed `industry 144` stage 3 (`sprite 4714`). The
completed state now selects `toy_factory_144_completed`, built from the source
blue finished factory components (hood, windows, conveyor machinery and roof).
It joins the existing stage 1/2 construction tower without replacing either
state.

The retained `world.png` is the actual title-world Vulkan capture with this
model active: the renderer reports no unmodelled reference sprites in that view.
`gallery.png` is the native model view; `source-1.png`/`source-2.png` are the
original OpenGFX source artwork. The source sprite itself is alpha-composited;
the 3D model is the visible factory volume, not a billboard.

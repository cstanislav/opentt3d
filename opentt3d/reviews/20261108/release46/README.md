# Release .46 macos-arm64 candidate (c875dfd9e)

Built from the accepted runtime commit `c875dfd9e`: **2,887 runtime rows, all
9/10**; 183 retained references separately at 3/10; zero coverage gaps.

The packaged app passed package resource/dependency audits, Vulkan and OpenGL
native load/save controls, and an independently extracted title-world Vulkan
run using only the package resources. That run completed an actual synchronous
save, recorded eight console acknowledgements, and reported **zero unmodelled
reference sprites**.

`package-build.log`, `SHA256SUMS`, `package-metadata.json`, `vulkan/`,
`opengl/` and `independent-title/` retain the evidence. The package is **not
published**. Hosted source/resource and all-platform packaging, independent
Windows/Linux runtime/window/input/replay/network checks, natural HQ/river
selection, LOD/picking/ship clearance and sustained60fps/memory remain open.
`.42` remains the recommended checkpoint.

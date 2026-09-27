# OpenTT3D playable development preview

## Download and play

This release introduces automatic desktop downloads. **Expand Assets below** after
the [package workflow](https://github.com/cstanislav/opentt3d/actions/workflows/opentt3d-release.yml)
finishes:

- **Windows:** `windows-x64.exe` installer or `windows-x64.zip` portable archive.
  ARM64 and 32-bit x86 packages are also built.
- **macOS 15+:** `macos-arm64.dmg` for Apple silicon, `macos-x86_64.dmg` for Intel.
  Drag OpenTT3D into Applications. ZIP versions contain the same apps.
- **Linux x86-64:** extract `linux-x86_64.tar.xz` and run `./opentt3d.sh`.
  Debian 12 / Ubuntu 24.04 or newer is recommended.

The game opens in **3D by default**. OpenGFX2 Classic, authored models, languages and
runtime dependencies are bundled; no original game files or development tools are
needed. Configuration is kept in OpenTT3D's own directory.

See [installation and first-launch instructions](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md),
including the development builds' unsigned/notarization prompts. Optional sound and
music are available through the game's online content browser. Matching game and
graphics sources, build metadata, license notices and SHA-256 checksums accompany
the downloads.

## Renderer repair

Vehicle and Cab smoothing now consume full elapsed presentation time. A retained
electric-train collector crash was reproduced locally with three-second presentation
stalls and passes with this repair on both OpenGL and Vulkan. The diagnostic delay
has been removed from the published implementation.

Verification includes **200 native tests, 128 asset checks, 11 harness checks, and
10 collector controls**, covering both retained crash saves, both development app
bundles, and two 9,000-frame electric-train journeys. All **1,416** model hashes remain
unchanged. Fresh Linux collector acceptance is tracked in the build-and-verify CI.

The package workflow also audits the actual extracted downloads. macOS/Linux check
default-3D and OpenGL rendering plus saving; Windows x64/x86 check native load/save,
while Windows ARM64 is cross-compiled.

This remains a development preview. Catalogue coverage, final artwork fidelity,
and sustained smooth 60 fps are still in progress. Zero final visual approvals are
claimed.

# Development `.45` packaging audit

Draft: https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20261107.45
Tag/commit: `71fb8ebf872c9bf61f5dd9dee8b64d1b99341d15`.

- Eight original packaging jobs passed; nineteen immutable hosted assets and the
  eighteen-entry `SHA256SUMS` were independently downloaded and hashed.
- All **49,190 tracked source files** in the immutable tag/source archive match
  their Git blob IDs; the packaged 1,915-model catalogues compile from the tagged
  authoring source and use the pinned OpenGFX2 graphics. Six platform packages
  were checked.
- The separately downloaded signed macOS ARM64 app passed a default Vulkan
  package control and an OpenGL package control, each with rendered 3D
  presentation and an actual save.
- **Not published.** Full independent native runtime/quality/source-fidelity and
  sustained-60fps/platform acceptance are still required; the draft remains a
  development preview. `.42` stays recommended.

The release adds the orange-cube logo, road-consistent bus/truck stop lanes,
six-unit stepped canal quays, centred bank cupolas, refreshed README/screenshots
and the green nightly workflow. It does not claim every model is 9/10.

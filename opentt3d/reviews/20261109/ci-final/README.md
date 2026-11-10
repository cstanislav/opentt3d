# Final CI matrix — all jobs green

Two independent runs of `OpenTT3D - Build and verify` completed **all ten jobs
successfully**, including the Linux OpenGL full renderer, Linux Vulkan scene and
all four vehicle-pose shards, macOS ARM64 and Windows x64/x86/ARM64:

- [`42584463110`](https://github.com/cstanislav/opentt3d/actions/runs/42584463110)
  at `b44de9cba` — recovered Windows jobs through the vcpkg fallback.
- [`42591061848`](https://github.com/cstanislav/opentt3d/actions/runs/42591061848)
  at `90b28288c` — includes the current OpenGL scene/picking evidence.

The Linux OpenGL full job ran the complete no-scope `--verify-renderer
--verify-tile-picking --verify-bridges --reference-bridge` path and completed
successfully in about 95 minutes. Its full job log is retained as
`linux-opengl-full.log`; this closes the full no-scope CI control (the local
attempt remains separately retained incomplete).

Both records retain each job's exact status and conclusion. Later commits are
documentation/evidence-only; runtime-source changes have a fully green CI
matrix on these runs.

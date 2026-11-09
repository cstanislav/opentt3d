# `.46` independent native release smoke

Workflow runs
[`42565973306`](https://github.com/cstanislav/opentt3d/actions/runs/42565973306)
and
[`42571096954`](https://github.com/cstanislav/opentt3d/actions/runs/42571096954)
downloaded and ran the hosted `.46` archives on real Windows and Linux
runners. All four jobs passed in both runs.

- Linux x86_64: the downloaded archive's default Vulkan 3D launch and explicit
  OpenGL launch both presented a GPU viewport, verified perspective clipping and
  wrote an actual save. The extracted `opentt3d.sh` title world then ran under
  OpenGL with 64 roof/wall picking samples across four rotations, independent
  vehicle picking, nine acknowledged console commands and a synchronous
  `smoke-state.sav`. The run reported no unmodelled-reference lines.
- Windows x64, x86 and ARM64: each independently downloaded portable archive
  started its native `opentt3d.exe`, loaded the packaged title world, and wrote
  a native `package-smoke.sav`. The ARM64 job ran on `windows-11-arm`, not the
  cross-compiling x64 host, so the previously pending native ARM64 execution is
  now verified.
- The Windows jobs exercise native executable/resource loading and save
  serialization only. Hosted Windows runners have no interactive GPU desktop
  or usable console stdin for the GUI-subsystem executable, so their windowed
  renderer, pointer input, replay and dedicated-server checks remain separate
  from this evidence. The Linux job exercises the real window, OpenGL
  presentation, tile picking and a native dedicated loopback listener under
  Xvfb (`network-linux/`).
- The hosted archives were checksum-verified against the release
  `SHA256SUMS`. No source or asset byte was rebuilt or modified for these runs.

Replay and multiplayer client/server transport are still not covered by this
workflow. The package remains the same immutable `.46` draft; `.42` remains the
recommended checkpoint until the outstanding performance and network/replay
gates are closed.

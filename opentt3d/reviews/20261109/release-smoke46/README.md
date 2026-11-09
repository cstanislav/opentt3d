# `.46` independent native release smoke

Workflow runs
[`42565973306`](https://github.com/cstanislav/opentt3d/actions/runs/42565973306),
[`42571096954`](https://github.com/cstanislav/opentt3d/actions/runs/42571096954)
and
[`42573903535`](https://github.com/cstanislav/opentt3d/actions/runs/42573903535)
downloaded and ran the hosted `.46` archives on real Windows and Linux
runners. All four jobs passed in each run; the final run also ran a native
dedicated-server listener on every Windows architecture.

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
  serialization, plus a native dedicated loopback listener on x64, x86 and
  ARM64. Windows console output/input is closed by the GUI-subsystem host after
  accepting the listener, so the result records `loopback_connected: true`,
  `log_acknowledged: false` and `console_input: false`; the wire listener is
  still independently accepted. Hosted Windows runners have no interactive GPU
  desktop, so windowed rendering, pointer input and replay remain separate.
  The Linux job exercises the real window, OpenGL presentation, tile picking
  and a listener with both console and loopback evidence (`network-linux/`).
- The hosted archives were checksum-verified against the release
  `SHA256SUMS`. No source or asset byte was rebuilt or modified for these runs.

Replay and multiplayer client/server transport are still not covered by this
workflow. The package remains the same immutable `.46` draft; `.42` remains the
recommended checkpoint until the outstanding performance and network/replay
gates are closed.

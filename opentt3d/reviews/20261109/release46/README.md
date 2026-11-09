# `.46` hosted source and package audit

The immutable tagged source (`c875dfd9e`) and all 19 hosted assets were
independently downloaded and checked:

- 8/8 packaging jobs passed; manifest `40dac9e8243024d50063b5bea57174b20998b6e07dd6fce4139d493c7fa2f407`.
- 49,507 tracked source files match their Git blob IDs in the source archive.
- The tagged authoring source compiles to the exactly packaged 2,035-volume
  catalogue; all six platform reports and pinned graphics resources agree.
- The independently downloaded macOS ARM64 app passed Vulkan and OpenGL package
  controls and a title-world Vulkan run with an actual synchronous save, eight
  console acknowledgements and zero unmodelled-reference report.
- The independently downloaded macOS x86_64 app ran under Rosetta and passed
  Vulkan/OpenGL package controls plus a title-world Vulkan run with an actual
  synchronous save, eight acknowledgements and zero unmodelled references.
- Independent native release smoke run
  [`42565973306`](https://github.com/cstanislav/opentt3d/actions/runs/42565973306)
  downloaded the hosted archives and passed all four jobs:
  - Linux x86_64 passed default Vulkan and explicit OpenGL package presentation,
    perspective clipping and saved worlds, then an OpenGL title-world run with
    64 tile-picking samples, nine acknowledged console commands and a
    synchronous save under Xvfb; its native dedicated server then listened on
    loopback and accepted a client connection;
  - Windows x64, x86 and native ARM64 each loaded and re-saved the packaged
    title world with the downloaded native executable. ARM64 ran on
    `windows-11-arm`, not a cross-compiling host.

The Windows controls are headless native load/save checks; hosted Windows
runners do not provide an interactive GPU desktop or a usable console stdin for
the GUI-subsystem executable. Windowed Windows rendering, pointer input, replay
and multiplayer transport remain open, as do sustained60fps/memory acceptance. The draft remains **unpublished**; `.42` remains
recommended. The detailed source/artifact audit is
`independent-artifact-audit.json`; native smoke evidence is in
`../release-smoke46/`.

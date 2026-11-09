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

The draft remains **unpublished**. Independent Linux/Windows/x86_64 native
runtime/window/input/replay/network checks and sustained60fps/memory acceptance
remain open; `.42` remains recommended. The detailed source/artifact audit is
`independent-artifact-audit.json`.

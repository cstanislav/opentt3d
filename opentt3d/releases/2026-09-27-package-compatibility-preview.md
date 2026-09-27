# OpenTT3D desktop-package compatibility preview

The first playable-package run exposed platform-specific packaging failures, so
release`.4`has no executable downloads. This follow-up fixes Debian12/Python3.11
archive extraction and Windows system-DLL exclusions. macOS background startup
checks now permit the requested software OpenGL context, print fatal errors instead
of waiting on hidden dialogs, and retain a process sample if startup stalls.

**Downloads appear under Assets only after the new package workflow passes.**
Choose the Windows x64 installer/portable ZIP, macOS Apple-silicon/Intel DMG or ZIP,
or Linux x86-64 archive. Windows x86/ARM64 are also built. See
[installation instructions](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md).
Required graphics, authored models, languages and runtime dependencies are bundled;
normal launches select3D. Sound/music are optional Online Content downloads.

The first hosted run already passes its source checks and native builds/tests.
Its extracted Apple-silicon automatic-Vulkan launch renders and saves successfully.
The other packaged launches, macOS Intel GPU availability, fresh Linux collector
acceptance and final download attachments remain under verification. Windows ARM64
is cross-compiled; native execution remains pending.

This release retains the1,416-model published artwork catalogue and the full-elapsed
vehicle/Cab smoothing repair. Gold-mine work is continuing separately. Catalogue-wide
coverage, final fidelity and sustained smooth60fps remain open; zero final visual
approvals are claimed.

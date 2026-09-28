# Download and play OpenTT3D

Download a desktop package from the **[verified `.29` release](https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20260927.29)**.
Expand **Assets** beneath the release notes. Choose your operating system below;
GitHub's automatic **Source code** downloads are for building the game yourself.

This release provides Windows x64/x86/ARM64, macOS Apple-silicon/Intel and Linux
x86-64 packages. Newer previews appear on the [release list](https://github.com/cstanislav/opentt3d/releases);
their executable assets become available after the package workflow passes.

These are playable development previews. Artwork coverage and performance are
still being developed; see [implementation status](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/STATUS.md).

## Windows

Choose **windows-x64** for most PCs, **windows-arm64** for Windows on ARM, or
**windows-x86** for 32-bit Windows. Windows 10 or newer is supported.

- **Installer (`.exe`):** run the installer, then launch **OpenTT3D**.
- **Portable (`.zip`):** extract the whole archive, then run **opentt3d.exe**.

The development builds are unsigned, so Windows may show an unknown-publisher
prompt. Check that the download came from this repository's release page.

## macOS

Choose **macos-arm64** for Apple silicon (M-series), or **macos-x86_64** for Intel.
The release packages require macOS 15 or newer.

Open the **`.dmg`**, drag **OpenTT3D** into **Applications**, then open it.
The **`.zip`** contains the same app if you prefer an archive.

The previews are ad-hoc signed, without Apple notarization. If macOS blocks the
first launch, use **System Settings → Privacy & Security → Open Anyway** after
trying to open the app. No Homebrew installation or Vulkan SDK is required.

## Linux

Choose **linux-x86_64.tar.xz** for an x86-64 desktop with glibc 2.36 or newer
(for example Debian 12 or Ubuntu 24.04), the GCC 12 C++ runtime, and a working
OpenGL or Vulkan graphics driver. Wayland desktops can use XWayland.

Extract the whole archive, open its directory in a terminal, and run:

```sh
./opentt3d.sh
```

The launcher finds the bundled libraries. Keep the `lib`, `baseset`, and `lang`
directories next to the executable.

## Your first game

The required **OpenGFX2 Classic** graphics and the 3D models are included. You
do not need the original Transport Tycoon game or a separate OpenTTD install.
The game starts in 3D; choose **New Game** or load an existing OpenTTD save.
Saves using NewGRFs still need those NewGRFs. Optional sound and music sets can
be installed from **Check Online Content** in the main menu.
On first launch, a message may say that only a fallback sound set was found.
Close it to play silently, or install **OpenSFX** from **Online Content** for sound
effects. **OpenMSX** provides music.

- Hold the **middle mouse button** on terrain and drag to orbit and tilt.
- Use the **mouse wheel** to move closer or farther away.
- Use a vehicle's **Cab** button for a first-person ride.
- Gameplay, construction tools, menus, and saves follow OpenTTD 15.3.

OpenTT3D uses its own configuration directory: `Documents/OpenTT3D` on macOS
and Windows, and `~/.opentt3d` on Linux (or the platform's XDG data/config paths).
Existing OpenTTD saves can be opened through the load-game dialog.

For troubleshooting, OpenGL can be selected with `-v win32-opengl` on Windows,
`-v cocoa-opengl` on macOS, or `-v sdl-opengl` on Linux. Developers can set
`OPENTT3D_RENDERER=0` to compare the original 2D renderer.

## Release contents

Every new release starts the desktop-package workflow. Assets appear when its
builds and package checks pass; source-only previews before this workflow was introduced do not
have executables. A failed build is visible in
[Actions](https://github.com/cstanislav/opentt3d/actions/workflows/opentt3d-release.yml).

Each published package includes the game, languages, authored models, pinned base
graphics, license notices, and build metadata. The matching `source.tar.xz`
contains the game and authored-asset sources, build scripts, and the pinned
OpenGFX2 source archive. `SHA256SUMS` lists checksums for the uploaded files.

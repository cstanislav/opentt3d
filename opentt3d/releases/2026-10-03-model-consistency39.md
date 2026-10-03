# Road-stop, canal and bank consistency — `.39`

## Download and play

| Platform | Verified download | Installation |
| :--- | :--- | :--- |
| Windows, most PCs | [x64 installer](https://github.com/cstanislav/opentt3d/releases/download/opentt3d-dev-20261003.39/opentt3d-dev-20261003.39-windows-x64.exe) | Install, then open **OpenTT3D**. |
| Mac, Apple silicon | [ARM64 DMG](https://github.com/cstanislav/opentt3d/releases/download/opentt3d-dev-20261003.39/opentt3d-dev-20261003.39-macos-arm64.dmg) | Drag **OpenTT3D** into **Applications**. Requires macOS 15+. |
| Mac, Intel | [Intel DMG](https://github.com/cstanislav/opentt3d/releases/download/opentt3d-dev-20261003.39/opentt3d-dev-20261003.39-macos-x86_64.dmg) | Drag **OpenTT3D** into **Applications**. Requires macOS 15+. |
| Linux, x86-64 | [Linux archive](https://github.com/cstanislav/opentt3d/releases/download/opentt3d-dev-20261003.39/opentt3d-dev-20261003.39-linux-x86_64.tar.xz) | Extract, then run **`./opentt3d.sh`**. Requires glibc 2.36+ and the GCC 12 C++ runtime. |

Portable archives, Windows x86/ARM64 installers, matching source and checksums are
under **Assets**. Graphics are included; optional **OpenSFX/OpenMSX** can be installed
from **Online Content**. See [installation and first-launch guidance](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md)
for unsigned Windows/ad-hoc-signed Mac prompts. Windows ARM64 execution and Windows
GPU/foreground-input acceptance remain unverified.

## What changed

This successor preserves the validated road-stop/canal/bank artwork and runtime
fixes, with portable source-test controls and gated draft-release access. Rejected
`.38` and both failed attempts remain intact at their original commit.

- Bus/truck stops use the original full-tile ground chart and palette at the same
  native texture scale as ordinary roads, without repeated microcrops/markings.
- Bank cupolas are centred across their two original tile owners without missing
  or duplicated seam cells.
- Twelve true stepped canal dikes follow the original live side/corner selections
  in all four climates on Vulkan and OpenGL. Exact Classic climate-soil paint and
  animated water remain independently owned; alternate/custom/partial families
  retain their complete original rendering.
- Native210/asset174/native-host harness76 and boundary140 pass. Source-script
  tests explicitly cover macOS/Linux/Windows without relaxing background guards.

The1,794-model catalogue preserves1,778 preceding non-bank models and every earlier
binding. Four bank bodies intentionally change and twelve dikes are added. Twenty
individual reviews retain6–7/10 scores and hashed evidence in the
[full quality ledger](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/MODEL_QUALITY.md). **No model is claimed8/10-complete.**

Strict backend image differences, full ship/aircraft-volume clearance, missing
object/HQ/lock/river/disaster breadth, source/all-angle fidelity, unresolved effects,
sustained60fps and long-duration memory remain open. Original sources, failures
and rejected studies stay retained. No simulation/command/save changes are made.

## Independent release verification

The immutable tag targets `383e895fd65cbce706245b09bc7f89c19d2c72e2`.
[All eight packaging jobs](https://github.com/cstanislav/opentt3d/actions/runs/37104385626)
pass. Independent downloads reconcile 19 attachments, 18 checksums, 2,154 exact
tagged source files, pinned graphics and six matching 1,794-model catalogues.
Three downloaded Mac render/save/clipping controls, seven hosted graphical
controls and Windows x64/x86 native load/save pass. Hosted Mac worlds match `.37`;
software OpenGL retains zero black pixels and nine differences from Vulkan.

Linux's 1,800-frame journey retains every original support/collector context and
contact tolerance. Its software-rendered 1.505fps and 2,545,934,336 sampled bytes
are **not** sustained smooth60fps or long-duration memory acceptance.
[Guarded publication](https://github.com/cstanislav/opentt3d/actions/runs/37109011247)
preserves every audited attachment ID, size and digest without a rebuild. Checksum
manifest SHA-256: `1d04eecdbee9f28107b672af1ee47b7915859cbbf94edd27194865876ce8facb`.

The newer object/landmark artwork is work in progress and **not included** in these
immutable packages. `.38` remains rejected with both failed attempts and no packages;
`.37` stays available as the earlier independently verified release.

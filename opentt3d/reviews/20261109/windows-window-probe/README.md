# Windows hosted windowed probe (rejected environment)

This is a diagnostic, not a release gate. It independently downloaded the
checksum-verified `.46` Windows x64 package, installed Mesa 26.2.6 software
OpenGL in the extracted package, and ran `package_smoke.py` in its normal
windowed path under a hosted `windows-2022` runner.

The process launched but produced an empty `package-run.log`, no screenshot,
no benchmark and no save; the probe timed out after 300 seconds. The hosted
runner has no interactive desktop/session for a GUI-subsystem window, so this
does **not** establish Windows windowed rendering, pointer input or a native
window. No release byte was changed. The native headless title load/save and
the dedicated loopback listener on Windows are separately verified and pass.

The probe remains rejected rather than being replaced by a headless result.

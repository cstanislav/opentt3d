# Windows CI vcpkg fallback evidence

Run [`42584463110`](https://github.com/cstanislav/opentt3d/actions/runs/42584463110)
completed macOS ARM64 and Windows x64/x86/ARM64 successfully while the GitHub
vcpkg bootstrap was returning HTTP 504.

The workflow now:
1. retries the vcpkg bootstrap;
2. clears a failed bootstrap before retrying;
3. falls back to the runner's preinstalled vcpkg when both downloads fail;
4. selects the fallback toolchain before the failed action output; and
5. uses system CMake/Ninja to avoid vcpkg downloading its own CMake.

The retained Windows job logs show the bootstrap 504 followed by successful
build/test execution. Linux jobs from this run are still in progress and are
not claimed green. This is CI infrastructure recovery, not a runtime asset
change.

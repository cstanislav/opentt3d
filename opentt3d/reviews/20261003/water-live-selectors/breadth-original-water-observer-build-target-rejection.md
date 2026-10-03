# Retained wrong CMake build-target request

`cmake --build build-macos --target opentt3d` returns success without compiling:
`opentt3d` is an existing output filename, not this project's CMake target. Its
binary remains the earlier mixed-working-source runtime build with hash
`f8297acd5b9d674aecd0585f82469ac01799ec1b84e7b4c3f1011c29ed8ff99a`.
The subsequent213 native tests pass that existing baseline and do **not** validate
the new optional water observer. Both original logs remain retained.

Build the actual `openttd` and `openttd_test` targets, record new binary hashes and
rerun controls before claiming the observer has been compiled or validated. This
does not affect the unchanged downloaded/signed exact-tag `.42` app's prior audits.

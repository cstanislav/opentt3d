# Zero-heading identity-transform parity — scoped runtime noninterference

The Vulkan vertex path already skips yaw arithmetic for an exact zero heading.
The GL path now makes the same branch, leaving unrotated instances unchanged and
retaining every existing nonzero canonical/noncanonical rotation. It does not
change raster origins, cameras, object size/origin, source pixels, palette, depth,
draw order, UVs, picking, simulation commands or RNG. This is not the rejected
raster-origin inversion and no speedup or strict-backend repair is inferred.

Twelve fresh acknowledged quiet40bpp-anim controls and eight explicitly reused
fresh shore baselines compare2,498 complete same-backend images and ten original
save-byte pairs exactly: eight world/32 atlas/360 shore-model views, plus two world/
eight atlas/2,088 larger-and-small-HQ owner gallery views. All116 HQ owners remain
separately included; unaccepted larger-stage bindings stay diagnostic/unbound.

Four original/candidate backend controls pass the full scene renderer comparison
including48,840 exact authored voxel/CPU/palette/transparent-picking views and
explicit original engine26/160/204/248/253 company/crash/cargo/heading pose matrices.
The five engine matrices are not a claim that every vehicle/clearance/state is
accepted. Every world/gallery is nonempty and full raw RGBA; no mask/crop/resize/
alpha compositing/tolerance is used. Cross-backend shore/world differences remain
298 pixels; source fidelity, whole-renderer equality and the8/10 goal remain open.

The initial audit used directory-only image discovery for world-file paths. That
empty-world claim is rejected and preserved with its driver/report/hash; corrected
direct-file comparisons require complete nonempty image sets. Portable5,464 PNGs
reconstruct2,060,919,840 exact original PAM bytes, retaining headers and hidden RGB.
`verify-portable.py` recomputes all corrected comparisons and original saves.

Bounded saved-size1 timing/memory observations are separate, background-only,
and do not establish foreground input, all-platform smooth60fps or a measured
speedup. Each backend retains1,800 frames, near60 mean fps but421 Vulkan/181 GL
intervals over20ms, with3,161,853,384/3,227,520,456-byte sampled peaks. Sustained60fps
and memory remain unaccepted; mean fps cannot hide uneven delivery. Native219
tests and integrated asset276/harness116 tests pass. The
catalogue-wide3D/every-model8/10, original source/state/clearance/support/LOD and
performance/platform/input/replay/network acceptance remain unfinished.

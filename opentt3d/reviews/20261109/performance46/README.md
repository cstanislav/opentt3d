# `.46` performance control

Native Apple M3 Pro, Vulkan, 1280×720, title world `(200,160)`, rotation1, zoom5,
600 measured frames. The final 2,887-row catalogue produced **39.37 fps**, p95
work **28.39 ms**, maximum work **50.71 ms**, 600/600 intervals over20 ms and a
peak sampled process footprint of **3.765 GiB** (6 GiB limit; not exceeded).

This is a retained failure against the sustained60fps objective. It is not
hidden by lowering resolution, distance or detail; the exact benchmark and
memory samples are retained.

## LOD trial (rejected, not applied)

A trial coarse rail mesh reduced the captured vertex count from **105.4M** to
**69.1M** (rail 53.5M→21.2M; running rail 37.8M→4.9M), but measured work
remained **39.32 fps** with the same 300-frame overrun pattern. The trial was
reverted because it degraded rail detail without advancing the60fps goal. The
retained capture is CPU-bound at about18.5ms in scene collection even after the
vertex reduction; the exact trial benchmark and world are retained here.

# Zero-yaw identity-transform noninterference study

The Vulkan vertex path skips yaw arithmetic for an exact zero heading. The GL
path currently multiplies the same identity rotation unconditionally. Qualifying
the GL branch identically avoids unnecessary arithmetic on the many straight or
unrotated instances and removes a needless backend arithmetic difference.

This is not the rejected raster-origin inversion. There is no camera, object
size/origin, terrain height, source pixel, palette, draw-order, picking, UV
registration, tolerance or simulation change. Nonzero headings retain their
existing precise canonical rotation and all original transforms.

Only retain the candidate if complete fresh same-backend worlds and complete
model galleries are byte-exact against the immutable baseline. Preserve failed
worlds/candidates; cross-backend differences, source fidelity, 8/10 and sustained
60fps remain unaccepted unless separately demonstrated. A structural compiler
or native-test pass alone does not qualify this runtime change.

# Rejected development preview `.38`

**No playable downloads were produced. Use independently audited
[`.37`](https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20261002.37).**

The immutable tag `opentt3d-dev-20261003.38` retains commit
`18c3ae698f8e4d77e7b1fe9eb0746927a0085f4c`. First run37103567392 could not access
the draft release with a read-only token. After job-scoped access was corrected,
run37104029160 passed source boundary/asset tests but rejected two harness tests
that supplied a macOS-only background flag on Linux. No platform compilation or
package publication ran. Both failures are retained; the tag is not moved.

The corrected source tests require a fresh successor tag and full package audits.
The road-stop, canal and bank fixes remain validated locally; whole-catalogue
8/10 quality, full runtime breadth and sustained60fps remain incomplete.

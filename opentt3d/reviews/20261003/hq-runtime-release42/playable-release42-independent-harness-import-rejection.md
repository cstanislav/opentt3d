# Retained independent diagnostic harness import failure

The independently downloaded `.42` app passes signature verification and both
default/OpenGL package startup/clipping/save controls. The first HQ diagnostic
does not start the game: the copy-on-write resource wrapper invokes the unmodified
smoke harness through `runpy`, but does not add its tools directory to Python's
import path. `fetch_baseset` therefore fails to import. The failed wrapper bytes,
outer log and explicit failed-run record remain retained. No HQ diagnostic pass
or publication is inferred from the two package controls.

Add the same module search path used by normal direct script execution, then use
a fresh `independent-harness-fixed` prefix. Reuse only the independently downloaded,
already extracted app after checking the original archive digest, code signature,
exact metadata and catalogue again. No binary, app resource, game/harness assertion,
RGBA tolerance, source artwork or old result is replaced or weakened.

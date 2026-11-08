# Release .46 local macOS-arm64 candidate

This candidate was built from commit `0128cbdc8` (the accepted 2,886-row runtime
ledger, all at 9/10; 183 retained references separately at 3/10; zero coverage
gaps). The package contains the pinned OpenGFX2 Classic set and the final
disaster body/shadow catalogue.

Local package-generation and resource/dependency audits passed. Two extracted
package runs loaded and saved natively: Vulkan and OpenGL. Their results and logs
are retained here. The `.dmg` and `.zip` hashes are in `SHA256SUMS` and
`package-metadata.json`.

This is **not** a published release and not a full independent matrix. Hosted
source/resource downloads, Windows/macOS x86_64/Linux packaging jobs, independent
native GPU/window/input/replay/network checks, sustained 60fps/memory, natural
HQ-score selection and natural custom river-source selection remain open.
`.42` remains the recommended checkpoint.

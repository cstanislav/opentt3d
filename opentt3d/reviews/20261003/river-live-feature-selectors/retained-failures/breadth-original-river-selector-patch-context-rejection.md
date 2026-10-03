# Retained patch-context failure

The first multi-file selector patch omitted the trailing comment on the existing
`if (base == 0) return; // Don't draw if no sprites provided.` line. The patch tool
rejected the entire operation before changing any file. A subsequent search found
no new observer symbols and `git diff --stat -- src` was empty. The corrected patch
keeps the original early return and comment, and adds only a preceding read-only
absence observation. This is an editing-context failure, not a runtime test result.

# Windows checkout blocker and conservative recovery

The requested public .43 publication could not be accepted: run37222704319
completed with source, both Mac architectures and Linux passing, all three
Windows jobs failing checkout, and the final upload/checksum job skipped. The
exact job receipts and complete failure logs remain. This is not eight passed
jobs or nineteen independently audited hosted release attachments.

Git for Windows rejected long retained native-evidence paths before compilation.
The recovery enables `git config --global core.longpaths true` before Windows
`actions/checkout`. It does not shorten, exclude, rename or delete evidence,
relax a renderer comparison, move the .43 tag, or silently activate an unaccepted
model. Two regression tests guard ordering/no exclusions; the full harness now
passes118 tests. The new immutable .44 draft starts a fresh packaging attempt.
Neither draft is publicly promoted or recommended merely because the timebox ends.

The available .43 Mac ARM64 CI artifact can be independently downloaded and
audited as a **limited preview only**. Its outer artifact SHA-256, immutable
tagged authoring, compiled catalogue and pinned graphics are checked, then its
signed app is reviewed quietly. This is not a complete source/hosted-platform
audit, nineteen assets, independent Windows execution, or publication acceptance.

For a later resumption: follow the new .44 Actions run, require all eight jobs,
and retain all new downloads and native controls under fresh .44 paths rather
than overwriting any .43 preview. Source/package/native/publication verifiers must
use that exact .44 tag, commit, run and checksum manifest. Only then use guarded
GITHUB_TOKEN publication, recheck all original attachment IDs/digests and both
prior releases, and confirm anonymous public access without a package rebuild.
Do not infer this completion from the checkout fix or leave a promise of automatic
publication. .42 remains immutable and recommended; .41/.43 remain immutable drafts.

# Bounded exact mesh restoration

Cold animated voxel states can now restore their original triangle streams from
compact CPU storage. Independently packed spans support tall and disconnected volumes;
every decoded vertex must retain its exact original words.

## Changes

- Compact buffers share the existing1GiB CPU soft budget, using at most its quarter
  and never more than256MiB.
- Active scenes retain their leases and stable mesh identities. Forced retirement
  releases compact copies; unsupported geometry uses retained-source reconstruction.
- Automatic LODs remain active. The production catalogue contains1,736 models.

## Verification

All207 native checks and eight sequential background Vulkan/OpenGL controls pass.
Both cold900-frame crash replays preserve two complete63-phase explosion lifetimes
with zero gaps. Maximum scene capture is13.702/14.239ms, compared with38.147ms in the
earlier default Vulkan control. Peak sampled cold-control memory is3.224/3.262GB;
the earlier no-retirement diagnostic exceeded6GB.

378 model captures and162 original source exports match their controls. Ordinary
copper-mine replays retain26 complete smoke lifetimes each. The explosion models used
to expose the stall remain staged artwork outside this release.

## Play

The [verified `.33` desktop release](https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20260927.33)
builds exact commit `5cd9284e4de7ab101a65f0cea15d8c9ddf8fecc5`. All eight jobs pass;
independent checks reconcile19 attachments,18 checksums,2,107 source files and six
identical1,736-model catalogues. Three downloaded Mac render/save/clipping controls,
seven hosted graphical controls, Windows x64/x86 load/save and Linux's900-frame
support/collector journey pass. Hosted ARM/Intel software-OpenGL worlds retain zero
black pixels and nine differing pixels from Vulkan.
Use the [installation guide](https://github.com/cstanislav/opentt3d/blob/main/opentt3d/PLAYING.md)
for the current independently verified download.

## Still in progress

These short controls retain uneven pacing; the mine run reaches53.373ms between frames.
Sustained arbitrary-world smooth60fps, long-duration/reload/multiple-viewport memory,
complete catalogue artwork and essential larger-aircraft clearances remain open.
No model has final visual approval.

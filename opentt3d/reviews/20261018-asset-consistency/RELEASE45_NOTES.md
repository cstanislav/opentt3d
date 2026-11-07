# OpenTT3D development .45 — branding and consistency pass
This is a development prerelease. It is not a claim that every model is 9/10 or
that sustained 60fps has been accepted. [Immutable `.42`](https://github.com/cstanislav/opentt3d/releases/tag/opentt3d-dev-20261003.42)
remains the recommended playable checkpoint; `.44` remains an immutable draft.

## Included work
- New isometric orange-cube icon with a central dollar mark and OPEN/TT3D
  ribbons, replacing the locomotive icon. PNG/ICO/ICNS/installer assets were
  regenerated from the same polygon source.
- Drive-through and bay bus/truck stop lanes now sample the adjoining paved road
  ground, so asphalt and markings continue through the stop instead of showing a
  different station-ground rectangle.
- Twelve canal dikes are six-world-unit stepped stone quays with the original
  ten-world-unit clear channel, water level, animation and picking retained.
- Arctic/tropical bank cupolas are centred on the exact joined-roof seam.
- The high-level README, eight representative screenshots and wording were
  refreshed; hand-crafting language was removed from public descriptions.
- Nightly CI now passes both platform jobs and the annotation check. Windows
  checkout long paths, the macOS deployment target, the retired MINGW32 matrix,
  regression-test timeouts and pinned OpenGFX2 for the regression suite were
  corrected. Upstream stable remains 15.3; 16.0-RC1 is the newest prerelease and
  is not merged.

## Acceptance limits
The catalogue-wide model reviews still have no 9/10 approvals. 1,827 bound
models remain structural 5/10 screens, 271 profiles await individual review, 536
missing/fallback rows remain, 84 larger-HQ owners remain unbound and the 192
canal-lock source layers remain fallback. Flat airport/construction ground
surfaces, effect shells, river/conditional states, source fidelity, support, LOD,
picking, ship clearances, strict whole-world equality, sustained 60fps/memory
and Windows ARM64/GPU/input/replay/network acceptance remain open. Downloads are
attached only after the eight packaging jobs and independent hosted-source/
resource/native checks pass.

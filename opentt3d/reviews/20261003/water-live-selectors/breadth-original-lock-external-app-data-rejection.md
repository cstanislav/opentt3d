# Retained dedicated external-app data lookup failure

The first lock fixture exits before creating a map or starting its public AI:
`No available language packs`. The separately executed exact-tag Mac binary with
`-X` does not find language data in its Resources directory automatically. The
original command, config, AI and failure log are retained; no lock/save was created
and no package is modified.

The corrected runner copies the unchanged matching Resources language pack into
its new isolated data directory and verifies/seeds the pinned original graphics,
as the normal smoke harness does. It does not alter the app, gameplay, source slope,
AI commands, acknowledgements or save assertions. Use a fresh output directory.

The second isolated attempt also exits before creating a map: the deliberately
omitted bundled `no_sound.obs`/`no_music.obm` prevent original startup even with
null sound/music drivers. Its fresh output/log remain retained separately. The
runner now copies the app's unchanged GRF/sound/music/font/graphics-set descriptors,
excluding all JSON model catalogues, alongside its matching language and verified
graphics tar. Renderer0 dedicated fixtures do not need the voxel catalogue. No
gameplay or lock assertion is weakened and the exact-tag app remains unchanged.

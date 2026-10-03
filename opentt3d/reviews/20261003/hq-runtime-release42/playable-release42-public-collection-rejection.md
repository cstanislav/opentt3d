# Retained public-release collection KeyError

The first public reconciliation passes the nineteen exact .42 attachment IDs,
sizes/digests, notes/title, tag, guarded publication receipt and no-rebuild history.
It then fails because the prior .41 withheld snapshot requested no `isPrerelease`,
`name` or `body` fields. This is not a package failure or evidence of changed .41
attachments. No portable success receipt was created by the failed script.

The original script/log remain retained. The fresh reconciliation explicitly
compares every available withheld tag/commit/release-ID/attachment field and draft
flag. Its earlier creation snapshot additionally supplies the prerelease flag and
title. The withheld snapshot does not establish a before/after notes comparison;
that limitation is explicit rather than claiming unobserved equality. No .41 API
mutation is performed. All .42 exact title/notes/attachment checks stay unchanged.

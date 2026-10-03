# Initial draft metadata rejected before artifact audit

The initial `.42` draft points `target_commitish` at `main` and lacks the required
development prerelease flag. Its exact authenticated snapshot is retained in
`playable-release42-initial-draft.json`; it has no uploaded attachments and remains
draft. Neither branch shorthand nor an annotated tag object is an exact commit.

Before auditing any attachments, correct only `target_commitish` to the immutable
full commit1247c88d5e180ac6fbd88bdf9b71bfafd468f7a5 and `prerelease=true`.
Preserve the release ID, tag, draft flag, notes/title and every artifact byte.
The annotated tag must peel to that exact commit locally and remotely. Later
guarded publication still changes only `draft=false`. `.41` is untouched.

The first metadata-only PATCH also exposes the API draft's provisional
`untagged-e0f4ff832edc301b0b07` tag name, unlike the gh release-view selector.
Its response remains retained in `playable-release42-exact-draft.json`. Supply
the exact existing annotated tag name explicitly in the second metadata PATCH;
check the authenticated API fields rather than inferring them from a friendly
release URL. Both responses must stay draft and preserve title/notes/attachments.

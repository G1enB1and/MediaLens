## MediaLens v1.1.1

### Summary
This release marks a major MediaLens milestone: duplicate review and similar-image grouping are now built directly into the gallery workflow. Exact duplicate sets, visually similar image groups, keep-best suggestions, metadata merging, and review controls are now live!

### Highlights
- Added Group By `Duplicates`, `Duplicates and Similar`, and `Similar` gallery review modes in both the header and native `View` menu.
- Added perceptual-hash based similar image grouping for images, alongside exact duplicate grouping by content hash.
- Added duplicate and similar group review UI with keep-target selection, auto resolve actions, per-file delete, metadata merge, and group summary controls.
- Added non-destructive metadata merge across duplicate groups so tags, descriptions, notes, and related fields can be preserved before cleanup.
- Added keep-candidate reasoning such as metadata richness, folder organization, resolution, file size, and newest edit.

### Notes
- `Duplicates` finds exact file matches.
- `Duplicates and Similar` combines exact duplicates with perceptual similar-image grouping.
- `Similar` excludes exact duplicate-only matches so finding edits, burst shots, and prompt reruns are easier.
- Similar-image detection currently targets images and uses perceptual hashing; exact duplicate detection still covers videos through the existing content hash.

---

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md

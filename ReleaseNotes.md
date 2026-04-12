## MediaLens v1.1.17

### Summary

This release makes duplicate cleanup easier to trust. MediaLens now keeps your review decisions consistent, improves how duplicate matches are identified, and introduces a built-in retention system for safer file cleanup and recovery.

### Highlights

- Duplicate and similar review now loads more smoothly, with clearer progress stages and more stable rendering.
- Selections, folder priorities, and copied tags now behave more consistently during cleanup.
- Exact image duplicates continue matching even after metadata-only edits.
- New built-in retention system gives you a safer alternative to the Recycle Bin, with restore and cleanup controls.

### Notes

- Image duplicate matching now ignores metadata-only changes, which helps embedded-tag edits stay grouped as exact duplicates after a rescan.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>

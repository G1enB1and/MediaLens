## MediaLens v1.2.9

### Summary

This release expands folder workflows, collection behavior, and file handling while making gallery video playback and sorting more dependable. MediaLens now handles more real-world library layouts with less unnecessary scanning, smoother playback behavior, and clearer fallback handling.

### Highlights

- Drag folders between the gallery, file tree, pinned folders, collections, and external destinations with clearer move, copy, and pin behavior.
- Build live collections from folders, including folder display and Include nested files behavior that matches normal gallery browsing.
- Recover deleted folders and non-media files from the MediaLens recycle bin when MediaLens performed the delete.
- Show all file types when enabled, while keeping unsupported files lightweight and avoiding expensive media processing.
- Play WebM files more reliably in the gallery and sort galleries with less background work.

### Notes

- Masonry remains media-only, even when Show All File Types is enabled.
- Non-media files are shown as external-openable files and support MediaLens move, copy, and delete workflows without thumbnail, OCR, AI, or metadata processing.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>

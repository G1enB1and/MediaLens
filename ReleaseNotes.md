## MediaLens v1.2.11

### Summary

This release introduces persistent Action History with undo and redo across sessions, making large cleanup and metadata workflows safer, easier to review, and easier to recover from. MediaLens now tracks whether previous actions remain reversible, adds clearer history states, and improves workflow organization across editing and review tools.

### Highlights

- Review recent file and metadata actions in a dedicated Action History window.
- Undo or redo supported actions across sessions when the original files or retained copies are still available.
- Work with a cleaner Edit and View menu layout plus improved light and dark theme coverage for related dialogs.

### Notes

- Action History validates recoverability lazily so normal browsing and editing stay responsive.
- This release does not include installer or runtime packaging changes.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>

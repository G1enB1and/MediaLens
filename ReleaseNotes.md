## MediaLens v1.1.34

### Summary

This update makes MediaLens more dependable when working with SVGs, bulk selections, and the details panel. SVG previews are cleaner, Local AI can tag SVGs through generated preview images, and empty details states no longer leave stale metadata behind.

### Highlights

- SVGs now preview more sharply and can be tagged with Local AI through generated preview images.
- The details panel now fully resets when nothing is selected, avoiding stale tags, descriptions, or AI metadata.
- Ctrl-click deselection now works correctly when removing one file from a selected group.

### Notes

- This release also includes internal refactors that split large bridge, window, settings, and web files into smaller modules without changing intended behavior.
- Several native UI symbols were moved to SVG assets to avoid character encoding problems.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md

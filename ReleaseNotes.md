## MediaLens v1.1.9

### Summary

This release makes everyday browsing feel more flexible and polished. It improves filtering, startup presentation, and several header and settings workflows so common actions take less effort.

### Highlights

- Filter By now supports independent media-type and text-detection groups, so you can combine filters without resetting the rest of your view.
- Startup now feels cleaner with an optional transparent splash screen and without the extra stray window before the full UI appears.
- Header, settings, and sidebar polish reduce visual friction during navigation, sorting, and folder review.

### Notes

- This release also refines the header, settings layout, pinned-folder area, and sidebar behavior for a more consistent day-to-day workflow.

### Details

#### Added

- Added grouped Filter By controls so media type and text detection can be filtered independently.
- Added a `No Text Detected` filter for quickly isolating images without detected text.
- Added a `Sort: None` option to return to the default order, including randomized order when that setting is enabled.
- Added an optional transparent startup splash screen with an Appearance setting to turn it on or off.

#### Changed

- Widened and refined the Filter By control so grouped filters remain easier to scan and use.
- Updated the header layout by moving the search bar to the lower row, improving address-bar responsiveness, moving the file count next to search and pagination, and replacing the old Compare header button with the bottom-panel toggle.
- Replaced the gallery scroll-to-top and scroll-to-bottom header icons with cleaner themed SVG icons.
- Moved the MediaLens title and logo above Pinned Folders, added a matching separator, and aligned left-panel separator spacing and thickness more consistently.
- Updated settings layout and wording by moving Appearance above Player, moving the close control to the top right, and renaming duplicate-review rules to Similar File Rules.
- Restored accent styling for the active folder in the File Tree and removed the extra focus border from pinned folders.
- Changed the right details panel scrollbar to appear only when needed.
- Improved startup loading by fixing parentage for the main splitter panels so the app opens more cleanly.

#### Removed

- Removed the standalone Compare button from the header.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>

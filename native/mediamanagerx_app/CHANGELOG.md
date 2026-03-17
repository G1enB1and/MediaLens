# Change Log

## v1.0.12 (Current)

### Added in v1.0.12

- **Update Notification Enhancements**: Improved update notifications by replacing redundant native OS dialogues with stylized toasts for a more consistent and modern UI experience.

### Changed in v1.0.12

- **Video Loading Optimization**: Refined the video loading mechanism to significantly reduce delay, ensuring a smoother playback experience in the gallery.
- **Scanning Efficiency**: Optimized the file tree scanning process to ensure full scans only occur when necessary, improving overall application responsiveness.

---

## v1.0.11

### Added in v1.0.11

- **Collections System**: Introduced a new system to organize media into collections. Collections appear in the left sidebar, are resizable, and persist across sessions.
- **Enhanced Search Syntax**: Overhauled the search engine to support collections, wildcards, mathematical expressions, exclusions, phrases, and complex operators (+ - ? * | OR).
- **Search Help**: Added a detailed search syntax guide accessible via the Help menu.
- **Collection Context Menu**: Added "Add to Collection..." to the gallery context menu, supporting both individual and bulk actions with the ability to create new collections on the fly.

### Changed in v1.0.11

- **Scanning Progress Bar**: The progress bar is now stationary at the bottom of the screen and hides completely when clicked.
- **Sidebar Resize Handles**: Refined the UI by reducing the sidebar resize handle width from 5px to 1px.

### Fixed in v1.0.11

- **Glass Morphism Persistence**: Fixed an issue where the glass morphism setting was not correctly restored on application launch.

---

## v1.0.10

---

## v1.0.9

### Added in v1.0.9

- **Enhanced Metadata Support**: Expanded metadata scraping to include tEXt, iTXt, zTXt, XMP, EXIF, chara, C2PA, JUMBF, caBX, IPTC, JFIF, and COM. The app now detects digital watermarks, ComfyUI workflows, character cards, AI prompts/parameters, and more.
- **Metadata Settings Tabs**: Added separate tabs in Settings for Image, Video, and GIF metadata configurations.
- **Metadata Grouping**: Grouped metadata into General, Camera, and AI sections that can be individually hidden or reordered.
- **Metadata Persistence**: Added a button to save hidden metadata into a visible comments field for easier access.

### Changed in v1.0.9

- **Metadata Sidebar UI**: Redesigned the metadata sidebar to use vertically stacked buttons, ensuring elements fit correctly within the available width.

---

## v1.0.8

### Added in v1.0.8

- **Video Rotation**: Added context menu options to rotate video files 90 degrees CW and CCW.
- **Image Rotation**: Added context menu options to rotate image files 90 degrees CW and CCW.
- **External Editors**: Added Open with Photoshop and Open with Affinity right-click actions.

### Changed in v1.0.8

- **Pause Button**: Refined the pause button interaction and logic.

### Fixed in v1.0.8

- **Installer**: Fixed setup installer missing files and pathing bugs.

---

## v1.0.7

### Changed in v1.0.7

- **Video Player Sizing Fix**: Addressed a race condition that caused in-place gallery videos to occasionally play at an incorrect, minimized size.
- **Lightbox Styling Refinements**: Fixed an issue where hovering over the lightbox previous/next navigation buttons caused them to shift downward. They now scale up smoothly in place.
- **Mute Default Restored**: Fixed a bug where in-place videos would sometimes start with sound. Videos are properly muted by default again.
- **Previous and Next Buttons Changed**: Replaced the native video player's previous and next emoji buttons with custom SVG graphics to prevent the Windows OS from rendering them with colorful backgrounds.

### Removed in v1.0.7

- **Close Buttons Removed**: Completely removed both the native video player close button and the underlying web lightbox close button to eliminate visual ghosting and overlapping. Users can cleanly close the media overview by clicking anywhere outside the media content.

---

## v1.0.6

### Added in v1.0.6

- **In-Place Video Playback**: Videos can now play directly inside the gallery card, overlaid on the thumbnail, without opening a separate window.
- **Custom SVG Media Controls**: Play and Pause buttons now use custom SVG icons for a crisp, professional appearance that avoids OS emoji rendering issues on Windows.
- **Video Controls Overlay**: A translucent control bar with play/pause, mute, volume slider, and a seek bar is displayed while a video is playing in-place.

### Changed in v1.0.6

- **Accent Color on Video Sliders**: Volume and seek bar sliders in the video overlay now use the user's selected accent color from Settings.
- **Smart Lazy Loading**: Gallery images are now loaded on demand as you scroll, using a native `IntersectionObserver` bound to the scrollable container. Images one full screen below the visible area are preloaded before you scroll to them.
- **Poster Restoration**: Pausing or closing an in-place video now correctly restores the original thumbnail poster image.
- **Video Click Behavior**: Clicking the video frame no longer pauses playback; only the dedicated Pause button does.
- **Fixed What's New:** What's New now accurately reflects current Changelog.md.
- **Fixed Auto-Update:** Auto-Update now uses RedirectPolicyAttribute with NoLessSafeRedirectPolicy which properly follows the redirects that github uses for releases.

### Removed in v1.0.6

- **Removed Loading Media Dialog**: Removed the "Loading Media" progress dialogue because local files load faster than the dialog can meaningfully update, eliminating a visual stutter on every gallery update.

---

## v1.0.5

### Changed in v1.0.5

- **File Tree Fix**: Improved path normalization and initialization robustness to ensure the file tree is visible in the packaged installer environment.
- **Improved Logging**: Added detailed initialization logging to help diagnose environment-specific path issues.

---

## v1.0.4

### Added in v1.0.4

- **Gallery Drag & Drop**: Drag and drop files or folders from Windows File Explorer directly into the gallery area with the same behavior and styling as the file tree.
- **Conflict Comparison Dialog**: Added a popup dialog when copying or moving files to a destination containing an existing filename, allowing context comparison before resolving the conflict.

### Changed in v1.0.4

- **Cursor Feedback**: Cursor now changes to a hand pointer when hovering over clickable folders and files.
- **Conflict Dialog Improvements**:
  - Fixed SVG rendering for the **“Apply to all”** checkbox so the checkmark displays correctly in all themes.
  - Improved button hover effects for clearer interaction feedback.
  - Fixed vertical clipping of long filenames.
- **Drag & Drop Refinements**:
  - Improved handling of multi-file transfers between the gallery and file tree.
  - Adjusted tooltip offset and event handling to suppress duplicate Windows tooltips.
- **Gallery Context Menu**: Right-clicking empty gallery space now correctly opens the application menu.

---

## v1.0.3

### Added in v1.0.3

- **Keyboard Shortcuts**:
  - **Ctrl+C / Ctrl+X / Ctrl+V** — Copy, Cut, Paste files and folders
  - **Delete** — Delete selected items with confirmation
  - **F2** — Rename selected items (inline for folders, dialog for gallery)
  - **Ctrl+A** — Select all gallery items

### Changed in v1.0.3

- **Drag & Drop Improvements**:
  - Move or copy multiple selections simultaneously
  - Default action is **Move**, hold **Ctrl** to **Copy**
  - Dynamic tooltips showing destination folder
  - Drag thumbnails offset from cursor for better visibility
- **Selection & UI Stability**:
  - Fixed gallery items deselecting when opening context menus
  - Gallery now refreshes immediately after deletion
  - Keyboard shortcuts no longer trigger while typing in Tags or Description fields
- **Metadata Compatibility**: Fixed tag and comment embedding so metadata appears correctly in Windows File Properties.
- **Persistent Layout**: Sidebar widths are now remembered across sessions.
- **UI Improvements**:
  - Fixed inconsistent theme colors in metadata and bulk tagging sidebars
  - Adjusted scrollbar hover effects for better visual consistency
- **Bug Fix**: Resolved `AttributeError` in native shortcut handlers.

---

## v1.0.2

### Added in v1.0.2

- **Auto-Update System**: App now checks GitHub for updates on launch (manual check available).
- **Help Dialogs**: Added **Terms of Service** and **What’s New** windows in the Help menu.

### Changed in v1.0.2

- **Media Loading**: Placeholders and borders remain hidden until metadata and dimensions are loaded.
- **Navigation Fix**: Scroll position now resets correctly when switching pages or search results.
- **Performance Optimization**: Removed real-time GIF pausing in the lightbox to reduce overhead.
- **UI Improvements**:
  - Help dialogs now use themed backgrounds matching light and dark modes
  - Fixed button contrast issues in light mode
  - Added native Markdown rendering for informational documents
- **About Window**: Expanded version and author information.
- **Masonry Layout Stability**: Prevented layout shifts by reserving space using correct aspect ratios.

---

## v1.0.1-alpha

### Added in v1.0.1-alpha

- Initial MediaManagerX project scaffold and Python package layout.
- SQLite schema bootstrap and initialization scripts.
- Windows path normalization utilities and scope validation.
- Folder scope query builder and selection state helpers.
- Core repositories for media ingest/query, metadata CRUD, and tag CRUD.
- Repository facade (`MediaRepository`) for native UI integration.
- Unit test suite for foundation modules.
- Development validation helper (`scripts/dev_check.py`).
- First-run database bootstrap helpers and automatic DB initialization.
- Repository hygiene configuration (`.gitignore`) for caches and runtime data.
- `Makefile` convenience commands (`setup`, `test`, `run`).
- CLI support for custom database paths via `--db-path`.
- Demo ingest script for quick ingestion and scoped listing tests.
- Initial container-first masonry layout helper and design documentation.

---

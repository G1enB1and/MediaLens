# Change Log

## v1.0.16 (Current)

### Changed

- **Grouped Details View**: Fixed grouped Details mode so only one sticky column header appears at the top, date groups collapse correctly, sticky date headers sit beneath the Details header, and the header seam no longer exposes scrolling content behind it.
- **List Context Menu**: Refined list-view context menu layering so the custom right-click menu reliably appears above gallery rows instead of being visually overlapped by list items.
- **Fresh Install Bootstrap**: Updated the packaged database initialization flow to bundle and load the SQL schema correctly in installed builds, preventing first-run launch failures caused by missing `app\\mediamanager\\db` resources.

---

## v1.0.15

### Added

- **Date Grouping**: Added `Group By Date` across gallery views with date headers, collapsible sections, and a right-side jump/scrub timeline.
- **Date Metadata Fields**: Added `Date Taken`, `Date Acquired`, `Date Created`, and `Date Modified` to metadata settings and the Details sidebar for images, GIFs, and videos.

### Changed

- **Timeline UI**: Refined the timeline scrubber layout, spacing, padding, coloring, and docked sizing so it no longer overlaps the gallery and behaves predictably while resizing.
- **Metadata Dates**: Updated scanning, import, save, and embed flows to extract and persist filesystem dates plus EXIF/XMP-style taken/acquired dates, and made `Date Taken` and `Date Acquired` editable in the sidebar.
- **Date Labels**: Renamed date labels throughout the app for consistency with Windows Properties and the Details/settings panels.

---

## v1.0.14

### Changed

- **Installer Build**: Updated the packaged Windows app so background media scanning and related `ffmpeg`/`ffprobe` work no longer opens console windows while scanning folders.

---

## v1.0.13

### Added in v1.0.13

- **AVIF Support**: Introduced support for AVIF image files.
- **New Gallery Views**: Added several new view modes including List, Details, Content, and multiple Grid sizes (Small, Medium, Large, Extra Large) alongside the default Masonry layout.
- **Sidebar Preview Section**: Added a new preview panel at the top of the right sidebar that displays a thumbnail of the selected item above the metadata details.
- **View Menu**: Added a new "View" menu to toggle panels and switch between different gallery view modes.

### Changed in v1.0.13

- **Video Controls**: Reduced the time video controls remain visible after mouse-over to 500ms for a more responsive feel.
- **Details Panel Responsiveness**: Improved the responsiveness of the metadata details panel.
- **Hidden Files Logic**: Updated hidden files, folders, and collections logic to use hidden status in database rather than filenames starting with a dot.

### Fixed in v1.0.13

- **File Tree**: Fixed a critical issue where the folder tree appeared empty in the installed application when the root was a drive path (e.g., `C:/Pictures`).
- **AVIF Previews**: Implemented FFmpeg-based fallback for AVIF sidebar previews, resolving the issue where native Qt support was missing.
- **AVIF Dimensions**: Added ffprobe-based dimension retrieval for AVIF files to ensure correct aspect ratios and details rendering.
- **Conflict Dialog**: Improved conflict detection and thumbnail rendering in the conflict dialog for AVIF files.

---

## v1.0.12

### Changed in v1.0.12

- **Video Loading Optimization**: Refined the video loading mechanism to significantly reduce delay, ensuring a smoother playback experience in the gallery.
- **Scanning Efficiency**: Optimized the file tree scanning process to ensure full scans only occur when necessary, improving overall application responsiveness.
- **Update Notification Enhancements**: Improved update notifications by replacing redundant native OS dialogues with stylized toasts for a more consistent and modern UI experience.

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

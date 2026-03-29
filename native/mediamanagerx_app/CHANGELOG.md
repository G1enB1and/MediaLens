# Change Log

## v1.1.4 (Current)

### Added

- **Recycle Bin Delete Workflow**  
    Added recycle-bin delete as the default behavior, a `Shift+Delete` permanent delete shortcut with confirmation, and a new setting to control recycle-bin usage.
- **Pinned Folders Sidebar**  
    Added pinned folders in the left sidebar with right-click add/remove actions and drag-and-drop support.

### Changed

- **Video Preview Reliability**  
    Rebuilt the preview-above-details video pipeline to restore metadata, static posters, explicit in-place playback, lightbox double-click, and stable delete behavior without the earlier crashes.
- **Accent Contrast**  
    Improved accent-color readability in lower-contrast situations by dynamically increasing contrast where needed.
- **File Tree Visual Polish**  
    Refined tree and pinned-folder styling so selected folders use bold accent text without tinting icons, and chevrons only render when folders actually have children.
- **Header Branding**  
    Replaced the header logo.

---

## v1.1.3

### Added

- **Sidebar Video Player**  
    In-place video playback directly above the metadata panel.
- **Text Detection Filter**  
    3-stage text detection system (Likely, More Likely, Verified) powered by OpenCV and OCR.

### Changed

- **Video Playback Stability**  
    Improved async teardown of video pipelines to prevent UI freezes and crashes during navigation.
- **Preview Toggle UX**  
    Moved preview toggle beside the header using a dedicated outline icon, keeping the header consistently visible.
- **Video Controls UI**  
    Refined controls with clean borders, frosted glass backgrounds, and high-contrast white icons.
- **Documentation**  
    Updated README and screenshots to reflect duplicate grouping, resolution workflows, and settings.
- **Branding**  
    Updated app icon and logo.

---

## v1.1.2

### Added

- **Auto Resolve Settings Panel**: Added a dedicated Duplicate and Similarity Auto Resolve Rules settings section with Rules and Priorities tabs for review behavior.
- **Variant Detection Labels**: Added color/grayscale, cropped/full-frame, file-size, and preferred-format labels to duplicate and similar review cards.

### Changed

- **Duplicate and Similar Ranking**: Refined keep-best scoring so visible category winners align better with the overall recommendation and user-configurable priority order.
- **Similarity Detection Stability**: Fixed pHash backfill, review grouping, and duplicate/similar counting regressions that were causing empty results in real folders.
- **Review Workflow Reliability**: Restored scan-driven duplicate and similar results, preserved review positioning more reliably after delete actions, and kept the duplicate/similar experience responsive.

---

## v1.1.1

### Added

- **Duplicate Review Modes**: Added `Duplicates`, `Duplicates and Similar`, and `Similar` gallery review modes in both the header controls and native `View` menu.
- **Perceptual Similarity Grouping**: Added perceptual-hash based grouping for visually similar images, alongside the existing exact duplicate grouping by content hash.
- **Duplicate Workflow Actions**: Added duplicate/similar group summary cards, keep-target selection, auto resolve, per-file delete, and group-level metadata merge actions.

### Changed

- **Keep Candidate Scoring**: Added richer keep-best reasoning based on metadata richness, folder organization, file size, resolution, and newest edit to make duplicate cleanup more trustworthy.
- **Similarity Threshold Controls**: Added user-selectable similarity threshold levels and split exact duplicate review from near-duplicate review for easier tuning.
- **Header Layout Polish**: Refined header wrapping, select sizing, breadcrumb behavior, and selected-folder responsiveness so the new review controls fit cleanly in the main UI.

---

## v1.0.23

### Added

- **MediaLens Brand Assets**: Added the new MediaLens logo set and multi-resolution ICO packaging assets for the app, installer, taskbar, and Start menu.

### Changed

- **MediaLens Rebrand**: Updated the app name across the header, window title, About dialog, DevTools window, installer, and packaged release outputs so shipped builds consistently present MediaLens.
- **Theme-Aware Header Branding**: Swapped the header logo to the new MediaLens light and dark variants while preserving theme-aware sidebar toggle behavior.
- **Release Packaging Names**: Renamed the build spec, packaged executable, installer output, and related workflow/docs references to the MediaLens naming scheme.
- **Update and Repo Links**: Pointed in-app update checks, installer downloads, Help menu links, and release documentation to the renamed G1enB1and/MediaLens GitHub repository.

---

## v1.0.22

### Added

- **Bottom AI Panel Shell**: Added a new hideable and resizable bottom panel with persisted visibility and size so the upcoming AI chat area has a dedicated place in the layout.
- **Explorer-Style Address Bar**: Replaced the simple selected-folder label with a full Windows Explorer-style address bar that shows the full path as clickable breadcrumbs.
- **Breadcrumb Folder Menus**: Added dropdown chevrons between breadcrumb segments and at the end of the current path so nearby folders can be opened directly from the address bar.

### Changed

- **Navigation Responsiveness**: Moved breadcrumb folder enumeration, gallery counts, and gallery listing requests off the UI thread so folder navigation is less likely to freeze the app.
- **Tree Sync Scheduling**: Changed native tree synchronization so folder navigation updates the selected folder first and coalesces heavier tree sync work behind a deferred timer instead of doing it immediately on every navigation.
- **Address Bar Interaction**: Added editable-path mode plus keyboard navigation and lazy-expanding flyout menus so the address bar behaves much closer to Windows Explorer.
- **Header Wrapping**: Updated the header layout so pagination drops below the address bar on narrower widths instead of overlapping it.
- **Release Build Safety**: Hardened the release build flow to catch stale packaged artifacts before producing an installer and kept `setup.cfg` versioning in sync during version bumps.

---

## v1.0.21

### Added

- **Explorer-Style Folder Navigation**: Added `Back`, `Up`, `Forward`, and `Refresh` controls beside the selected-folder readout for faster folder browsing.

### Changed

- **Context Menu Placement**: Refined right-click menu positioning so menus stay fully visible on screen instead of getting clipped near the bottom or edges.
- **Native Drag Preview Overhaul**: Replaced the Windows shell drag preview with a native in-app drag stack that keeps original aspect ratios, supports larger previews, and positions the preview/tooltip stack cleanly beside the cursor.
- **Multi-Item Drag Stacks**: Multi-select drags now show overlapping preview thumbnails so stacked drags communicate that multiple files are moving or copying.
- **Left Tree Navigation Behavior**: Restored the file tree so normal folder navigation highlights subfolders without re-rooting the tree unexpectedly.

---

## v1.0.20

### Added

- **Metadata Detail Group Headings**: Added `General`, `Camera`, and `AI` section headings to the single-item metadata details panel so dense metadata is easier to scan.

### Changed

- **Gallery Folder Drag and Drop**: Fixed dragging files from the gallery into folder cards shown inside the gallery, while preserving cancel behavior when dropping back on the same item or gallery background.
- **Timeline Polish Pass**: Added active/visible/dim anchor emphasis, corrected the bottom-of-gallery anchor edge case, made the timeline resize against the visible gallery viewport, improved its final positioning, and cleaned up the rounded shell rendering.
- **Metadata Panel Cleanup**: Removed unwanted Qt label indentation/left rules from metadata labels and headings, kept detail-only group headers out of bulk/empty states, and restyled `Clear Tags From DB` to match the other bulk tag editor actions.
- **Glassmorphism Removal**: Removed the appearance toggle and remaining blur/translucency paths so the header, lightbox, and other surfaces render fully opaque without flicker around animated GIFs and videos.
- **Sidebar Divider Stability**: Refined the native sidebar splitter/divider rendering so borders and resize hover states render crisply instead of appearing too thin or flickering.

### Removed

- **Glassmorphism Setting**: Removed the `Enable glassmorphism` appearance option and its remaining runtime wiring.

---

## v1.0.19

### Added

- **What's New Release Notes**: The `What's New` dialog now shows the polished `ReleaseNotes.md` summary first, followed by the full bundled changelog for users who want the detailed breakdown.
- **Timeline Navigation Arrows**: Added dedicated up/down controls to the timeline rail so dense timelines more clearly communicate that extra dates are available above or below the current viewport.

### Changed

- **Timeline Navigation Overhaul**: Rebuilt the grouped-date timeline to use one anchor per real date header, unified tooltip behavior, smoother drag and wheel scrubbing, a hybrid viewported anchor rail for dense timelines, and granularity-specific sizing for day, month, and year modes.
- **Infinite Scroll Policy**: Switched grouped-date non-masonry views plus `List`, `Details`, `Content`, `Small Grid`, and `Medium Grid` to infinite scroll so timeline navigation and long-form browsing are no longer broken up by pagination.
- **Header Responsiveness**: Moved the panel toggle and settings buttons beside Search and reworked the header layout so the controls wrap more cleanly on narrower widths instead of clipping off the right edge.
- **Bundled Help Content**: Packaged `SEARCH_SYNTAX.md` and `ReleaseNotes.md` with installed builds so help/release dialogs work outside the raw development environment.
- **Startup Folder Settings**: Corrected startup-folder settings state so the Browse button and related controls stay enabled/disabled based on the real `restore_last` setting.

---

## v1.0.18

### Changed

- **Details Header Layout**: Refined regular and grouped Details header spacing, sticky positioning, separator styling, and scroll-state behavior so both modes align cleanly without visible jumps or header gaps.
- **Grouped Details Columns**: Fixed grouped-by-date Details mode so the shared resizable header stays aligned with filenames, folders, sizes, and other row data below it while resizing.
- **Sidebar Width Persistence**: Corrected sidebar state persistence so reopening panels restores their previous usable widths instead of saving and restoring zero-width sidebars.
- **WebEngine Startup Stability**: Deferred the initial WebEngine background-color setup until after the event loop starts, avoiding native startup aborts seen on some installed Windows machines.

---

## v1.0.17

### Added

- **Crash Diagnostics**: Added local crash-report generation, `faulthandler` logging, and Help menu actions to create a diagnostic report or open the crash-report folder for troubleshooting installed builds on other machines.

### Changed

- **Packaged Runtime Stability**: Hardened packaged startup/runtime behavior by normalizing AI metadata values before JSON persistence, preventing scan-time failures from non-serializable EXIF values like Pillow `IFDRational`.
- **Details Panel States**: Updated the right sidebar so it shows a true empty-state prompt when nothing is selected and switches to a dedicated bulk tag editor when multiple files are selected.
- **Bulk Tag Editing**: Refined bulk tag save/embed behavior so entered tags append to existing DB and embedded file tags instead of replacing them.

---

## v1.0.16

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
  - Fixed SVG rendering for the **â€œApply to allâ€** checkbox so the checkmark displays correctly in all themes.
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
  - **Ctrl+C / Ctrl+X / Ctrl+V** â€” Copy, Cut, Paste files and folders
  - **Delete** â€” Delete selected items with confirmation
  - **F2** â€” Rename selected items (inline for folders, dialog for gallery)
  - **Ctrl+A** â€” Select all gallery items

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
- **Help Dialogs**: Added **Terms of Service** and **Whatâ€™s New** windows in the Help menu.

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

- Initial MediaLens project scaffold and Python package layout.
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

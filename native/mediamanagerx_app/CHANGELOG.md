# What's New in MediaManagerX

## v1.0.4 (Current)

### Added

- **Gallery Drag & Drop**: Support for dropping files/folders from Windows File Explorer or the internal tree directly into the gallery area.
- **Standard Key Bindings**: Focus-aware support for standard shortcuts:
  - **Ctrl+C / Ctrl+X / Ctrl+V**: Copy, Cut, and Paste operations.
  - **Ctrl+A**: Select All items in the current view.
  - **Del**: Delete selected items with confirmation.
  - **F2**: Rename selected media or folders.
- **Conflict Resolution**: New comparison dialog for managing file collisions during move/copy operations.
- **Enhanced Tooltips**: Custom themed tooltips ("Move to..." / "Copy to...") that follow the cursor during drag operations.

### Changed

- **Context Menu Coverage**: Expanded the clickable background area in the gallery to ensure the app-level context menu shows even when clicking far below images.
- **Native Tooltip Suppression**: Fixed a "double tooltip" issue where Windows would show a secondary drop description behind the custom app tooltip.
- **File Tree UX**: Added a hand pointer cursor when hovering over clickable folders and files for clearer feedback.
- **Dialog Aesthetics**: Refined the conflict dialog with stronger accent-tinted hover effects on buttons and fixed checkbox SVG rendering.
- **Layout Adjustments**: Fixed vertical clipping of long filenames in the conflict resolution window.
- **Stability**: Improvements to multi-file transfer logic and focus management during shortcut execution.

## v1.0.3

### Added

- **Focus Awareness**: Shortcuts automatically prioritize text input (like tags/description) when a field is focused.
- **Persistent Layout**: The application now remembers preferred sidebar widths across sessions.

### Changed

- **Enhanced Drag & Drop**:
  - **Multi-file Support**: Improved ability to move or copy multiple selections simultaneously.
  - **Modifier Keys**: "Move" is now default; holding **Ctrl** toggles to "Copy".
  - **Visual Feedback**: Improved drag thumbnails with a slight offset from the cursor for better visibility.
- **Gallery Selection Stability**: Fixed issues where items would deselect incorrectly when interacting with the right sidebar or opening context menus.
- **Reliable Refresh**: Gallery now removes items and refreshes immediately after successful file operations.
- **Metadata Parity**: Fixed tag and comment embedding (XMP/EXIF) to ensure full visibility within native Windows File Properties.
- **Scrollbar Aesthetics**: Softened native scrollbar hover effects to better match the web-based gallery design.
- **Bug Fixes**:
  - Resolved `AttributeError` in native shortcut handling logic.
  - Fixed inconsistent theme colors in the metadata and bulk tagging panels.

## v1.0.2

### Added

- **Auto-Update System**: Integrated version checking that monitors the GitHub repository on launch, with manual check support in settings.
- **Legal & Info Dialogs**: Added "Terms of Service" and "What's New" (Changelog) windows under the Help menu.

### Changed

- **Media Loading UX**: Improved stability by hiding placeholders and borders until metadata and dimensions are fully fetched.
- **Masonry Layout**: Fixed layout shifts by reserving space with correct aspect-ratio placeholders.
- **Navigation Logic**: Fixed a bug where scroll position would not reset when jumping between different folders or search results.
- **Performance**: Removed overhead from real-time GIF pausing in the lightbox to improve rendering speed.
- **UI Refinements**:
  - Help dialogs now use themed, tinted backgrounds matching the active mode.
  - Fixed contrast issues on buttons in light mode for improved accessibility.
  - Enabled native Markdown rendering for all informational documents.
- **About Window**: Refined the About dialog with detailed version and author information.

## v1.0.1-alpha

### Added

- Project scaffold and Python package layout for MediaManager Phase 1.
- SQLite schema bootstrap and init script (`scripts/init_db.py`).
- Windows path normalization utilities and scope checks.
- Folder scope query builder and selection-state helpers.
- Foundation repositories for media ingest/query, metadata CRUD, and tag CRUD.
- Repository facade (`MediaRepository`) for native UI integration seam.
- Unit test suite covering foundation modules.
- Dev validation helper (`scripts/dev_check.py`).
- First-run DB bootstrap helper (`scripts/setup.py`) and auto-init DB connector (`app/mediamanager/db/connect.py`).
- Project hygiene via `.gitignore` and `Makefile` convenience targets.
- App bootstrap CLI support for custom DB locations via `--db-path`.
- Initial container-first masonry layout helper and design documentation.

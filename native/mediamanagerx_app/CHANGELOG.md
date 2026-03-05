## v1.0.5 (Current)

### Changed

- **File Tree Fix**: Improved path normalization and initialization robustness to ensure the file tree is visible in the packaged installer environment.
- **Improved Logging**: Added detailed initialization logging to help diagnose environment-specific path issues.

---

## v1.0.4

### Added

- **Gallery Drag & Drop**: Drag and drop files or folders from Windows File Explorer directly into the gallery area with the same behavior and styling as the file tree.
- **Conflict Comparison Dialog**: Added a popup dialog when copying or moving files to a destination containing an existing filename, allowing context comparison before resolving the conflict.

### Changed

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

### Added

- **Keyboard Shortcuts**:
  - **Ctrl+C / Ctrl+X / Ctrl+V** — Copy, Cut, Paste files and folders
  - **Delete** — Delete selected items with confirmation
  - **F2** — Rename selected items (inline for folders, dialog for gallery)
  - **Ctrl+A** — Select all gallery items

### Changed

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

### Added

- **Auto-Update System**: App now checks GitHub for updates on launch (manual check available).
- **Help Dialogs**: Added **Terms of Service** and **What’s New** windows in the Help menu.

### Changed

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

### Added

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

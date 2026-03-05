# What's New in MediaManagerX

## v1.0.4 (Current)

- **UI & Navigation**:
  - **Interactive File Tree**: Cursor now changes to a hand pointer when hovering over clickable folders and files for better visual feedback.
- **Conflict Resolution Improvements**:
  - **Themed Checkboxes**: Fixed the "Apply to all" checkbox SVG rendering to ensure a clear checkmark is visible in all themes.
  - **Refined Dialog Aesthetics**: Stronger hover effects on buttons for clearer interaction.
  - **Layout Fixes**: Resolved vertical clipping of long filenames in the conflict dialog.
- **Improved Drag & Drop**: Refined logic for multi-file transfers between the gallery and file tree.

## v1.0.3

- **Standard Keyboard Shortcuts**: Added global, focus-aware shortcuts:
  - **Ctrl+C/X/V**: Copy, Cut, and Paste files/folders.
  - **Del**: Delete selected items with confirmation.
  - **F2**: Rename selected items (inline for folders, prompt for gallery).
  - **Ctrl+A**: Select All items in the gallery.
- **Enhanced Drag & Drop**:
  - **Multi-file Support**: Move or copy multiple selections simultaneously.
  - **Intuitive Modifiers**: "Move" is default; hold **Ctrl** to "Copy".
  - **Dynamic Tooltips**: Real-time feedback showing "Move to [Folder]" or "Copy to [Folder]" that follows the cursor.
  - **Visual Feedback**: Improved drag thumbnails offset from the cursor for better visibility.
- **Selection & UI Stability**:
  - **Right-Click Fix**: Prevented gallery items from deselecting when opening context menus or using "Select All" from the tree.
  - **Reliable Refresh**: Gallery now automatically refreshes and removes items immediately after deletion.
  - **Focus Isolation**: Shortcuts automatically prioritize text input (like tags/description) when a field is focused.
- **Metadata & Compatibility**:
  - **Windows Explorer Parity**: Fixed tag and comment embedding (XMP/EXIF) to be fully visible in Windows File Properties.
  - **Persistent Layout**: Application now remembers your preferred sidebar widths across sessions.
- **Bug Fixes**:
  - Resolved `AttributeError` in native shortcut handlers.
  - Fixed inconsistent theme colors in metadata and bulk tagging sidebars.
  - Softened scrollbar hover effects to match web aesthetics.

## v1.0.2

- **Enhanced Media Loading**: Improved experience by hiding placeholders and borders until metadata/dimensions are fully fetched.
- **Masonry Stability**: Fixed layout shifts during scrolling by reserving space with correct aspect ratio placeholders.
- **Auto-Update System**: Integrated an auto-updater that checks the GitHub repository on launch (manual check also available).
- **Navigation Improvements**: Fixed scroll position not resetting when switching between pages or search results.
- **Performance Optimization**: Removed real-time GIF pausing in the lightbox to eliminate overhead from poster generation.
- **Legal & Info Dialogs**: Added "Terms of Service" and "What's New" (Changelog) windows under the Help menu.
- **Premium UI Refinements**:
  - All help dialogs now use themed, tinted backgrounds (matching the app's dark/light mode).
  - Fixed button contrast issues in light mode for a cleaner look.
  - Native Markdown rendering for all informational documents.
- **Main Window Improvements**: Refined the "About" window with more detailed version and author information.

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
- First-run DB bootstrap helper (`scripts/setup.py`) and auto-init DB connector (`app/mediamanager/db/connect.py`) to create a blank database automatically.
- Repo hygiene `.gitignore` for Python caches, temp test artifacts, and local runtime DB data.
- `Makefile` convenience targets (`make setup`, `make test`, `make run`) for easier first-run, validation, and smoke-run commands.
- App bootstrap CLI now supports `--db-path` for custom DB locations.
- Added `scripts/demo_ingest.py` for quick ingest + selection + scoped listing sanity checks.
- Initial container-first masonry layout helper (`app/mediamanager/layout/masonry.py`) + design doc (`docs/masonry-layout.md`).

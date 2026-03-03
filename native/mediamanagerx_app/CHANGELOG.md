# What's New in MediaManagerX

## v1.0.2 (Current)

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
# Changelog

## 0.1.0-foundation (in progress)

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

### Notes
- Current focus remains backend/data foundation for Phase 1 stability before UI wiring.

# MediaManager Backlog (Current)

## Sprint 0 — Foundation
- [x] Create project scaffold (`app/`, `native/`, `server/`, `docs/`)
- [x] Choose embedded web strategy in PySide6 (QWebEngineView vs WebView2 wrapper)
- [x] Add path normalization utility (Windows-safe, case-insensitive handling)
- [x] Add DB bootstrap/migrations for `SCHEMA_V1`

## Sprint 1 — Viewer Core
- [ ] Implement masonry container-first layout engine (container dimensions before asset load)
- [ ] Implement pagination (100 items/page)
- [ ] Implement lazy loading + near-viewport precache
- [ ] Implement playback policy:
  - [ ] GIF autoplay+loop
  - [ ] Video <1m autoplay+loop
  - [ ] Video >=1m paused with first frame + controls
- [ ] Implement shadowbox overlay (image + video)

## Sprint 2 — Folder Scope + Persistence
- [ ] Implement left tree with Explorer-like Ctrl/Shift selection
- [ ] Implement parent=>descendant inclusion rule
- [ ] Wire selected-folder scope query to gallery
- [ ] Implement metadata CRUD (tags/description/notes)
- [ ] Regression test: deselect/reselect/restart never loses metadata

## Validation gates
- [ ] No visible layout jumping during asset load
- [ ] Smooth scroll with mixed media
- [ ] Scope filtering correctness
- [ ] Metadata persistence correctness

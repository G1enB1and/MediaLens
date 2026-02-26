# MediaManager — Phase 1 Plan (Viewer + Folder Scope + Persistence)

## Phase 1 Goal

Deliver a stable local Windows app with:

- native shell + embedded web masonry gallery,
- correct folder-selection behavior (Explorer-like multi-select),
- and persistent metadata storage that is independent of current gallery selection.

---

## Locked UX Rules (from Glen)

### A) Gallery

- Masonry/Pinterest layout (not fixed grid)
- Responsive resizing
- Lazy loading + near-viewport precache
- Pagination (~100 items/page)
- GIFs: autoplay + loop
- Videos < 1 minute: autoplay + loop
- Videos >= 1 minute: paused thumbnail/first frame + controls
- Click image/video: open larger shadowbox overlay

### B) Left Folder Tree (critical)

- Explorer-like folder selection behavior:
  - Ctrl-click to add/remove individual folders from selection
  - Shift-click for range selection among visible sibling items
- Selected folders are highlighted
- Non-selected folders do not appear in gallery
- Selecting a parent folder includes subfolders by default

### C) Metadata persistence (critical)

- Tags/descriptions/notes must persist regardless of whether folders are currently selected/open in gallery.
- Selection scope controls only what is displayed, never what metadata exists.

---

## Architecture Split (Phase 1)

### Native (PySide6)

- Main app shell/window
- Left folder tree panel
- Selection state manager
- API bridge to web gallery
- Local DB read/write services

### Web (embedded view)

- Masonry renderer
- Media playback behavior rules
- Lazy loading + prefetch
- Shadowbox overlay
- Pagination UI

---

## Data Model Rules (Phase 1)

## 1) Persistent Catalog (never flushed due to UI selection)

- `media_items` (id, path, file stats, media type, duration, thumb/previews, etc.)
- `media_metadata` (media_id, title, description, notes, optional json)
- `tags` + `media_tags`
- Optional: `media_paths_history` for rename/move resilience

## 2) Workspace/Selection State (safe to change)

- `folder_index` (known folders)
- `folder_selection_state` (currently selected roots/nodes)
- Optional cache table for current page results

### Hard rule

Closing/unselecting folders must not delete metadata rows.
Even completely replacing which root folder the file tree starts in must still not reset or lose any data from previous file roots
---

## File Tree Selection Implementation Notes

1. Build canonical ordered list of currently visible tree nodes (for shift-range)
2. Ctrl-click:
   - Toggle clicked folder selected/unselected
3. Shift-click:
   - Use last anchor + current clicked node to select range
4. Parent selection:
   - Selecting a parent implies recursive include of all descendants
5. Gallery scope query:
   - Include media under any selected folder roots
   - Deduplicate when overlapping parent/child selections exist

---

## Gallery Scope Query Contract

Given selected folders S:

- Return only media whose path is under at least one folder in S
- Exclude all media outside S
- If S is empty: show empty gallery state (or configured default)

---

## Phase 1 Build Sequence

1. **Scaffold app shell + embedded web gallery host**
2. **Implement folder tree + explorer-like selection mechanics**
3. **Wire scope filtering (selected folders -> gallery feed)**
4. **Implement masonry + autoplay/loop policy + shadowbox**
5. **Add lazy load + prefetch + pagination (~100/page)**
6. **Add persistent metadata CRUD (tags/description/notes)**
7. **Validate persistence across selection changes and app restarts**

### Layout stabilization rule (locked)

- Render fixed-size/responsive **media containers first** and compute masonry placement from container dimensions before media bytes load.
- Resize/reflow containers first, then stream image/video into prepositioned containers.
- Goal: prevent layout jumping while assets load.

---

## Acceptance Criteria (Phase 1 complete)

- Folder multi-select behaves like Windows Explorer (Ctrl/Shift)
- Parent selection includes subfolders by default
- Gallery shows only selected folder content
- Masonry viewer remains smooth with mixed images/GIFs/videos
- Media playback rules by duration are correct
- Shadowbox opens for all media types
- Metadata persists when folders are deselected, reselected, and after restart
- No metadata loss when changing gallery scope

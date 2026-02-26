# MediaManager — Schema v1 (Persistent Catalog + Workspace Scope)

## Design principles
- Persistent metadata is never deleted due to folder selection changes.
- Workspace selection controls only what appears in gallery.
- Folder scope and metadata storage are separate concerns.

---

## Core tables

## 1) media_items (persistent catalog)
Stores one row per discovered media file.

```sql
CREATE TABLE media_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  media_type TEXT NOT NULL,                -- image|gif|video
  file_size_bytes INTEGER,
  modified_time_utc TEXT,
  width INTEGER,
  height INTEGER,
  duration_ms INTEGER,                     -- null for non-video
  thumb_path TEXT,
  preview_path TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE INDEX idx_media_items_path ON media_items(path);
CREATE INDEX idx_media_items_type ON media_items(media_type);
```

## 2) media_metadata (persistent, user-editable)
Holds per-media textual metadata that must persist.

```sql
CREATE TABLE media_metadata (
  media_id INTEGER PRIMARY KEY,
  title TEXT,
  description TEXT,
  notes TEXT,
  updated_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);
```

## 3) tags (persistent)
Controlled vocabulary plus user-created tags.

```sql
CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  category TEXT,                           -- context|content|style|technical|other
  created_at_utc TEXT NOT NULL
);

CREATE INDEX idx_tags_name ON tags(name);
```

## 4) media_tags (persistent many-to-many)
Attach tags to media items.

```sql
CREATE TABLE media_tags (
  media_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  created_at_utc TEXT NOT NULL,
  PRIMARY KEY (media_id, tag_id),
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX idx_media_tags_media ON media_tags(media_id);
CREATE INDEX idx_media_tags_tag ON media_tags(tag_id);
```

---

## Workspace tables (selection/view scope)

## 5) folder_nodes
Known folders from indexed roots.

```sql
CREATE TABLE folder_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  parent_path TEXT,
  depth INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_folder_nodes_parent ON folder_nodes(parent_path);
CREATE INDEX idx_folder_nodes_path ON folder_nodes(path);
```

## 6) folder_selection_state
Current selection set (drives gallery scope only).

```sql
CREATE TABLE folder_selection_state (
  path TEXT PRIMARY KEY,
  selected_at_utc TEXT NOT NULL
);
```

Notes:
- Ctrl/Shift behavior is handled in app logic; this table stores current selected set only.
- Parent selection implies descendants in scope by query logic.

---

## Query contract
Given selected folders S (`folder_selection_state.path`), gallery returns media where:
- `media_items.path` is under at least one selected folder path, and
- duplicates from overlapping parent/child selections are removed.

Pseudo condition:
- `media.path LIKE selected_path || '/%' OR media.path = selected_path` (path normalization required)

---

## Data safety invariants
1. Clearing `folder_selection_state` must not modify `media_items`, `media_metadata`, `tags`, or `media_tags`.
2. Deselecting folders only changes gallery results.
3. Metadata edits always target persistent tables keyed by `media_id`.

---

## Future-proofing (deferred)
- Stable content identity table (hash-based) for rename/move resilience.
- Optional path history table.
- Optional workspace result cache table for pagination acceleration.
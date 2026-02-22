CREATE TABLE IF NOT EXISTS media_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  content_hash TEXT,                         -- SHA-256 for identity/dedupe
  media_type TEXT NOT NULL,                -- image|gif|video
  file_size_bytes INTEGER,
  modified_time_utc TEXT,
  width INTEGER,
  height INTEGER,
  duration_ms INTEGER,
  thumb_path TEXT,
  preview_path TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_media_items_path ON media_items(path);
CREATE INDEX IF NOT EXISTS idx_media_items_hash ON media_items(content_hash);
CREATE INDEX IF NOT EXISTS idx_media_items_type ON media_items(media_type);

CREATE TABLE IF NOT EXISTS media_paths_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  media_id INTEGER NOT NULL,
  old_path TEXT NOT NULL,
  new_path TEXT NOT NULL,
  moved_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_paths_history_media ON media_paths_history(media_id);

CREATE TABLE IF NOT EXISTS media_metadata (
  media_id INTEGER PRIMARY KEY,
  title TEXT,
  description TEXT,
  notes TEXT,
  updated_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  category TEXT,
  created_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);

CREATE TABLE IF NOT EXISTS media_tags (
  media_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  created_at_utc TEXT NOT NULL,
  PRIMARY KEY (media_id, tag_id),
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_tags_media ON media_tags(media_id);
CREATE INDEX IF NOT EXISTS idx_media_tags_tag ON media_tags(tag_id);

CREATE TABLE IF NOT EXISTS folder_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  parent_path TEXT,
  depth INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_folder_nodes_parent ON folder_nodes(parent_path);
CREATE INDEX IF NOT EXISTS idx_folder_nodes_path ON folder_nodes(path);

CREATE TABLE IF NOT EXISTS folder_selection_state (
  path TEXT PRIMARY KEY,
  selected_at_utc TEXT NOT NULL
);

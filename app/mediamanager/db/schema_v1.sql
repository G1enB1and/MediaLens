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

CREATE TABLE IF NOT EXISTS media_ai_metadata (
  media_id INTEGER PRIMARY KEY,
  parser_version TEXT NOT NULL,
  normalized_schema_version TEXT NOT NULL,
  is_ai_detected INTEGER NOT NULL DEFAULT 0,
  is_ai_confidence REAL NOT NULL DEFAULT 0,
  tool_name_found TEXT,
  tool_name_inferred TEXT,
  tool_name_confidence REAL NOT NULL DEFAULT 0,
  ai_prompt TEXT,
  ai_negative_prompt TEXT,
  description TEXT,
  model_name TEXT,
  model_hash TEXT,
  checkpoint_name TEXT,
  sampler TEXT,
  scheduler TEXT,
  cfg_scale REAL,
  steps INTEGER,
  seed TEXT,
  width INTEGER,
  height INTEGER,
  denoise_strength REAL,
  upscaler TEXT,
  source_formats_json TEXT NOT NULL DEFAULT '[]',
  metadata_families_json TEXT NOT NULL DEFAULT '[]',
  ai_detection_reasons_json TEXT NOT NULL DEFAULT '[]',
  raw_paths_json TEXT NOT NULL DEFAULT '[]',
  unknown_fields_json TEXT NOT NULL DEFAULT '{}',
  updated_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media_ai_metadata_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  media_id INTEGER NOT NULL,
  family TEXT NOT NULL,
  container_type TEXT,
  path_descriptor TEXT NOT NULL,
  raw_kind TEXT NOT NULL,
  raw_text TEXT,
  raw_json TEXT,
  raw_binary_b64 TEXT,
  parse_status TEXT NOT NULL DEFAULT 'parsed',
  parser_version TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_ai_metadata_raw_media ON media_ai_metadata_raw(media_id);
CREATE INDEX IF NOT EXISTS idx_media_ai_metadata_raw_family ON media_ai_metadata_raw(family);

CREATE TABLE IF NOT EXISTS media_ai_loras (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  media_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  weight TEXT,
  hash TEXT,
  source TEXT,
  created_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_ai_loras_media ON media_ai_loras(media_id);

CREATE TABLE IF NOT EXISTS media_ai_workflows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  media_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  data_json TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_ai_workflows_media ON media_ai_workflows(media_id);

CREATE TABLE IF NOT EXISTS media_ai_provenance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  media_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  data_json TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_ai_provenance_media ON media_ai_provenance(media_id);

CREATE TABLE IF NOT EXISTS media_character_cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  media_id INTEGER NOT NULL,
  name TEXT,
  data_json TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_character_cards_media ON media_character_cards(media_id);

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

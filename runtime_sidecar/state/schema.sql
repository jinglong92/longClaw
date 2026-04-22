-- Schema for the runtime sidecar SQLite ledger

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  parent_session_id TEXT,
  platform TEXT,
  profile TEXT,
  topic_key TEXT,
  started_at TEXT DEFAULT (datetime('now')),
  ended_at TEXT,
  compacted_from TEXT
);

CREATE TABLE IF NOT EXISTS route_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  turn_id INTEGER,
  ctrl_route TEXT,
  specialists_json TEXT,
  confidence_json TEXT,
  audit_level TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tool_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  turn_id INTEGER,
  tool_name TEXT,
  args_json TEXT,
  result_ref TEXT,
  ok INTEGER,
  latency_ms INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  kind TEXT,
  content TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  goal TEXT NOT NULL,
  current_focus TEXT DEFAULT '',
  next_action TEXT DEFAULT '',
  status TEXT DEFAULT 'active',
  constraints_json TEXT DEFAULT '[]',
  related_paths_json TEXT DEFAULT '[]',
  related_urls_json TEXT DEFAULT '[]',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  summary TEXT,
  payload_json TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
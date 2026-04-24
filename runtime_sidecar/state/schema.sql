-- Schema for the runtime sidecar SQLite ledger

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  parent_session_id TEXT,
  platform TEXT,
  profile TEXT,
  topic_key TEXT,
  current_turn_count INTEGER,
  current_context_tokens INTEGER,
  context_limit_tokens INTEGER,
  context_usage_source TEXT,
  last_turn_count_at TEXT,
  last_context_usage_at TEXT,
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

CREATE TABLE IF NOT EXISTS compact_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  compacted_at TEXT DEFAULT (datetime('now')),
  turn_count_before INTEGER,
  tool_events_before INTEGER,
  trim_events_before INTEGER,
  summary_hint TEXT,
  trigger_source TEXT
);
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','paused','failed','completed','canceled')),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  parent_node_id TEXT REFERENCES nodes(id) ON DELETE SET NULL,
  attempt INT NOT NULL DEFAULT 1,
  agent_id TEXT NOT NULL,
  node_type TEXT NOT NULL CHECK (node_type IN ('router','agent','tool','aggregator','human_gate')),
  status TEXT NOT NULL CHECK (status IN ('queued','running','waiting','failed','completed','canceled')),
  input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  session_id TEXT NOT NULL,
  request_id TEXT,
  node_id TEXT,
  event_id TEXT,
  actor_type TEXT,
  agent_id TEXT,
  parent_event_id TEXT,
  seq BIGINT NOT NULL,
  event_type TEXT NOT NULL,
  metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  version_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(run_id, seq)
);

ALTER TABLE events ADD COLUMN IF NOT EXISTS request_id TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS event_id TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS actor_type TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS parent_event_id TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE events ADD COLUMN IF NOT EXISTS version_json JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_events_run_created_at ON events(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_request_id ON events(request_id);

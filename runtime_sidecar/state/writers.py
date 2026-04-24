"""
Write operations for the sidecar state ledger.

These functions encapsulate SQL statements for inserting and updating
records.  They should be used by plugins and scripts rather than executing
SQL directly elsewhere in the codebase.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

from .db import get_connection
from ..logging.logger import get_logger

logger = get_logger(__name__)

_SESSION_COLUMNS = {
    "current_turn_count": "INTEGER",
    "current_context_tokens": "INTEGER",
    "context_limit_tokens": "INTEGER",
    "context_usage_source": "TEXT",
    "last_turn_count_at": "TEXT",
    "last_context_usage_at": "TEXT",
}


def initialise_schema(conn: Optional[sqlite3.Connection] = None) -> None:
    """Create tables if they do not exist using the embedded schema file."""
    if conn is None:
        conn = get_connection()
    # Locate schema.sql relative to this file to avoid relying on
    # importlib.resources (which may not be available in older Python versions)
    import os as _os
    try:
        schema_path = _os.path.join(_os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        _ensure_session_columns(conn)
        conn.commit()
    except Exception as exc:
        logger.error("Failed to initialise schema: %s", exc)


def _ensure_session_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    for column, column_type in _SESSION_COLUMNS.items():
        if column in existing:
            continue
        conn.execute(f"ALTER TABLE sessions ADD COLUMN {column} {column_type}")


def _normalize_session_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(record)
    for key in (
        "session_id",
        "parent_session_id",
        "platform",
        "profile",
        "topic_key",
        "current_turn_count",
        "current_context_tokens",
        "context_limit_tokens",
        "context_usage_source",
        "last_turn_count_at",
        "last_context_usage_at",
        "compacted_from",
    ):
        normalized.setdefault(key, None)
    return normalized


def upsert_session(conn: sqlite3.Connection, record: Dict[str, Any]) -> None:
    """Insert or update a session record."""
    record = _normalize_session_record(record)
    sql = """
    INSERT INTO sessions (
      session_id, parent_session_id, platform, profile, topic_key,
      current_turn_count,
      current_context_tokens, context_limit_tokens, context_usage_source,
      last_turn_count_at, last_context_usage_at, compacted_from
    )
    VALUES (
      :session_id, :parent_session_id, :platform, :profile, :topic_key,
      :current_turn_count,
      :current_context_tokens, :context_limit_tokens, :context_usage_source,
      :last_turn_count_at, :last_context_usage_at, :compacted_from
    )
    ON CONFLICT(session_id) DO UPDATE SET
      parent_session_id=COALESCE(excluded.parent_session_id, sessions.parent_session_id),
      platform=COALESCE(excluded.platform, sessions.platform),
      profile=COALESCE(excluded.profile, sessions.profile),
      topic_key=COALESCE(excluded.topic_key, sessions.topic_key),
      current_turn_count=COALESCE(excluded.current_turn_count, sessions.current_turn_count),
      current_context_tokens=COALESCE(excluded.current_context_tokens, sessions.current_context_tokens),
      context_limit_tokens=COALESCE(excluded.context_limit_tokens, sessions.context_limit_tokens),
      context_usage_source=COALESCE(excluded.context_usage_source, sessions.context_usage_source),
      last_turn_count_at=COALESCE(excluded.last_turn_count_at, sessions.last_turn_count_at),
      last_context_usage_at=COALESCE(excluded.last_context_usage_at, sessions.last_context_usage_at),
      compacted_from=COALESCE(excluded.compacted_from, sessions.compacted_from)
    """
    try:
        conn.execute(sql, record)
        conn.commit()
    except Exception as exc:
        logger.error("Failed to upsert session record: %s", exc)


def insert_route_decision(
    conn: sqlite3.Connection,
    session_id: str,
    turn_id: Optional[int],
    ctrl_route: Optional[str],
    specialists_json: Optional[str],
    confidence_json: Optional[str],
    audit_level: Optional[str],
) -> None:
    sql = """
    INSERT INTO route_decisions (session_id, turn_id, ctrl_route, specialists_json, confidence_json, audit_level)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        conn.execute(sql, (session_id, turn_id, ctrl_route, specialists_json, confidence_json, audit_level))
        conn.commit()
    except Exception as exc:
        logger.error("Failed to insert route decision: %s", exc)


def insert_tool_event(
    conn: sqlite3.Connection,
    session_id: str,
    turn_id: Optional[int],
    tool_name: Optional[str],
    args_json: Optional[str],
    result_ref: Optional[str],
    ok: Optional[int],
    latency_ms: Optional[int],
) -> None:
    sql = """
    INSERT INTO tool_events (session_id, turn_id, tool_name, args_json, result_ref, ok, latency_ms)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        conn.execute(sql, (session_id, turn_id, tool_name, args_json, result_ref, ok, latency_ms))
        conn.commit()
    except Exception as exc:
        logger.error("Failed to insert tool event: %s", exc)


def insert_note(
    conn: sqlite3.Connection,
    session_id: str,
    kind: str,
    content: str,
) -> None:
    sql = "INSERT INTO notes (session_id, kind, content) VALUES (?, ?, ?)"
    try:
        conn.execute(sql, (session_id, kind, content))
        conn.commit()
    except Exception as exc:
        logger.error("Failed to insert note: %s", exc)


def insert_compact_event(
    conn: sqlite3.Connection,
    session_id: str,
    turn_count_before: Optional[int] = None,
    tool_events_before: Optional[int] = None,
    trim_events_before: Optional[int] = None,
    summary_hint: Optional[str] = None,
    trigger_source: Optional[str] = None,
) -> None:
    """Record a structured compact event when PostCompact fires.

    Fields:
    - turn_count_before: number of turns in the session before compaction
    - tool_events_before: tool_events count before compaction (from ledger)
    - trim_events_before: trim_event note count before compaction
    - summary_hint: short description of what was compacted (optional)
    - trigger_source: 'native_compaction' | 'layer2_summarize' | 'manual'
    """
    sql = """
    INSERT INTO compact_events
        (session_id, turn_count_before, tool_events_before, trim_events_before,
         summary_hint, trigger_source)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        conn.execute(sql, (
            session_id,
            turn_count_before,
            tool_events_before,
            trim_events_before,
            summary_hint,
            trigger_source,
        ))
        conn.commit()
    except Exception as exc:
        logger.error("Failed to insert compact event for %s: %s", session_id, exc)
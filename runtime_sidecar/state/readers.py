"""
Read operations for the sidecar state ledger.

These functions provide simple wrappers around SQL queries to fetch
information from the ledger.  They are used by CLI tools such as
`longclaw-status` and `session_search.py`.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Optional

from .db import get_connection
from ..logging.logger import get_logger

logger = get_logger(__name__)


def _fetch_all(sql: str, params: Iterable[Any]) -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        return cur.fetchall()
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        return []


def count_records(table: str) -> int:
    sql = f"SELECT COUNT(*) as cnt FROM {table}"
    rows = _fetch_all(sql, [])
    return int(rows[0]["cnt"]) if rows else 0


def latest_note_timestamp() -> Optional[str]:
    sql = "SELECT created_at FROM notes ORDER BY created_at DESC LIMIT 1"
    rows = _fetch_all(sql, [])
    return rows[0]["created_at"] if rows else None


def count_session_tool_events(session_id: str) -> int:
    """Return the number of tool_events recorded for a given session.

    Used by Layer 2 Summarize to decide whether compression should trigger
    for persistent sessions (threshold: > 30).
    """
    sql = "SELECT COUNT(*) as cnt FROM tool_events WHERE session_id = ?"
    rows = _fetch_all(sql, [session_id])
    return int(rows[0]["cnt"]) if rows else 0


def count_session_trim_events(session_id: str) -> int:
    """Return the number of Layer 1 trim_event notes for a given session.

    Used by Layer 2 Summarize as a secondary trigger (threshold: > 10).
    """
    sql = "SELECT COUNT(*) as cnt FROM notes WHERE session_id = ? AND kind = 'trim_event'"
    rows = _fetch_all(sql, [session_id])
    return int(rows[0]["cnt"]) if rows else 0


def should_trigger_layer2_summarize(
    session_id: str,
    session_type: str = "persistent",
    tool_event_threshold: int = 30,
    trim_event_threshold: int = 10,
) -> str:
    """Return the trigger reason if Layer 2 Summarize should fire, else ''.

    Rules (from CTRL_PROTOCOLS.md):
    - Ephemeral sessions: never trigger (return '' immediately)
    - Persistent sessions: trigger if tool_events > 30 OR trim_events > 10

    Returning the reason string avoids callers having to re-query counts
    just to build a human-readable message.
    """
    if session_type == "ephemeral":
        return ""
    tool_count = count_session_tool_events(session_id)
    if tool_count > tool_event_threshold:
        return f"tool_events={tool_count}>{tool_event_threshold}"
    trim_count = count_session_trim_events(session_id)
    if trim_count > trim_event_threshold:
        return f"trim_events={trim_count}>{trim_event_threshold}"
    return ""


def get_latest_recap(session_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recent session_recap for a session, or None.

    Important: recap.authoritative is always 0.
    Use raw_events table for audit/verification, not this.
    """
    sql = """
    SELECT * FROM session_recaps
    WHERE session_id = ?
    ORDER BY created_at DESC
    LIMIT 1
    """
    rows = _fetch_all(sql, [session_id])
    return dict(rows[0]) if rows else None


def count_session_raw_events(session_id: str) -> int:
    """Return raw_events count for a session (authoritative tool call count)."""
    sql = "SELECT COUNT(*) as cnt FROM raw_events WHERE session_id = ?"
    rows = _fetch_all(sql, [session_id])
    return int(rows[0]["cnt"]) if rows else 0


def get_latest_compact_event(session_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recent compact_event for a session, or None."""
    sql = """
    SELECT * FROM compact_events
    WHERE session_id = ?
    ORDER BY compacted_at DESC
    LIMIT 1
    """
    rows = _fetch_all(sql, [session_id])
    return dict(rows[0]) if rows else None


def search_records(table: str, query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Perform a simple LIKE search across all text columns of a table."""
    conn = get_connection()
    # Build WHERE clause: search across TEXT columns
    cur = conn.execute(f"PRAGMA table_info({table})")
    text_columns = [row[1] for row in cur.fetchall() if row[2].upper() == "TEXT"]
    if not text_columns:
        return []
    like_expr = " OR ".join([f"{col} LIKE ?" for col in text_columns])
    params = [f"%{query}%"] * len(text_columns)
    sql = f"SELECT * FROM {table} WHERE {like_expr} LIMIT ?"
    params.append(limit)
    try:
        cur2 = conn.execute(sql, params)
        rows = cur2.fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("Failed to search records: %s", exc)
        return []
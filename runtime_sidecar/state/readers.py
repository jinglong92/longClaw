"""
Read operations for the sidecar state ledger.

These functions provide simple wrappers around SQL queries to fetch
information from the ledger.  They are used by CLI tools such as
`longclaw-status` and `session_search.py`.
"""

from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------

def get_active_project() -> Optional[Dict[str, Any]]:
    """Return the most recently updated active project, or None."""
    sql = """
    SELECT * FROM projects
    WHERE status = 'active'
    ORDER BY updated_at DESC
    LIMIT 1
    """
    rows = _fetch_all(sql, [])
    if not rows:
        return None
    row = dict(rows[0])
    # Deserialise JSON fields
    for field in ("constraints_json", "related_paths_json", "related_urls_json"):
        key = field.replace("_json", "")
        try:
            row[key] = json.loads(row.pop(field, "[]") or "[]")
        except (json.JSONDecodeError, TypeError):
            row[key] = []
    return row


def get_recent_project_events(project_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Return the most recent events for a project."""
    sql = """
    SELECT event_id, project_id, event_type, summary, payload_json, created_at
    FROM project_events
    WHERE project_id = ?
    ORDER BY created_at DESC
    LIMIT ?
    """
    rows = _fetch_all(sql, [project_id, limit])
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["payload"] = json.loads(d.pop("payload_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["payload"] = {}
        result.append(d)
    return result


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
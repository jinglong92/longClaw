"""
Write operations for the sidecar state ledger.

These functions encapsulate SQL statements for inserting and updating
records.  They should be used by plugins and scripts rather than executing
SQL directly elsewhere in the codebase.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from .db import get_connection
from ..logging.logger import get_logger

logger = get_logger(__name__)


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
        conn.commit()
    except Exception as exc:
        logger.error("Failed to initialise schema: %s", exc)


def upsert_session(conn: sqlite3.Connection, record: Dict[str, Optional[str]]) -> None:
    """Insert or update a session record."""
    sql = """
    INSERT INTO sessions (session_id, parent_session_id, platform, profile, topic_key, compacted_from)
    VALUES (:session_id, :parent_session_id, :platform, :profile, :topic_key, :compacted_from)
    ON CONFLICT(session_id) DO UPDATE SET
      parent_session_id=excluded.parent_session_id,
      platform=excluded.platform,
      profile=excluded.profile,
      topic_key=excluded.topic_key,
      compacted_from=excluded.compacted_from
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


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------

def upsert_project(
    conn: sqlite3.Connection,
    project_id: str,
    name: str,
    goal: str,
    current_focus: str = "",
    next_action: str = "",
    status: str = "active",
    constraints: Optional[List[str]] = None,
    related_paths: Optional[List[str]] = None,
    related_urls: Optional[List[str]] = None,
) -> None:
    """Insert or update a project record."""
    sql = """
    INSERT INTO projects (
        project_id, name, goal, current_focus, next_action, status,
        constraints_json, related_paths_json, related_urls_json, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ON CONFLICT(project_id) DO UPDATE SET
        name=excluded.name,
        goal=excluded.goal,
        current_focus=excluded.current_focus,
        next_action=excluded.next_action,
        status=excluded.status,
        constraints_json=excluded.constraints_json,
        related_paths_json=excluded.related_paths_json,
        related_urls_json=excluded.related_urls_json,
        updated_at=excluded.updated_at
    """
    try:
        conn.execute(sql, (
            project_id,
            name,
            goal,
            current_focus,
            next_action,
            status,
            json.dumps(constraints or [], ensure_ascii=False),
            json.dumps(related_paths or [], ensure_ascii=False),
            json.dumps(related_urls or [], ensure_ascii=False),
        ))
        conn.commit()
    except Exception as exc:
        logger.error("Failed to upsert project %s: %s", project_id, exc)


def insert_project_event(
    conn: sqlite3.Connection,
    project_id: str,
    event_type: str,
    summary: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a project event (e.g. research_writeback, code_writeback, status_change)."""
    sql = """
    INSERT INTO project_events (project_id, event_type, summary, payload_json)
    VALUES (?, ?, ?, ?)
    """
    try:
        conn.execute(sql, (
            project_id,
            event_type,
            summary,
            json.dumps(payload or {}, ensure_ascii=False) if payload else None,
        ))
        conn.commit()
    except Exception as exc:
        logger.error("Failed to insert project event for %s: %s", project_id, exc)
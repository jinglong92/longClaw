"""
Plugin for handling the SessionStart hook.

When a new session begins, this plugin records the session information in the
sidecar ledger and checks for pending heartbeat states.  It also injects
protocol reminders by returning a message for the host to consume.
"""

import json
import os
import uuid
from typing import Any, Dict

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, session_state, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.SESSION_START.value]


def _load_heartbeat() -> str:
    """Inspect heartbeat-state.json and return a message if P0/P1 exist.

    Reads the current format written by heartbeat-agent:
      { "has_pending": bool, "pending_items": [{"priority": "P0"|"P1", ...}] }
    """
    heartbeat_path = os.path.join(os.getcwd(), "memory", "heartbeat-state.json")
    if not os.path.exists(heartbeat_path):
        return ""
    try:
        with open(heartbeat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("has_pending") and any(
            i.get("priority") in ("P0", "P1") and not i.get("shown")
            for i in data.get("pending_items", [])
        ):
            return (
                "[heartbeat] 有待处理事项，请在本轮回复开头读取 "
                "memory/heartbeat-state.json 并呈现 P0/P1 pending_items"
            )
    except Exception as exc:
        logger.warning("Failed to parse heartbeat-state.json: %s", exc)
    return ""


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle SessionStart.

    Expected context keys (if provided by host):
    - session_id: unique identifier for the session.
    - parent_session_id: ID of the parent session.
    - platform: platform name (e.g. "Mac mini").
    - profile: user profile JSON string.
    - topic_key: conversation topic.
    - current_turn_count: current turn count for this session (optional)
    - current_context_tokens: current assembled context tokens (optional)
    - context_limit_tokens: context budget ceiling, e.g. 200000 (optional)
    - context_usage_source: source label such as host_exact (optional)
    """
    # Ensure database is initialised
    conn = db.get_connection()
    writers.initialise_schema(conn)

    # Determine session ID.  If none provided, generate a sidecar ID.
    session_id = context.get("session_id")
    if not session_id:
        session_id = f"sidecar-{uuid.uuid4()}"
        logger.info("Generated sidecar session_id %s", session_id)

    turn_count = session_state.extract_turn_count(context)
    session_record = {
        "session_id": session_id,
        "parent_session_id": context.get("parent_session_id"),
        "platform": context.get("platform"),
        "profile": context.get("profile"),
        "topic_key": context.get("topic_key"),
        **turn_count,
        **session_state.extract_context_usage(context),
        "compacted_from": None,
    }

    writers.upsert_session(conn, session_record)
    session_state.merge_turn_count(session_id=session_id, **turn_count)
    session_state.merge_context_usage(session_id=session_id, **session_state.extract_context_usage(context))

    # Check heartbeat state for critical alerts
    heartbeat_msg = _load_heartbeat()

    # Compose a message reminding to review protocols and dev log.  We simply
    # return a structured dict for the host or CLI to display.
    msg = {
        "message": "Session started. Protocols injected.",
        "heartbeat": heartbeat_msg,
        "session_id": session_id,
        **turn_count,
        **session_state.extract_context_usage(context),
    }
    return msg
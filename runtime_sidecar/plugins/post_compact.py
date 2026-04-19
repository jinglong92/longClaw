"""
Plugin for handling the PostCompact hook.

This plugin records a note indicating that a compact operation occurred.  It
also reinjects protocol reminders by returning a message.  In a real
environment this might restore context after compaction.
"""

from datetime import datetime
from typing import Any, Dict

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.POST_COMPACT.value]


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PostCompact.

    Records a compact note in the ledger and returns a protocol reminder.
    Expected context keys:
    - session_id: session identifier.
    """
    conn = db.get_connection()
    writers.initialise_schema(conn)
    session_id = context.get("session_id")
    if session_id:
        writers.insert_note(conn, session_id=session_id, kind="compact", content="PostCompact triggered")
    else:
        logger.warning("PostCompact called without session_id in context")
    return {
        "message": "PostCompact complete. Protocols reinjected.",
        "session_id": session_id,
    }
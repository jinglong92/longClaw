"""
Plugin for handling the FileChanged hook.

This plugin inspects a list of changed files and notifies the user if any
important protocol files have been modified.  It logs a note in the ledger
for auditing.
"""

from typing import Any, Dict, List

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.FILE_CHANGED.value]


IMPORTANT_FILES = {
    "AGENTS.md",
    "MULTI_AGENTS.md",
    "CTRL_PROTOCOLS.md",
    "DEV_LOG.md",
}


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle FileChanged.

    Context keys:
    - session_id: current session ID.
    - files: a list of file paths that changed.
    """
    conn = db.get_connection()
    writers.initialise_schema(conn)
    session_id = context.get("session_id")
    files: List[str] = context.get("files", []) or []
    if session_id:
        writers.insert_note(conn, session_id=session_id, kind="file_changed", content=",".join(files))
    important = [f for f in files if any(f.endswith(name) for name in IMPORTANT_FILES)]
    if important:
        return {
            "message": f"Important protocol files changed: {', '.join(important)}. Please re-read them.",
            "session_id": session_id,
        }
    return {"message": "File changes detected.", "session_id": session_id}
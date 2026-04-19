"""
Plugin for handling the PreToolUse hook.

Records tool invocations in the sidecar ledger. When the host does not pass
``session_id`` (common in real OpenClaw flows), we synthesize a ``sidecar-…``
session so events still persist instead of only appearing in logs.
"""

import uuid
from typing import Any, Dict

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.PRE_TOOL_USE.value]


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle PreToolUse.

    Context keys:
    - session_id: current session ID.
    - tool_name: name of the tool being invoked (e.g. "bash").
    - args: argument string or structure passed to the tool.
    """
    conn = db.get_connection()
    writers.initialise_schema(conn)

    session_id = context.get("session_id")
    if not session_id:
        session_id = f"sidecar-{uuid.uuid4()}"
        writers.upsert_session(
            conn,
            {
                "session_id": session_id,
                "parent_session_id": None,
                "platform": context.get("platform"),
                "profile": context.get("profile"),
                "topic_key": context.get("topic_key"),
                "compacted_from": None,
            },
        )

    tool_name = context.get("tool_name")
    args = context.get("args")

    writers.insert_tool_event(
        conn,
        session_id=session_id,
        turn_id=context.get("turn_id"),
        tool_name=tool_name,
        args_json=str(args),
        result_ref=None,
        ok=1,
        latency_ms=None,
    )

    if tool_name == "bash" and isinstance(args, str) and " rm " in args and "-i" not in args:
        safe_args = args.replace(" rm ", " rm -i ")
        return {
            "message": "Unsafe rm detected; added -i flag for interactive deletion.",
            "modified_args": safe_args,
            "session_id": session_id,
        }

    return {"session_id": session_id}

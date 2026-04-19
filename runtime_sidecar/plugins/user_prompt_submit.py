"""
Plugin for UserPromptSubmit hook.

Records the user prompt turn in the ledger (session upsert + note). Used when
the host does not fire SessionStart; initialization is driven from the bridge.
"""

import json
import os
from typing import Any, Dict

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.USER_PROMPT_SUBMIT.value]


def _load_heartbeat_message() -> str:
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
    conn = db.get_connection()
    writers.initialise_schema(conn)

    # Bridge passes a stable id (host env or literal sidecar-host-unknown).
    session_id = context.get("session_id") or "sidecar-host-unknown"

    writers.upsert_session(
        conn,
        {
            "session_id": session_id,
            "parent_session_id": context.get("parent_session_id"),
            "platform": context.get("platform"),
            "profile": context.get("profile"),
            "topic_key": context.get("topic_key"),
            "compacted_from": None,
        },
    )

    prompt_preview = context.get("prompt_preview") or ""
    if isinstance(prompt_preview, str):
        preview = prompt_preview[:500]
    else:
        preview = ""

    writers.insert_note(
        conn,
        session_id=session_id,
        kind="user_prompt_submit",
        content=preview,
    )

    return {
        "message": "UserPromptSubmit recorded.",
        "heartbeat": _load_heartbeat_message(),
        "session_id": session_id,
    }

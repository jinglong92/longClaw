"""
Plugin for UserPromptSubmit hook.

Records the user prompt turn in the ledger (session upsert + note).  Also
checks whether Layer 2 Summarize should trigger for the current session and,
if so, injects a prompt hint asking CTRL to run the summarize flow.

Layer 2 trigger logic (from CTRL_PROTOCOLS.md):
- Only for persistent sessions (session_type != 'ephemeral')
- Condition: tool_events > 30 OR trim_events > 10 in this session
- When triggered: inject a hint into the return message so CTRL sees it
  at the start of the next turn and can execute the summarize flow
"""

import json
import os
from typing import Any, Dict

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, readers, session_state, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.USER_PROMPT_SUBMIT.value]

_SCHEMA_INITIALISED = False


def _ensure_schema() -> None:
    global _SCHEMA_INITIALISED
    if not _SCHEMA_INITIALISED:
        conn = db.get_connection()
        writers.initialise_schema(conn)
        _SCHEMA_INITIALISED = True


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


def _load_session_type(session_id: str) -> str:
    """Read session_type from memory/session-state.json.

    Returns 'ephemeral' or 'persistent' (default).
    Falls back to 'persistent' on any read/parse error.
    """
    state_path = os.path.join(os.getcwd(), "memory", "session-state.json")
    if not os.path.exists(state_path):
        return "persistent"
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("session_type", "persistent")
    except Exception as exc:
        logger.warning("Failed to read session-state.json: %s", exc)
        return "persistent"


def _build_layer2_hint(session_id: str) -> str:
    """Return a Layer 2 Summarize hint string if conditions are met, else ''.

    Calls should_trigger_layer2_summarize once; uses its reason string directly
    to avoid redundant count queries.
    """
    session_type = _load_session_type(session_id)
    reason = readers.should_trigger_layer2_summarize(session_id, session_type=session_type)
    if not reason:
        return ""
    return (
        f"[layer2-summarize] 上下文压力触发（{reason}）。"
        "请在本轮回复前执行 Layer 2 Summarize："
        "生成摘要块替换中间历史，保护 system prompt + 前3条 + 后8条，"
        "格式：目标/进展/决策/下一步/关键实体，"
        "完成后写入 session-state.json（compression_count += 1, last_compression_at）。"
    )


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_schema()
    conn = db.get_connection()

    session_id = context.get("session_id") or "sidecar-host-unknown"
    turn_count = session_state.extract_turn_count(context)
    context_usage = session_state.extract_context_usage(context)

    writers.upsert_session(
        conn,
        {
            "session_id": session_id,
            "parent_session_id": context.get("parent_session_id"),
            "platform": context.get("platform"),
            "profile": context.get("profile"),
            "topic_key": context.get("topic_key"),
            **turn_count,
            **context_usage,
            "compacted_from": None,
        },
    )
    session_state.merge_turn_count(session_id=session_id, **turn_count)
    session_state.merge_context_usage(session_id=session_id, **context_usage)

    prompt_preview = context.get("prompt_preview") or ""
    preview = prompt_preview[:500] if isinstance(prompt_preview, str) else ""

    writers.insert_note(
        conn,
        session_id=session_id,
        kind="user_prompt_submit",
        content=preview,
    )

    layer2_hint = _build_layer2_hint(session_id)
    if layer2_hint:
        logger.info("Layer 2 Summarize hint injected for session %s", session_id)

    return {
        "message": "UserPromptSubmit recorded.",
        "heartbeat": _load_heartbeat_message(),
        "layer2_summarize": layer2_hint,
        "session_id": session_id,
        **turn_count,
        **context_usage,
    }

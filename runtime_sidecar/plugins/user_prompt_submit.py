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
from ..state import db, readers, writers

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
        "请在本轮回复前执行 Layer 2 Summarize + 生成结构化 recap：\n"
        "1. 生成摘要块替换中间历史，保护 system prompt + 前3条 + 后8条\n"
        "2. 写入 session-state.json（compression_count += 1, last_compression_at）\n"
        "3. 生成结构化 recap 并写入 memory/recap.json，schema 要求：\n"
        "   - type: session_recap\n"
        "   - authoritative: false  ← 必须为 false，recap 不是事实源\n"
        "   - objective: 当前会话目标\n"
        "   - confirmed_facts: [] 已确认事实列表\n"
        "   - actions_taken: [] 已执行操作（含 target/result）\n"
        "   - files_touched: [] 修改过的文件\n"
        "   - open_issues: [] 未解决问题\n"
        "   - next_steps: [] 下一步行动\n"
        "   - uncertainty: [] 不确定项（假设不可写成事实）\n"
        "   - failed_attempts: [] 失败路径（防止重复踩坑）\n"
        "   - trigger: layer2\n"
        "4. 同时调用 writers.insert_session_recap() 写入 SQLite session_recaps 表\n"
        "注意：raw_events 表是工具调用的事实源，recap 不能替代它用于审计。"
    )


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_schema()
    conn = db.get_connection()

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

    tool_events = readers.count_session_tool_events(session_id)
    trim_events = readers.count_session_trim_events(session_id)

    return {
        "message": "UserPromptSubmit recorded.",
        "heartbeat": _load_heartbeat_message(),
        "layer2_summarize": layer2_hint,
        "session_id": session_id,
        "tool_events": tool_events,
        "trim_events": trim_events,
    }

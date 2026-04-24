"""
Helpers for reading and updating memory/session-state.json.

This file is intentionally small and conservative: it only merges runtime
observability fields that can later be consumed by DEV LOG, and it never
fabricates missing values.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..logging.logger import get_logger

logger = get_logger(__name__)


def _session_state_path() -> str:
    override = os.environ.get("LONGCLAW_SESSION_STATE_PATH")
    if override:
        return override
    return os.path.join(os.getcwd(), "memory", "session-state.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_state() -> Dict[str, Any]:
    path = _session_state_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to read session-state.json: %s", exc)
        return {}


def save_state(state: Dict[str, Any]) -> None:
    path = _session_state_path()
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def extract_context_usage(context: Dict[str, Any]) -> Dict[str, Any]:
    def _int_or_none(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    current_context_tokens = _int_or_none(context.get("current_context_tokens"))
    return {
        "current_context_tokens": current_context_tokens,
        "context_limit_tokens": _int_or_none(context.get("context_limit_tokens")),
        "context_usage_source": context.get("context_usage_source") or None,
        "last_context_usage_at": _utc_now() if current_context_tokens is not None else None,
    }


def extract_turn_count(context: Dict[str, Any]) -> Dict[str, Any]:
    def _int_or_none(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    current_turn_count = _int_or_none(
        context.get("current_turn_count", context.get("turn_count", context.get("turn_count_before")))
    )
    return {
        "current_turn_count": current_turn_count,
        "last_turn_count_at": _utc_now() if current_turn_count is not None else None,
    }


def merge_context_usage(
    *,
    session_id: Optional[str] = None,
    current_context_tokens: Optional[int] = None,
    context_limit_tokens: Optional[int] = None,
    context_usage_source: Optional[str] = None,
    last_context_usage_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist host-provided context usage fields without inventing values."""
    state = load_state()
    changed = False

    if session_id and state.get("session_id") != session_id:
        state["session_id"] = session_id
        changed = True

    if current_context_tokens is not None:
        state["current_context_tokens"] = current_context_tokens
        state["last_context_usage_at"] = last_context_usage_at or _utc_now()
        changed = True

    if context_limit_tokens is not None:
        state["context_limit_tokens"] = context_limit_tokens
        changed = True

    if context_usage_source:
        state["context_usage_source"] = context_usage_source
        changed = True

    if changed:
        state["updated_at"] = _utc_now()
        save_state(state)

    return state


def merge_turn_count(
    *,
    session_id: Optional[str] = None,
    current_turn_count: Optional[int] = None,
    last_turn_count_at: Optional[str] = None,
) -> Dict[str, Any]:
    state = load_state()
    changed = False

    if session_id and state.get("session_id") != session_id:
        state["session_id"] = session_id
        changed = True

    if current_turn_count is not None:
        state["current_turn_count"] = current_turn_count
        state["last_turn_count_at"] = last_turn_count_at or _utc_now()
        changed = True

    if changed:
        state["updated_at"] = _utc_now()
        save_state(state)

    return state


def format_devlog_ctx(state: Optional[Dict[str, Any]] = None) -> str:
    """Render DEV LOG ctx field from persisted session-state fields."""
    state = state if state is not None else load_state()

    def _fmt(value: Optional[int]) -> str:
        if value is None:
            return "unavailable"
        if value >= 1000:
            return f"{value // 1000}k"
        return str(value)

    current = state.get("current_context_tokens")
    limit = state.get("context_limit_tokens", 200000)
    return f"ctx={_fmt(current)}/{_fmt(limit)}"


def format_devlog_recent_turns(state: Optional[Dict[str, Any]] = None, threshold: int = 20) -> str:
    state = state if state is not None else load_state()
    current_turn_count = state.get("current_turn_count")
    if current_turn_count is None:
        return f"recent_turns=unavailable/{threshold}"
    return f"recent_turns={current_turn_count}/{threshold}"

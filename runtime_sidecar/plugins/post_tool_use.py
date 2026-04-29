"""
Plugin for handling the PostToolUse hook.

Two responsibilities:
1. Layer 1 Trim: record trim_event when output > 500 chars.
2. Model failure detection: scan output for API error signals and call
   model_config.py mark-failure / mark-success accordingly.
"""

import subprocess
import sys
import os
from typing import Any, Dict, Optional

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.POST_TOOL_USE.value]

TRIM_THRESHOLD = 500  # characters

_SCHEMA_INITIALISED = False


def _ensure_schema() -> None:
    global _SCHEMA_INITIALISED
    if not _SCHEMA_INITIALISED:
        conn = db.get_connection()
        writers.initialise_schema(conn)
        _SCHEMA_INITIALISED = True


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PostToolUse.

    Expected context keys:
    - session_id: current session identifier
    - tool_name: name of the tool that just ran
    - output: the raw tool output string
    - output_length: pre-computed length (optional, computed here if absent)
    - turn_id: current turn number (optional)

    Returns a dict with:
    - trimmed: bool — whether truncation was applied
    - output_length: int — original output length
    - trim_threshold: int
    - session_id: str
    """
    _ensure_schema()
    conn = db.get_connection()

    session_id = context.get("session_id", "unknown")
    tool_name = context.get("tool_name", "unknown")
    output = context.get("output", "")
    raw_len = context.get("output_length")
    output_length = raw_len if raw_len is not None else len(output)
    turn_id = context.get("turn_id")

    trimmed = output_length > TRIM_THRESHOLD

    if trimmed:
        note_content = (
            f"tool={tool_name} output_length={output_length} "
            f"threshold={TRIM_THRESHOLD} trimmed=true turn={turn_id}"
        )
        writers.insert_note(
            conn,
            session_id=session_id,
            kind="trim_event",
            content=note_content,
        )
        logger.debug(
            "Layer 1 Trim: tool=%s output_length=%d session=%s",
            tool_name,
            output_length,
            session_id,
        )

    # ── Model failure detection ───────────────────────────────────────────────
    failure_signal = _detect_failure(output)
    model_action: Optional[str] = None

    if failure_signal:
        writers.insert_note(
            conn,
            session_id=session_id,
            kind="model_failure",
            content=f"tool={tool_name} signal={failure_signal!r} turn={turn_id}",
        )
        model_action = _run_model_config("mark-failure", f"--reason", failure_signal)
        logger.info(
            "Model failure detected: tool=%s signal=%r session=%s action=%s",
            tool_name, failure_signal, session_id, model_action,
        )
    elif output and not trimmed:
        # Non-empty, non-truncated output with no error signal → success hint
        # Only call mark-success for the tool most likely to surface API errors
        if tool_name in ("WebFetch", "WebSearch", "Bash"):
            _run_model_config("mark-success")

    return {
        "trimmed": trimmed,
        "output_length": output_length,
        "trim_threshold": TRIM_THRESHOLD,
        "session_id": session_id,
        "model_failure_detected": bool(failure_signal),
        "model_action": model_action,
    }


def _detect_failure(output: str) -> Optional[str]:
    """Import and use model_config.detect_failure_in_output without subprocess."""
    if not output:
        return None
    try:
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from tools.model_config import detect_failure_in_output  # type: ignore
        return detect_failure_in_output(output)
    except Exception as exc:
        logger.debug("model_config import failed: %s", exc)
        return None


def _run_model_config(*args: str) -> Optional[str]:
    """Fire model_config.py as a subprocess (fire-and-forget)."""
    try:
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        script = os.path.join(repo_root, "tools", "model_config.py")
        result = subprocess.run(
            [sys.executable, script, *args],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or None
    except Exception as exc:
        logger.debug("model_config call failed: %s", exc)
        return None

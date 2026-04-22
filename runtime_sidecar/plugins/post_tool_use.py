"""
Plugin for handling the PostToolUse hook — Layer 1 Trim.

When a tool result exceeds TRIM_THRESHOLD characters, this plugin records a
structured trim_event note in the ledger.  The actual truncation in the
conversation is performed by the hook bridge script (which can inject
hookSpecificOutput); this plugin's job is to make the event observable and
persistent in the sidecar ledger.

Layer 1 Trim contract (from CTRL_PROTOCOLS.md):
- Trigger: any tool output > 500 characters, applied immediately this turn
- Action: keep first 500 chars, append truncation footnote
- Silent: does NOT increment compression_count, does NOT touch session-state.json
"""

from typing import Any, Dict

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.POST_TOOL_USE.value]

TRIM_THRESHOLD = 500  # characters


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
    conn = db.get_connection()
    writers.initialise_schema(conn)

    session_id = context.get("session_id", "unknown")
    tool_name = context.get("tool_name", "unknown")
    output = context.get("output", "")
    output_length = context.get("output_length") or len(output)
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

    return {
        "trimmed": trimmed,
        "output_length": output_length,
        "trim_threshold": TRIM_THRESHOLD,
        "session_id": session_id,
    }

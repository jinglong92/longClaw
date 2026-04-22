"""
Plugin for handling the PostCompact hook.

Records a structured compact_event in the ledger (session_id, turn_count,
tool_events_before, trim_events_before, trigger_source) instead of just a
plain "PostCompact triggered" note.

Also reinjects protocol reminders by returning a message — this is handled
by the hook bridge script (hook_dispatcher_post_compact.sh) at the bash
layer; this plugin focuses on the ledger side.

Compact state written to:
1. compact_events table (structured, queryable)
2. notes table (kind="compact", for backward-compatible log tailing)
"""

from typing import Any, Dict, Optional

from ..hook_events import HookEventType
from ..logging.logger import get_logger
from ..state import db, readers, writers

logger = get_logger(__name__)

HANDLED_EVENTS = [HookEventType.POST_COMPACT.value]


def handle_event(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PostCompact.

    Expected context keys:
    - session_id: session identifier
    - turn_count_before: turns in session before compaction (optional)
    - summary_hint: short description of what was compacted (optional)
    - trigger_source: 'native_compaction' | 'layer2_summarize' | 'manual' (optional)
    """
    conn = db.get_connection()
    writers.initialise_schema(conn)

    session_id: Optional[str] = context.get("session_id")
    if not session_id:
        logger.warning("PostCompact called without session_id in context")
        return {"message": "PostCompact: no session_id, skipped ledger write."}

    turn_count_before: Optional[int] = context.get("turn_count_before")
    summary_hint: Optional[str] = context.get("summary_hint")
    trigger_source: str = context.get("trigger_source") or "native_compaction"

    # Snapshot current sidecar counts before they reset
    tool_events_before = readers.count_session_tool_events(session_id)
    trim_events_before = readers.count_session_trim_events(session_id)

    # Write structured compact_event
    writers.insert_compact_event(
        conn,
        session_id=session_id,
        turn_count_before=turn_count_before,
        tool_events_before=tool_events_before,
        trim_events_before=trim_events_before,
        summary_hint=summary_hint,
        trigger_source=trigger_source,
    )

    # Also write backward-compatible note for log tailing
    note_content = (
        f"trigger={trigger_source} "
        f"tool_events={tool_events_before} "
        f"trim_events={trim_events_before} "
        f"turns={turn_count_before or 'unknown'}"
    )
    writers.insert_note(conn, session_id=session_id, kind="compact", content=note_content)

    logger.debug(
        "PostCompact recorded: session=%s tool_events=%d trim_events=%d trigger=%s",
        session_id,
        tool_events_before,
        trim_events_before,
        trigger_source,
    )

    return {
        "message": "PostCompact recorded. Protocols reinjected.",
        "session_id": session_id,
        "tool_events_before": tool_events_before,
        "trim_events_before": trim_events_before,
        "trigger_source": trigger_source,
    }

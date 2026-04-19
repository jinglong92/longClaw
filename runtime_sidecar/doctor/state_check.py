"""
State database checks for the longClaw sidecar.

This module performs a minimal health check on the SQLite ledger.  It
verifies that the database can be initialised and written to.  These
checks are intentionally light‑weight; they do not exhaustively test the
schema.
"""

import os
from typing import Tuple

from ..logging.logger import get_logger
from ..state import db, writers

logger = get_logger(__name__)


def check_state_db() -> Tuple[str, str]:
    """Return a status and message about the state database health."""
    try:
        conn = db.get_connection()
        writers.initialise_schema(conn)
        # Attempt to write a dummy session and delete it again
        test_id = "__healthcheck__"
        writers.upsert_session(conn, {
            "session_id": test_id,
            "parent_session_id": None,
            "platform": None,
            "profile": None,
            "topic_key": None,
            "compacted_from": None,
        })
        # Remove the dummy record
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (test_id,))
        conn.commit()
        return "PASS", f"State database is initialised at {db._determine_db_path()}."
    except Exception as exc:
        logger.error("State database check failed: %s", exc)
        return "FAIL", f"State database error: {exc}"
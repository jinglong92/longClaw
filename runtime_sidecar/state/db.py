"""
Database connection management for the sidecar.

This module provides a function to obtain a SQLite connection to the
sidecar ledger.  The database path defaults to `memory/state.db` within
the repository root but can be overridden by setting the environment
variable `LONGCLAW_STATE_DB`.  The parent directory will be created if
necessary.
"""

import os
import sqlite3
from typing import Optional

from ..logging.logger import get_logger

logger = get_logger(__name__)

_connection: Optional[sqlite3.Connection] = None


def _determine_db_path() -> str:
    """Resolve the path to the SQLite database file."""
    # Environment variable override
    env_path = os.environ.get("LONGCLAW_STATE_DB")
    if env_path:
        return env_path
    # Default to memory/state.db relative to current working directory
    return os.path.join(os.getcwd(), "memory", "state.db")


def get_connection() -> sqlite3.Connection:
    """Return a cached SQLite connection, creating it on first use."""
    global _connection
    if _connection is not None:
        return _connection
    db_path = _determine_db_path()
    # Ensure parent directory exists
    parent = os.path.dirname(db_path)
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception as exc:
            logger.warning("Failed to create directory %s: %s", parent, exc)
    # Create connection with row factory
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _connection = conn
    return conn
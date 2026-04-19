"""
State management for the runtime sidecar.

This package exposes high‑level functions for persisting and querying
session ledger data.  The underlying storage is a SQLite database stored
in the workspace under `memory/state.db` unless overridden via the
`LONGCLAW_STATE_DB` environment variable.
"""

from . import db  # noqa: F401
from . import writers  # noqa: F401
from . import readers  # noqa: F401
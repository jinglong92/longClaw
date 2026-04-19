"""
Non‑intrusive runtime sidecar for longClaw.

This package provides a thin layer that sits alongside the OpenClaw runtime to
deliver extra capabilities such as hook dispatching and a session ledger
without modifying the host.  Importing this package does not have any side
effects; use the contained modules directly.
"""

from . import hook_events  # noqa: F401
from . import event_bus    # noqa: F401
"""
Provide a uniform logger for the runtime sidecar.

This wraps the standard library logging module to configure a basic
formatter and level.  Consumers should obtain loggers via
`get_logger(__name__)`.
"""

import logging
from typing import Optional

_configured = False


def _configure_logging() -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger.  Configure logging on first call."""
    _configure_logging()
    return logging.getLogger(name)
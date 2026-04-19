#!/usr/bin/env python3
"""
Unified hook dispatcher for longClaw.

This script is invoked by `.claude/settings.json` for each hook event.  It
determines the type of event from the environment or command line
arguments, reads a JSON context payload from stdin if present and then
dispatches the event to registered plugins via the event bus.  Plugin
results are aggregated and printed as a JSON array on stdout.

If the dispatcher encounters an unknown event it will exit with a non‑zero
status and log the error.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict

from .event_bus import EventBus
from .hook_events import HookEvent, HookEventType
from .logging.logger import get_logger


logger = get_logger(__name__)


def load_context() -> Dict[str, Any]:
    """Load JSON context from stdin if available, else return empty dict."""
    try:
        if not sys.stdin.isatty():
            data = sys.stdin.read().strip()
            if data:
                return json.loads(data)
    except Exception as exc:
        logger.warning("Failed to read context from stdin: %s", exc)
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Hook dispatcher for longClaw")
    parser.add_argument(
        "event", nargs="?", help="Name of the hook event (e.g. SessionStart)", default=os.environ.get("HOOK_EVENT")
    )
    args = parser.parse_args()
    event_name = args.event
    if not event_name:
        logger.error("No event name provided via argument or HOOK_EVENT env var")
        return 1
    try:
        event_type = HookEventType.from_string(event_name)
    except ValueError as exc:
        logger.error(str(exc))
        return 1
    context = load_context()
    hook_event = HookEvent(event_type=event_type, context=context)
    bus = EventBus()
    results = bus.dispatch(hook_event)
    # Output results as JSON array
    try:
        print(json.dumps(results, default=str))
    except Exception as exc:
        logger.warning("Failed to serialise plugin results to JSON: %s", exc)
        print("[]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
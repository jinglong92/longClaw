"""
Definitions for hook events.

This module centralises the names of events that the dispatcher understands.
New events should be added here to ensure a single source of truth.

An event consists of:

* `name`: the identifier of the hook event (e.g. "SessionStart").
* `context`: an opaque dictionary containing metadata passed by the host.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class HookEventType(str, Enum):
    """Enumeration of supported hook event types."""

    SESSION_START = "SessionStart"
    POST_COMPACT = "PostCompact"
    FILE_CHANGED = "FileChanged"
    PRE_TOOL_USE = "PreToolUse"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"

    @classmethod
    def from_string(cls, name: str) -> "HookEventType":
        """Return the enumeration member for the given name or raise ValueError."""
        try:
            return cls(name)
        except ValueError:
            raise ValueError(f"Unsupported hook event type: {name}")


@dataclass
class HookEvent:
    """Container for a hook event dispatched via the dispatcher."""

    event_type: HookEventType
    context: Dict[str, Any]
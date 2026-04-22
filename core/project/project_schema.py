"""
Minimal Project schema for longClaw project-based workspace.

A Project captures the persistent context for a long-running task so that
CTRL can restore situational awareness across sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


# Valid status values — kept as strings for simplicity (no enum overhead)
PROJECT_STATUSES = ("active", "paused", "completed", "archived")


@dataclass
class Project:
    """Minimal project record.

    Fields are intentionally kept small.  Do not add task sub-objects here;
    use current_focus + next_action + status as the task state proxy.
    """

    project_id: str
    name: str
    goal: str

    # Operational context
    current_focus: str = ""
    next_action: str = ""
    status: str = "active"  # one of PROJECT_STATUSES

    # Constraints and scope hints (free-text list)
    constraints: List[str] = field(default_factory=list)

    # Related local paths and URLs for quick retrieval
    related_paths: List[str] = field(default_factory=list)
    related_urls: List[str] = field(default_factory=list)

    # Timestamps (ISO-8601 strings for JSON serialisability)
    created_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())

    def touch(self) -> None:
        """Refresh updated_at to now."""
        self.updated_at = _now_iso()

    def validate(self) -> None:
        """Raise ValueError if the record is malformed."""
        if not self.project_id:
            raise ValueError("project_id must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.goal:
            raise ValueError("goal must not be empty")
        if self.status not in PROJECT_STATUSES:
            raise ValueError(
                f"status must be one of {PROJECT_STATUSES}, got {self.status!r}"
            )

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "goal": self.goal,
            "current_focus": self.current_focus,
            "next_action": self.next_action,
            "status": self.status,
            "constraints": self.constraints,
            "related_paths": self.related_paths,
            "related_urls": self.related_urls,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(
            project_id=data["project_id"],
            name=data["name"],
            goal=data["goal"],
            current_focus=data.get("current_focus", ""),
            next_action=data.get("next_action", ""),
            status=data.get("status", "active"),
            constraints=data.get("constraints", []),
            related_paths=data.get("related_paths", []),
            related_urls=data.get("related_urls", []),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

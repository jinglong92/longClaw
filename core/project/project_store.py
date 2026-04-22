"""
Local JSON-backed store for Project records.

Persists to `memory/projects.json` by default (overridable via
LONGCLAW_PROJECTS_FILE env var).  All operations are synchronous and
single-process safe — no locking needed for the current single-agent use case.

Usage:
    store = ProjectStore()
    project = store.get("my-project-id")
    store.save(project)
    store.list_all()
    store.delete("my-project-id")
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .project_schema import Project


_DEFAULT_FILENAME = "projects.json"


def _resolve_store_path() -> str:
    env = os.environ.get("LONGCLAW_PROJECTS_FILE")
    if env:
        return env
    return os.path.join(os.getcwd(), "memory", _DEFAULT_FILENAME)


class ProjectStore:
    """Read/write Project records to a local JSON file."""

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or _resolve_store_path()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, project_id: str) -> Optional[Project]:
        """Return the project with the given ID, or None."""
        data = self._load()
        record = data.get(project_id)
        if record is None:
            return None
        return Project.from_dict(record)

    def save(self, project: Project) -> None:
        """Persist a project (insert or update)."""
        project.validate()
        project.touch()
        data = self._load()
        data[project.project_id] = project.to_dict()
        self._dump(data)

    def delete(self, project_id: str) -> bool:
        """Remove a project.  Returns True if it existed."""
        data = self._load()
        if project_id not in data:
            return False
        del data[project_id]
        self._dump(data)
        return True

    def list_all(self) -> List[Project]:
        """Return all projects sorted by updated_at descending."""
        data = self._load()
        projects = [Project.from_dict(v) for v in data.values()]
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    def get_active(self) -> Optional[Project]:
        """Return the most recently updated active project, or None."""
        for p in self.list_all():
            if p.status == "active":
                return p
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, dict]:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _dump(self, data: Dict[str, dict]) -> None:
        parent = os.path.dirname(self._path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

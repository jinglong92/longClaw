"""
Configuration checks for the longClaw workspace.

This module encapsulates logic for validating the presence and content
of `.claude/settings.json` and related configuration files.  It does not
attempt to modify any configuration; it simply reports potential issues.
"""

import json
import os
from typing import Dict, Tuple

from ..logging.logger import get_logger

logger = get_logger(__name__)


def check_hooks_configuration() -> Tuple[str, str]:
    """
    Check whether `.claude/settings.json` exists and appears to be configured
    to use the hook dispatcher.  Returns a status (PASS/WARN/FAIL) and a
    message.

    The dispatcher requirement is satisfied if the file contains the string
    "hook_dispatcher".  This heuristic allows flexibility in configuration
    structure while still detecting whether the user has migrated to the
    new dispatcher.
    """
    settings_path = os.path.join(os.getcwd(), ".claude", "settings.json")
    if not os.path.exists(settings_path):
        return "WARN", "Configuration file .claude/settings.json is missing."
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "hook_dispatcher" in content:
            return "PASS", "Hook dispatcher is configured in .claude/settings.json."
        else:
            return "WARN", "Hook dispatcher not detected in settings.json; please update to use runtime_sidecar/hook_dispatcher.py."
    except Exception as exc:
        logger.warning("Failed to read settings.json: %s", exc)
        return "FAIL", f"Cannot read .claude/settings.json: {exc}"
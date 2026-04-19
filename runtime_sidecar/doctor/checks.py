"""
Aggregate doctor checks for longClaw.

The doctor command runs a suite of checks covering file presence,
configuration, state database health and optional utilities.  Each check
returns a status (PASS/WARN/FAIL) and a message.  The doctor tool
aggregates these results into a report and exits with a non‑zero code if
any failures are present.
"""

import json
import os
from typing import Dict, List, Tuple

from ..logging.logger import get_logger
from .config_check import check_hooks_configuration
from .state_check import check_state_db

logger = get_logger(__name__)


def _check_file_exists(path: str, description: str) -> Tuple[str, str]:
    if os.path.exists(path):
        return "PASS", f"{description} present"
    else:
        return "FAIL", f"{description} missing at {path}"


def _check_json_file(path: str, description: str) -> Tuple[str, str]:
    if not os.path.exists(path):
        return "PASS", f"{description} not present (optional)"
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return "PASS", f"{description} valid JSON"
    except Exception as exc:
        return "FAIL", f"{description} invalid JSON: {exc}"


def run_all_checks() -> List[Dict[str, str]]:
    """Execute all doctor checks and return a list of result dicts."""
    results: List[Dict[str, str]] = []

    # Check mandatory protocol files
    for filename in ["AGENTS.md", "MULTI_AGENTS.md", "CTRL_PROTOCOLS.md", "DEV_LOG.md"]:
        path = os.path.join(os.getcwd(), filename)
        status, msg = _check_file_exists(path, filename)
        results.append({"check": filename, "status": status, "message": msg})

    # Check .claude/settings.json configuration
    status, msg = check_hooks_configuration()
    results.append({"check": "settings.json", "status": status, "message": msg})

    # Check state database
    status, msg = check_state_db()
    results.append({"check": "state.db", "status": status, "message": msg})

    # Check heartbeat JSON (optional)
    hb_path = os.path.join(os.getcwd(), "memory", "heartbeat-state.json")
    status, msg = _check_json_file(hb_path, "heartbeat-state.json")
    results.append({"check": "heartbeat-state.json", "status": status, "message": msg})

    # Check optional tools/memory_search.py
    ms_path = os.path.join(os.getcwd(), "tools", "memory_search.py")
    if os.path.exists(ms_path):
        status_msg = "PASS"
        message = "memory_search.py present"
    else:
        status_msg = "WARN"
        message = "memory_search.py not found (optional)"
    results.append({"check": "memory_search.py", "status": status_msg, "message": message})

    return results
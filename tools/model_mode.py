#!/usr/bin/env python3
"""
Session model_mode helper: writes memory/session-state.json.model_mode.

Valid modes: auto | primary
- auto: default hint for CTRL / observability
- primary: hint that the session should not rely on automatic downgrade paths

Workspace does not ship a local LLM fallback layer. Configure models in OpenClaw
(`~/.openclaw/openclaw.json`) or the client UI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SESSION_STATE_PATH = ROOT / "memory" / "session-state.json"
VALID_MODES = ("auto", "primary")


def load_state() -> dict[str, Any]:
    if not SESSION_STATE_PATH.is_file():
        return {}
    try:
        return json.loads(SESSION_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_legacy_mode(state: dict[str, Any]) -> dict[str, Any]:
    """Former `fallback` mode removed; coerce to primary."""
    m = state.get("model_mode", "auto")
    if m == "fallback":
        state = dict(state)
        state["model_mode"] = "primary"
        save_state(state)
    return state


def _build_get_payload(state: dict[str, Any]) -> dict[str, Any]:
    state = _normalize_legacy_mode(state)
    mode = state.get("model_mode", "auto")
    if mode not in VALID_MODES:
        mode = "auto"
    return {
        "ok": True,
        "model_mode": mode,
        "path": str(SESSION_STATE_PATH),
        "valid_modes": list(VALID_MODES),
    }


def main() -> int:
    argv = sys.argv[1:]

    if not argv or argv[0] in {"get", "show"}:
        print(json.dumps(_build_get_payload(load_state()), ensure_ascii=False))
        return 0

    cmd = argv[0]
    if cmd == "set":
        if len(argv) < 2:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "usage: model_mode.py set <auto|primary>",
                    },
                    ensure_ascii=False,
                )
            )
            return 2
        mode = argv[1].strip().lower()
    else:
        mode = cmd.strip().lower()

    if mode not in VALID_MODES:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"invalid_mode:{mode}",
                    "valid_modes": list(VALID_MODES),
                },
                ensure_ascii=False,
            )
        )
        return 2

    state = load_state()
    state["model_mode"] = mode
    save_state(state)

    print(
        json.dumps(
            {
                "ok": True,
                "model_mode": mode,
                "path": str(SESSION_STATE_PATH),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

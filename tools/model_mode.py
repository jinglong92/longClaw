#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SESSION_STATE_PATH = ROOT / "memory" / "session-state.json"
VALID_MODES = {"auto", "primary", "fallback"}


def load_state() -> dict[str, Any]:
    if not SESSION_STATE_PATH.is_file():
        return {}
    try:
        return json.loads(SESSION_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    SESSION_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in {"get", "show"}:
        state = load_state()
        print(json.dumps({
            "ok": True,
            "model_mode": state.get("model_mode", "auto"),
            "path": str(SESSION_STATE_PATH),
        }, ensure_ascii=False))
        return 0

    cmd = argv[0]
    if cmd == "set":
        if len(argv) < 2:
            print(json.dumps({"ok": False, "error": "usage: model_mode.py set <auto|primary|fallback>"}, ensure_ascii=False))
            return 2
        mode = argv[1].strip().lower()
    else:
        mode = cmd.strip().lower()

    if mode not in VALID_MODES:
        print(json.dumps({"ok": False, "error": f"invalid_mode:{mode}", "valid_modes": sorted(VALID_MODES)}, ensure_ascii=False))
        return 2

    state = load_state()
    state["model_mode"] = mode
    save_state(state)
    print(json.dumps({
        "ok": True,
        "model_mode": mode,
        "path": str(SESSION_STATE_PATH),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

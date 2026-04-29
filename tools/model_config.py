#!/usr/bin/env python3
"""
Manual model switching helper for longClaw.

OpenClaw handles automatic model failover natively via the `fallbacks` field
in openclaw.json.  This tool is for manual override only — switch to a
specific model for the current session, or restore the configured primary.

State is persisted in memory/model-config.json so that longclaw-status can
show the current model context.

Usage:
    python3 tools/model_config.py status
    python3 tools/model_config.py use primary
    python3 tools/model_config.py use fallback
    python3 tools/model_config.py use <model-id>
    python3 tools/model_config.py set-primary <model-id>
    python3 tools/model_config.py set-fallback <model-id>
    python3 tools/model_config.py reset
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "memory" / "model-config.json"

DEFAULTS: dict[str, Any] = {
    "primary_model": "openai-codex/gpt-5.4",
    "fallback_model": "deepseek/deepseek-v4-pro",
    "current_model": "openai-codex/gpt-5.4",
    "override_active": False,
    "override_reason": None,
    "updated_at": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for k, v in DEFAULTS.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return dict(DEFAULTS)


def save_config(cfg: dict[str, Any]) -> None:
    cfg["updated_at"] = _now()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _apply_model(model_id: str) -> tuple[bool, str]:
    """Call `openclaw models set <model_id>`."""
    try:
        result = subprocess.run(
            ["openclaw", "models", "set", model_id],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or f"switched to {model_id}"
        return False, result.stderr.strip() or f"exit {result.returncode}"
    except FileNotFoundError:
        return False, "openclaw CLI not found"
    except subprocess.TimeoutExpired:
        return False, "openclaw models set timed out"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status() -> dict[str, Any]:
    cfg = load_config()
    return {
        "ok": True,
        "current_model": cfg["current_model"],
        "primary_model": cfg["primary_model"],
        "fallback_model": cfg["fallback_model"],
        "override_active": cfg["override_active"],
        "override_reason": cfg["override_reason"],
        "updated_at": cfg["updated_at"],
        "note": (
            "Auto-failover is handled by OpenClaw natively (fallbacks field in openclaw.json). "
            "This tool is for manual override only."
        ),
    }


def cmd_use(target: str) -> dict[str, Any]:
    """Switch to 'primary', 'fallback', or an explicit model ID."""
    cfg = load_config()

    if target == "primary":
        model_id = cfg["primary_model"]
        override_active = False
        reason = None
    elif target == "fallback":
        model_id = cfg["fallback_model"]
        override_active = True
        reason = "manual override → fallback"
    else:
        model_id = target
        override_active = True
        reason = f"manual override → {target}"

    ok, msg = _apply_model(model_id)
    if not ok:
        return {"ok": False, "error": msg, "model_id": model_id}

    cfg["current_model"] = model_id
    cfg["override_active"] = override_active
    cfg["override_reason"] = reason
    save_config(cfg)
    return {
        "ok": True,
        "current_model": model_id,
        "override_active": override_active,
    }


def cmd_set_primary(model_id: str) -> dict[str, Any]:
    cfg = load_config()
    cfg["primary_model"] = model_id
    if not cfg["override_active"]:
        cfg["current_model"] = model_id
    save_config(cfg)
    return {"ok": True, "primary_model": model_id}


def cmd_set_fallback(model_id: str) -> dict[str, Any]:
    cfg = load_config()
    cfg["fallback_model"] = model_id
    save_config(cfg)
    return {"ok": True, "fallback_model": model_id}


def cmd_reset() -> dict[str, Any]:
    """Restore primary model and clear override."""
    cfg = load_config()
    primary_id = cfg["primary_model"]
    ok, msg = _apply_model(primary_id)
    cfg["current_model"] = primary_id
    cfg["override_active"] = False
    cfg["override_reason"] = None
    save_config(cfg)
    if not ok:
        return {"ok": False, "error": msg, "current_model": primary_id}
    return {"ok": True, "action": "reset", "current_model": primary_id}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    argv = sys.argv[1:]

    if not argv or argv[0] in {"status", "get", "show"}:
        print(json.dumps(cmd_status(), ensure_ascii=False, indent=2))
        return 0

    cmd = argv[0]

    if cmd == "use":
        if len(argv) < 2:
            print(json.dumps({"ok": False, "error": "usage: model_config.py use <primary|fallback|model-id>"}))
            return 2
        print(json.dumps(cmd_use(argv[1]), ensure_ascii=False, indent=2))
        return 0

    if cmd == "set-primary":
        if len(argv) < 2:
            print(json.dumps({"ok": False, "error": "usage: model_config.py set-primary <model-id>"}))
            return 2
        print(json.dumps(cmd_set_primary(argv[1]), ensure_ascii=False, indent=2))
        return 0

    if cmd == "set-fallback":
        if len(argv) < 2:
            print(json.dumps({"ok": False, "error": "usage: model_config.py set-fallback <model-id>"}))
            return 2
        print(json.dumps(cmd_set_fallback(argv[1]), ensure_ascii=False, indent=2))
        return 0

    if cmd == "reset":
        print(json.dumps(cmd_reset(), ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({"ok": False, "error": f"unknown command: {cmd}"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

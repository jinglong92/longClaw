#!/usr/bin/env python3
"""
Model configuration and fallback management for longClaw.

Manages primary / fallback model selection, automatic failure detection,
and manual override.  State is persisted in memory/model-config.json.

Usage:
    python3 tools/model_config.py status
    python3 tools/model_config.py use primary
    python3 tools/model_config.py use fallback
    python3 tools/model_config.py use <model-id>
    python3 tools/model_config.py set-primary <model-id>
    python3 tools/model_config.py set-fallback <model-id>
    python3 tools/model_config.py mark-failure [--reason <reason>]
    python3 tools/model_config.py mark-success
    python3 tools/model_config.py reset
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "memory" / "model-config.json"

DEFAULTS: dict[str, Any] = {
    "primary_model": "openai-codex/gpt-5.4",
    "fallback_model": "DS-V4-Pro",
    "fallback_enabled": True,
    "current_model": "openai-codex/gpt-5.4",
    "fallback_active": False,
    "fallback_reason": None,
    "consecutive_failures": 0,
    "failure_threshold": 2,
    "updated_at": None,
}

# Keywords in tool output that indicate an API / model failure
FAILURE_SIGNALS = [
    "rate_limit_exceeded",
    "rate limit",
    "ratelimit",
    "model_not_found",
    "insufficient_quota",
    "quota exceeded",
    "overloaded",
    "503 service unavailable",
    "502 bad gateway",
    "connection timeout",
    "read timeout",
    "upstream connect error",
    "the model `",          # OpenAI "the model `x` does not exist"
    "no such model",
    "invalid model",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        # Back-fill any missing keys from DEFAULTS
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
    """Call `openclaw models set <model_id>`.  Returns (success, message)."""
    try:
        result = subprocess.run(
            ["openclaw", "models", "set", model_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or f"switched to {model_id}"
        return False, (result.stderr.strip() or f"exit {result.returncode}")
    except FileNotFoundError:
        return False, "openclaw CLI not found"
    except subprocess.TimeoutExpired:
        return False, "openclaw models set timed out"


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------

def cmd_status() -> dict[str, Any]:
    cfg = load_config()
    return {
        "ok": True,
        "current_model": cfg["current_model"],
        "fallback_active": cfg["fallback_active"],
        "fallback_reason": cfg["fallback_reason"],
        "primary_model": cfg["primary_model"],
        "fallback_model": cfg["fallback_model"],
        "fallback_enabled": cfg["fallback_enabled"],
        "consecutive_failures": cfg["consecutive_failures"],
        "failure_threshold": cfg["failure_threshold"],
        "updated_at": cfg["updated_at"],
    }


def cmd_use(target: str) -> dict[str, Any]:
    """Switch to 'primary', 'fallback', or an explicit model ID."""
    cfg = load_config()

    if target == "primary":
        model_id = cfg["primary_model"]
        fallback_active = False
        reason = None
    elif target == "fallback":
        model_id = cfg["fallback_model"]
        fallback_active = True
        reason = "manual override"
    else:
        model_id = target
        fallback_active = (target == cfg["fallback_model"])
        reason = "manual override" if fallback_active else None

    ok, msg = _apply_model(model_id)
    if not ok:
        return {"ok": False, "error": msg, "model_id": model_id}

    cfg["current_model"] = model_id
    cfg["fallback_active"] = fallback_active
    cfg["fallback_reason"] = reason
    cfg["consecutive_failures"] = 0
    save_config(cfg)
    return {"ok": True, "current_model": model_id, "fallback_active": fallback_active}


def cmd_set_primary(model_id: str) -> dict[str, Any]:
    cfg = load_config()
    cfg["primary_model"] = model_id
    # If currently on primary, update current_model too
    if not cfg["fallback_active"]:
        cfg["current_model"] = model_id
    save_config(cfg)
    return {"ok": True, "primary_model": model_id}


def cmd_set_fallback(model_id: str) -> dict[str, Any]:
    cfg = load_config()
    cfg["fallback_model"] = model_id
    if cfg["fallback_active"]:
        cfg["current_model"] = model_id
    save_config(cfg)
    return {"ok": True, "fallback_model": model_id}


def cmd_mark_failure(reason: Optional[str] = None) -> dict[str, Any]:
    """Record one API failure.  Auto-switch to fallback if threshold reached."""
    cfg = load_config()

    if cfg["fallback_active"]:
        # Already on fallback — don't escalate further, just record
        return {
            "ok": True,
            "action": "already_on_fallback",
            "current_model": cfg["current_model"],
        }

    cfg["consecutive_failures"] = cfg.get("consecutive_failures", 0) + 1
    threshold = cfg.get("failure_threshold", 2)
    save_config(cfg)

    if cfg["fallback_enabled"] and cfg["consecutive_failures"] >= threshold:
        fallback_id = cfg["fallback_model"]
        ok, msg = _apply_model(fallback_id)
        if ok:
            cfg["current_model"] = fallback_id
            cfg["fallback_active"] = True
            cfg["fallback_reason"] = reason or f"primary failed {cfg['consecutive_failures']} times"
            save_config(cfg)
            return {
                "ok": True,
                "action": "switched_to_fallback",
                "current_model": fallback_id,
                "consecutive_failures": cfg["consecutive_failures"],
                "reason": cfg["fallback_reason"],
            }
        else:
            return {
                "ok": False,
                "action": "fallback_switch_failed",
                "error": msg,
                "consecutive_failures": cfg["consecutive_failures"],
            }

    return {
        "ok": True,
        "action": "failure_recorded",
        "consecutive_failures": cfg["consecutive_failures"],
        "threshold": threshold,
        "will_switch_at": threshold,
    }


def cmd_mark_success() -> dict[str, Any]:
    """Record a successful call.  Reset failure counter.
    If on fallback and failures cleared, optionally restore primary."""
    cfg = load_config()
    was_fallback = cfg["fallback_active"]
    cfg["consecutive_failures"] = 0

    # Auto-restore primary after success on fallback
    if was_fallback:
        primary_id = cfg["primary_model"]
        ok, msg = _apply_model(primary_id)
        if ok:
            cfg["current_model"] = primary_id
            cfg["fallback_active"] = False
            cfg["fallback_reason"] = None
            save_config(cfg)
            return {"ok": True, "action": "restored_primary", "current_model": primary_id}
        else:
            save_config(cfg)
            return {"ok": True, "action": "success_recorded_stay_on_fallback", "error": msg}

    save_config(cfg)
    return {"ok": True, "action": "success_recorded", "consecutive_failures": 0}


def cmd_reset() -> dict[str, Any]:
    """Reset to defaults, restore primary model."""
    cfg = load_config()
    primary_id = cfg["primary_model"]
    _apply_model(primary_id)
    new_cfg = dict(DEFAULTS)
    new_cfg["primary_model"] = cfg["primary_model"]
    new_cfg["fallback_model"] = cfg["fallback_model"]
    new_cfg["current_model"] = primary_id
    save_config(new_cfg)
    return {"ok": True, "action": "reset", "current_model": primary_id}


def detect_failure_in_output(output: str) -> Optional[str]:
    """Scan tool output for known API failure signals.  Return matched signal or None."""
    lower = output.lower()
    for sig in FAILURE_SIGNALS:
        if sig.lower() in lower:
            return sig
    return None


# ---------------------------------------------------------------------------
# CLI entry point
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

    if cmd == "mark-failure":
        reason = None
        if "--reason" in argv:
            idx = argv.index("--reason")
            if idx + 1 < len(argv):
                reason = argv[idx + 1]
        print(json.dumps(cmd_mark_failure(reason), ensure_ascii=False, indent=2))
        return 0

    if cmd == "mark-success":
        print(json.dumps(cmd_mark_success(), ensure_ascii=False, indent=2))
        return 0

    if cmd == "reset":
        print(json.dumps(cmd_reset(), ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({"ok": False, "error": f"unknown command: {cmd}"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

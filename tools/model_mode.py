#!/usr/bin/env python3
"""
Session model_mode helper + optional OpenClaw agent model sync.

- Writes memory/session-state.json.model_mode (may be overwritten by CTRL each turn).
- With --sync-openclaw: patches ~/.openclaw/openclaw.json so ALL subsequent chats use
  Ollama until you run set auto|primary --sync-openclaw — this is what makes
  "fallback" persist across new conversations and avoids Codex quota when bound to ollama/*.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SESSION_STATE_PATH = ROOT / "memory" / "session-state.json"
VALID_MODES = {"auto", "primary", "fallback"}

OPENCLAW_JSON = Path.home() / ".openclaw" / "openclaw.json"
RESTORE_PATH = Path.home() / ".openclaw" / "model_mode_agent_restore.json"

# Must match models.providers.ollama in openclaw.json
DEFAULT_FALLBACK_MODEL = os.environ.get("OPENCLAW_FALLBACK_MODEL", "ollama/gemma4:e2b")


def load_state() -> dict[str, Any]:
    if not SESSION_STATE_PATH.is_file():
        return {}
    try:
        return json.loads(SESSION_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    SESSION_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_openclaw() -> dict[str, Any]:
    if not OPENCLAW_JSON.is_file():
        raise FileNotFoundError(f"missing {OPENCLAW_JSON}")
    return json.loads(OPENCLAW_JSON.read_text(encoding="utf-8"))


def _read_openclaw_defaults_primary() -> str | None:
    try:
        cfg = _load_openclaw()
        agents = cfg.get("agents") or {}
        defaults = agents.get("defaults") or {}
        model_block = defaults.get("model") or {}
        p = model_block.get("primary")
        return str(p) if p else None
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return None


def _build_get_payload(state: dict[str, Any]) -> dict[str, Any]:
    mode = state.get("model_mode", "auto")
    oc_primary = _read_openclaw_defaults_primary()
    out: dict[str, Any] = {
        "ok": True,
        "model_mode": mode,
        "path": str(SESSION_STATE_PATH),
        "sync_openclaw_flag": "--sync-openclaw",
        "openclaw_defaults_primary": oc_primary,
    }
    ollama_bound = bool(oc_primary and oc_primary.startswith("ollama/"))
    out["persistent_fallback_active"] = mode == "fallback" and ollama_bound
    if mode == "fallback" and not ollama_bound:
        out["drift_warning"] = (
            "session-state says fallback but OpenClaw agents.defaults.model.primary is not ollama/*; "
            "new chats may still use Codex. Run: python3 tools/model_mode.py set fallback --sync-openclaw && openclaw gateway restart"
        )
    if mode in ("auto", "primary") and ollama_bound and RESTORE_PATH.is_file():
        out["note"] = (
            "OpenClaw is still on ollama (restore snapshot exists). "
            "Run set auto --sync-openclaw to restore Codex agents if desired."
        )
    return out


def _save_openclaw(data: dict[str, Any]) -> None:
    OPENCLAW_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _snapshot_agents(cfg: dict[str, Any]) -> dict[str, Any]:
    agents = cfg.get("agents") or {}
    defaults = agents.get("defaults") or {}
    model_block = defaults.get("model") or {}
    primary = model_block.get("primary")
    lst = agents.get("list") or []
    list_snap: list[dict[str, str]] = []
    for item in lst:
        if isinstance(item, dict) and "id" in item:
            list_snap.append({"id": str(item["id"]), "model": str(item.get("model", ""))})
    return {"defaults_primary": primary, "list": list_snap}


def _apply_snapshot(cfg: dict[str, Any], snap: dict[str, Any]) -> None:
    agents = cfg.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    model_block = defaults.setdefault("model", {})
    if snap.get("defaults_primary"):
        model_block["primary"] = snap["defaults_primary"]
    lst = agents.get("list") or []
    by_id = {x["id"]: x["model"] for x in (snap.get("list") or []) if "id" in x}
    for item in lst:
        if isinstance(item, dict) and item.get("id") in by_id:
            item["model"] = by_id[item["id"]]


def _apply_fallback_all(cfg: dict[str, Any], fallback_model: str) -> None:
    agents = cfg.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    model_block = defaults.setdefault("model", {})
    model_block["primary"] = fallback_model
    for item in agents.get("list") or []:
        if isinstance(item, dict):
            item["model"] = fallback_model


def sync_openclaw(mode: str, fallback_model: str) -> dict[str, Any]:
    """
    Align ~/.openclaw/openclaw.json agent models with model_mode.
    - fallback: point all listed agents + defaults.primary at Ollama (snapshot first).
    - auto|primary: restore snapshot if present.
    """
    cfg = _load_openclaw()

    if mode == "fallback":
        if not RESTORE_PATH.is_file():
            snap = _snapshot_agents(cfg)
            RESTORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            RESTORE_PATH.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _apply_fallback_all(cfg, fallback_model)
        _save_openclaw(cfg)
        return {
            "ok": True,
            "action": "apply_fallback",
            "fallback_model": fallback_model,
            "restore_saved_to": str(RESTORE_PATH),
            "hint": "Run: openclaw gateway restart (or restart the agent client) so the new model binds.",
        }

    # auto or primary: restore
    if not RESTORE_PATH.is_file():
        return {
            "ok": True,
            "action": "restore_skipped",
            "reason": "no_snapshot_file",
            "path": str(RESTORE_PATH),
        }
    snap = json.loads(RESTORE_PATH.read_text(encoding="utf-8"))
    _apply_snapshot(cfg, snap)
    _save_openclaw(cfg)
    try:
        RESTORE_PATH.unlink()
    except OSError:
        pass
    return {
        "ok": True,
        "action": "restored_agents",
        "hint": "Run: openclaw gateway restart so restored models take effect.",
    }


def main() -> int:
    argv = sys.argv[1:]
    sync_oc = "--sync-openclaw" in argv
    argv = [a for a in argv if a != "--sync-openclaw"]

    if not argv or argv[0] in {"get", "show"}:
        state = load_state()
        print(json.dumps(_build_get_payload(state), ensure_ascii=False))
        return 0

    cmd = argv[0]
    if cmd == "set":
        if len(argv) < 2:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "usage: model_mode.py set <auto|primary|fallback> [--sync-openclaw]",
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
                {"ok": False, "error": f"invalid_mode:{mode}", "valid_modes": sorted(VALID_MODES)},
                ensure_ascii=False,
            )
        )
        return 2

    state = load_state()
    state["model_mode"] = mode
    save_state(state)

    out: dict[str, Any] = {
        "ok": True,
        "model_mode": mode,
        "path": str(SESSION_STATE_PATH),
    }

    if sync_oc:
        try:
            out["openclaw"] = sync_openclaw(mode, DEFAULT_FALLBACK_MODEL)
        except FileNotFoundError as e:
            out["openclaw"] = {"ok": False, "error": str(e)}
        except (json.JSONDecodeError, OSError, KeyError, TypeError) as e:
            out["openclaw"] = {"ok": False, "error": str(e)}

    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Unified LLM entry with provider fallback (longClaw workspace).

Reads JSON from stdin: {"system": "...", "prompt": "..."}
Writes JSON to stdout. On fallback, also prints DEV LOG lines to stderr.

Config: runtime/model-fallback.json (relative to workspace root = parent of tools/).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "runtime" / "model-fallback.json"
SESSION_STATE_PATH = ROOT / "memory" / "session-state.json"


def load_cfg() -> dict[str, Any]:
    if not CFG_PATH.is_file():
        raise FileNotFoundError(f"missing config: {CFG_PATH}")
    with CFG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("stdin is empty, expected JSON request payload")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("stdin JSON must be an object")
    return data


def load_session_state() -> dict[str, Any]:
    if not SESSION_STATE_PATH.is_file():
        return {}
    try:
        with SESSION_STATE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def resolve_model_mode(payload: dict[str, Any]) -> str:
    raw = payload.get("model_mode")
    if raw is None:
        raw = load_session_state().get("model_mode", "auto")
    mode = str(raw or "auto").strip().lower()
    if mode not in {"auto", "primary", "fallback"}:
        return "auto"
    return mode


def _emit_devlog(primary_provider: str, primary_model: str, fb_provider: str, fb_model: str, reason: str) -> None:
    print(
        f"🧠 Model primary={primary_provider}:{primary_model} -> fallback={fb_provider}:{fb_model}",
        file=sys.stderr,
    )
    print(f"⚠️ Fallback reason: {reason}", file=sys.stderr)


def classify_from_exception(exc: BaseException) -> str:
    s = str(exc).lower()
    if "insufficient_quota" in s:
        return "insufficient_quota"
    if "billing_hard_limit" in s or ("billing" in s and "limit" in s):
        return "billing_hard_limit_reached"
    if "429" in s or "rate limit" in s or "too many requests" in s:
        return "rate_limit"
    if "timed out" in s or "timeout" in s:
        return "timeout"
    if "connection" in s or "connect" in s or "errno 61" in s or "refused" in s:
        return "connection_error"
    if "503" in s or "502" in s or "500" in s or "504" in s:
        return "server_error"
    if "unavailable" in s or "no route to host" in s:
        return "provider_unavailable"
    if "401" in s or "invalid api key" in s or "incorrect api key" in s:
        return "authentication_error"
    if "400" in s or "bad request" in s or "invalid_request" in s:
        return "bad_request"
    if "content_policy" in s or "content_filter" in s:
        return "content_policy"
    if "safety" in s or ("policy" in s and "refus" in s):
        return "safety_refusal"
    return "unknown"


def classify_http_error(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        body = ""
    text = f"{exc.code} {body}".lower()
    if exc.code == 429:
        return "rate_limit"
    if exc.code in (500, 502, 503, 504):
        return "server_error"
    if exc.code == 401:
        return "authentication_error"
    if exc.code == 400:
        if "insufficient_quota" in text:
            return "insufficient_quota"
        return "bad_request"
    try:
        j = json.loads(body) if body else {}
        err = j.get("error") if isinstance(j.get("error"), dict) else {}
        code = str(err.get("code") or err.get("type") or "").lower()
        msg = str(err.get("message") or "").lower()
        combined = f"{code} {msg}"
        if "insufficient_quota" in combined:
            return "insufficient_quota"
        if "billing" in combined and "hard" in combined:
            return "billing_hard_limit_reached"
        if "rate_limit" in combined or "429" in combined:
            return "rate_limit"
        if "content_policy" in combined or "content_filter" in combined:
            return "content_policy"
        if "safety" in combined or "refus" in combined:
            return "safety_refusal"
        if "invalid" in combined and "request" in combined:
            return "bad_request"
    except json.JSONDecodeError:
        pass
    return classify_from_exception(exc)


def should_fallback(err_type: str, cfg: dict[str, Any]) -> bool:
    if err_type in cfg.get("do_not_fallback_on", []):
        return False
    return err_type in cfg.get("fallback_on", [])


def _openai_style_messages(system: str, prompt: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system.strip():
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def call_primary(payload: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    primary = cfg["primary"]
    provider = str(primary.get("provider", "openai"))
    model = str(primary["model"])
    base = str(primary.get("base_url", "https://api.openai.com/v1")).rstrip("/")
    env_name = str(primary.get("api_key_env", "OPENAI_API_KEY"))
    api_key = os.environ.get(env_name, "").strip()
    if not api_key:
        raise RuntimeError(f"authentication_error: missing env {env_name} for primary provider")

    timeout = float(primary.get("timeout_seconds", 120))
    system = str(payload.get("system") or "")
    prompt = str(payload.get("prompt") or "")
    if not prompt.strip():
        raise ValueError("payload.prompt is required")

    body: dict[str, Any] = {
        "model": model,
        "messages": _openai_style_messages(system, prompt),
    }
    mcl = primary.get("max_completion_tokens")
    mt = primary.get("max_tokens")
    if mcl is not None:
        body["max_completion_tokens"] = int(mcl)
    elif mt is not None:
        body["max_tokens"] = int(mt)
    else:
        if any(model.startswith(p) for p in ("gpt-5", "o1", "o3", "o4")):
            body["max_completion_tokens"] = 4096
        else:
            body["max_tokens"] = 4096

    if primary.get("temperature") is not None:
        body["temperature"] = float(primary["temperature"])

    url = f"{base}/chat/completions"
    req = Request(
        url=url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        err_type = classify_http_error(e)
        raise RuntimeError(f"{err_type}: HTTP {e.code}") from e
    except TimeoutError as e:
        raise RuntimeError("timeout: primary request timed out") from e
    except OSError as e:
        msg = str(e).lower()
        if "timed out" in msg or "timeout" in msg:
            raise RuntimeError("timeout: primary connection timed out") from e
        raise RuntimeError(f"connection_error: {e}") from e

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"prompt_error: unexpected primary response shape: {data!r}") from e

    return {
        "ok": True,
        "text": text or "",
        "provider_used": provider,
        "model_used": model,
    }


def call_ollama(payload: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    fb = cfg["fallback"]
    base_url = str(fb["base_url"]).rstrip("/")
    model = str(fb["model"])
    timeout = float(fb.get("timeout_seconds", 120))
    system = str(payload.get("system") or "")
    prompt = str(payload.get("prompt") or "")

    body = {
        "model": model,
        "messages": _openai_style_messages(system, prompt),
        "stream": False,
    }
    req = Request(
        url=f"{base_url}/api/chat",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        raise RuntimeError(f"OLLAMA_HTTP_{e.code}: {raw}") from e
    except URLError as e:
        raise RuntimeError(f"OLLAMA_CALL_FAILED: {e}") from e

    msg = data.get("message") if isinstance(data.get("message"), dict) else {}
    text = str(msg.get("content") or data.get("response") or "")

    return {
        "ok": True,
        "text": text,
        "provider_used": "ollama",
        "model_used": model,
        "fallback_triggered": True,
    }


def main() -> None:
    cfg = load_cfg()
    payload = read_stdin_json()
    primary = cfg["primary"]
    fallback = cfg["fallback"]
    p_prov = str(primary.get("provider", "openai"))
    p_model = str(primary["model"])
    f_prov = str(fallback.get("provider", "ollama"))
    f_model = str(fallback["model"])
    model_mode = resolve_model_mode(payload)

    # 用户主动指定走兜底模型（payload 里传 force_fallback=true）或会话模式已切到 fallback
    if payload.get("force_fallback") or model_mode == "fallback":
        reason = "force_fallback" if payload.get("force_fallback") else "session_model_mode:fallback"
        print(
            f"🧠 Model [force] skipping primary={p_prov}:{p_model}, using fallback={f_prov}:{f_model}",
            file=sys.stderr,
        )
        result = call_ollama(payload, cfg)
        result["fallback_triggered"] = True
        result["fallback_reason"] = reason
        result["degraded_mode"] = True
        result["model_mode"] = model_mode
        if payload.get("force_fallback"):
            result["fallback_notice"] = f"[兜底模型] 用户指定走兜底模型：{f_prov}:{f_model}"
        else:
            result["fallback_notice"] = f"[兜底模型] 会话当前为 fallback 模式：{f_prov}:{f_model}"
        print(json.dumps(result, ensure_ascii=False))
        return

    if not cfg.get("enabled", False):
        result = call_primary(payload, cfg)
        result.setdefault("fallback_triggered", False)
        result["degraded_mode"] = False
        result["model_mode"] = model_mode
        print(json.dumps(result, ensure_ascii=False))
        return

    try:
        result = call_primary(payload, cfg)
        result["fallback_triggered"] = False
        result["degraded_mode"] = False
        result["model_mode"] = model_mode
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        err_type = classify_from_exception(e)
        if isinstance(e, RuntimeError) and ":" in str(e):
            prefix = str(e).split(":", 1)[0].strip()
            if prefix in (
                "insufficient_quota",
                "billing_hard_limit_reached",
                "rate_limit",
                "timeout",
                "connection_error",
                "provider_unavailable",
                "server_error",
                "bad_request",
                "prompt_error",
                "tool_schema_error",
                "content_policy",
                "safety_refusal",
                "authentication_error",
                "unknown",
            ):
                err_type = prefix
        if model_mode == "primary":
            out = {
                "ok": False,
                "error": str(e),
                "error_type": err_type,
                "degraded_mode": False,
                "fallback_triggered": False,
                "model_mode": model_mode,
                "fallback_blocked_by": "session_model_mode:primary",
            }
            print(json.dumps(out, ensure_ascii=False))
            sys.exit(1)
        if should_fallback(err_type, cfg):
            _emit_devlog(p_prov, p_model, f_prov, f_model, err_type)
            result = call_ollama(payload, cfg)
            result["fallback_reason"] = err_type
            result["degraded_mode"] = True
            result["model_mode"] = model_mode
            result["fallback_notice"] = f"[兜底模型] 本轮命中 fallback：primary={p_prov}:{p_model} 不可用（{err_type}），已切换至 {f_prov}:{f_model}"
            print(json.dumps(result, ensure_ascii=False))
            return
        out = {"ok": False, "error": str(e), "error_type": err_type, "degraded_mode": False, "model_mode": model_mode}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

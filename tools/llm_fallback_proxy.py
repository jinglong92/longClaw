#!/usr/bin/env python3
"""
OpenAI-compatible HTTP proxy: primary (OpenAI) -> optional Ollama fallback.

- OpenClaw keeps calling the same logical model (e.g. gpt-5.4); this proxy forwards
  that model to the primary upstream.
- On quota / rate-limit / selected HTTP statuses / substring matches, retries once
  against the fallback upstream with body.model rewritten to fallback.model only.

Config: runtime/model-router.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from copy import deepcopy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROUTER_CFG = ROOT / "runtime" / "model-router.json"


def load_router_cfg(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _chat_url(base: str) -> str:
    b = base.rstrip("/")
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    return f"{b}/v1/chat/completions"


def _should_fallback_http(status: int, body_text: str, cfg: dict[str, Any]) -> bool:
    if HTTPStatus.OK <= status < 300:
        return False
    statuses = set(cfg.get("fallback_http_statuses") or [])
    if status in statuses:
        return True
    low = body_text.lower()
    for sub in cfg.get("fallback_error_substrings") or []:
        if sub.lower() in low:
            return True
    return False


def _should_fallback_exc(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    s = str(exc).lower()
    for needle in (
        "timed out",
        "timeout",
        "connection refused",
        "connection reset",
        "errno 61",
        "errno 54",
        "service unavailable",
        "temporarily unavailable",
    ):
        if needle in s:
            return True
    return isinstance(exc, URLError)


def _emit_fallback_devlog(
    primary_model: str,
    fallback_model: str,
    reason: str,
) -> None:
    print(
        f"🧠 Model primary=openai:{primary_model} -> fallback=ollama:{fallback_model}",
        file=sys.stderr,
    )
    print(f"⚠️ Fallback reason: {reason}", file=sys.stderr)


def _forward_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, bytes, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "application/json")
            return resp.getcode() or 200, raw, ctype
    except HTTPError as e:
        try:
            raw = e.read()
        except Exception:  # noqa: BLE001
            raw = b""
        ctype = e.headers.get("Content-Type", "application/json") if e.headers else "application/json"
        return int(e.code), raw, ctype


def _build_upstream_headers(in_headers: dict[str, str], api_key_env: str) -> dict[str, str]:
    out = {"Content-Type": "application/json"}
    auth = in_headers.get("authorization") or in_headers.get("Authorization")
    if auth:
        out["Authorization"] = auth
    else:
        key = os.environ.get(api_key_env, "").strip()
        if key:
            out["Authorization"] = f"Bearer {key}"
    for k in ("OpenAI-Organization", "openai-organization"):
        if k in in_headers:
            out["OpenAI-Organization"] = in_headers[k]
            break
    return out


def _lower_header_dict(raw_headers: Any) -> dict[str, str]:
    d: dict[str, str] = {}
    for k, v in raw_headers.items():
        d[k.lower()] = v
    return d


class ProxyHandlerFactory:
    def __init__(self, cfg: dict[str, Any], config_path: Path) -> None:
        self.cfg = cfg
        self.config_path = config_path
        self.timeout = float(cfg.get("upstream_timeout_seconds") or 600)
        self.primary_base = str(cfg["primary"]["base_url"])
        self.primary_url = _chat_url(self.primary_base)
        self.api_key_env = str(cfg["primary"].get("api_key_env", "OPENAI_API_KEY"))
        self.default_primary_model = str(cfg["primary"].get("model", "gpt-5.4"))
        self.fallback_base = str(cfg["fallback"]["base_url"])
        self.fallback_url = _chat_url(self.fallback_base)
        self.fallback_model = str(cfg["fallback"]["model"])


class FallbackProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    shared_factory: ClassVar[ProxyHandlerFactory]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._factory = FallbackProxyHandler.shared_factory
        super().__init__(*args, **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/health", "/v1/health"):
            body = json.dumps(
                {"ok": True, "proxy": "llm_fallback_proxy", "cfg": self._factory.config_path.name}
            ).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/v1/chat/completions", "/chat/completions"):
            self.send_error(HTTPStatus.NOT_FOUND, "only /v1/chat/completions")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid json")
            return
        if not isinstance(payload, dict):
            self.send_error(HTTPStatus.BAD_REQUEST, "json must be object")
            return

        f = self._factory
        cfg = f.cfg
        in_h = _lower_header_dict(self.headers)
        up_headers = _build_upstream_headers(in_h, f.api_key_env)

        primary_model = str(payload.get("model") or f.default_primary_model)
        primary_payload = deepcopy(payload)
        primary_payload["model"] = primary_model

        reason = ""
        try:
            status, body, ctype = _forward_json(f.primary_url, primary_payload, up_headers, f.timeout)
        except (URLError, TimeoutError, OSError) as e:
            if _should_fallback_exc(e):
                reason = f"connection_or_timeout:{e}"
                self._try_fallback(payload, primary_model, reason, up_headers)
                return
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": {"message": str(e), "type": "proxy_upstream"}})
            return

        body_text = body.decode("utf-8", errors="replace")
        if not _should_fallback_http(status, body_text, cfg):
            self._send_raw(status, body, ctype)
            return

        reason = f"http_{status}"
        self._try_fallback(payload, primary_model, reason, up_headers, primary_error_body=body_text)

    def _try_fallback(
        self,
        original_payload: dict[str, Any],
        primary_model: str,
        reason: str,
        _up_headers: dict[str, str],
        primary_error_body: str | None = None,
    ) -> None:
        f = self._factory
        fb_payload = deepcopy(original_payload)
        fb_payload["model"] = f.fallback_model
        # Ollama OpenAI shim: no cloud key required; drop Authorization to avoid leaking.
        fb_headers = {"Content-Type": "application/json"}
        _emit_fallback_devlog(primary_model, f.fallback_model, reason)
        if primary_error_body:
            sys.stderr.write(f"[llm_fallback_proxy] primary error excerpt: {primary_error_body[:500]!r}\n")

        try:
            status, body, ctype = _forward_json(f.fallback_url, fb_payload, fb_headers, f.timeout)
        except (URLError, TimeoutError, OSError) as e:
            msg = {"error": {"message": f"fallback_failed: {e}", "type": "proxy_fallback"}}
            if primary_error_body:
                msg["primary_error_excerpt"] = primary_error_body[:2000]
            self._send_json(HTTPStatus.BAD_GATEWAY, msg)
            return

        self._send_raw(status, body, ctype)

    def _send_raw(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype.split(";")[0].strip())
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, obj: dict[str, Any]) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAI-compatible LLM fallback proxy")
    parser.add_argument("--config", type=Path, default=DEFAULT_ROUTER_CFG, help="Path to model-router.json")
    args = parser.parse_args()
    cfg_path = args.config.resolve()
    cfg = load_router_cfg(cfg_path)
    host = str(cfg.get("listen_host", "127.0.0.1"))
    port = int(cfg.get("listen_port", 18080))
    factory = ProxyHandlerFactory(cfg, cfg_path)
    FallbackProxyHandler.shared_factory = factory
    httpd = ThreadingHTTPServer((host, port), FallbackProxyHandler)
    httpd.daemon_threads = True
    sys.stderr.write(f"[llm_fallback_proxy] listening http://{host}:{port}/v1/chat/completions\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("[llm_fallback_proxy] shutdown\n")
        httpd.shutdown()


if __name__ == "__main__":
    main()

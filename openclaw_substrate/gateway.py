from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .config import SubstrateConfig
from .jsonlog import emit_log
from .schemas import TraceRecord
from .trace_plane import TracePlane


class OpenAIGatewayHandler(BaseHTTPRequestHandler):
    config: SubstrateConfig
    trace_plane: TracePlane

    server_version = "OpenClawGateway/0.1"

    def _json_response(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json_response(HTTPStatus.OK, {"status": "ok", "backend": self.config.gateway.default_backend})
            return
        self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))

        metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
        session_id = str(metadata.get("session_id", "local-session"))
        turn_id = str(metadata.get("turn_id", uuid4().hex[:12]))
        policy_version = str(metadata.get("policy_version", self.config.policy.policy_version))

        payload["metadata"] = {
            **metadata,
            "session_id": session_id,
            "turn_id": turn_id,
            "policy_version": policy_version,
        }

        emit_log(
            "gateway.request.received",
            {
                "session_id": session_id,
                "turn_id": turn_id,
                "policy_version": policy_version,
                "model": payload.get("model"),
            },
        )

        response_json: dict[str, Any]
        backend_error: str | None = None

        try:
            req = Request(
                self.config.gateway.mlx_chat_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=self.config.gateway.timeout_seconds) as resp:
                response_json = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network path
            backend_error = str(exc)
            if not self.config.gateway.mock_on_backend_error:
                self._json_response(HTTPStatus.BAD_GATEWAY, {"error": "backend unavailable", "detail": backend_error})
                return
            response_json = self._mock_response(payload)

        assistant_text = extract_assistant_text(response_json)
        user_text = extract_last_user_message(payload)

        trace = TraceRecord(
            trace_id=f"tr_{uuid4().hex[:16]}",
            session_id=session_id,
            turn_id=turn_id,
            policy_version=policy_version,
            request_text=user_text,
            response_text=assistant_text,
            route=self.config.gateway.default_backend,
            model=str(response_json.get("model", payload.get("model", "mlx-lm"))),
            metadata={
                "gateway_backend": self.config.gateway.default_backend,
                "backend_error": backend_error,
                "quality_score": 0.7,
            },
        )
        self.trace_plane.persist_raw_trace(trace)

        self._json_response(HTTPStatus.OK, response_json)

    def _mock_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = "[mock] backend unavailable, generated local fallback response."
        return {
            "id": f"chatcmpl-{uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": 0,
            "model": payload.get("model", "mlx-mock"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


def extract_last_user_message(payload: dict[str, Any]) -> str:
    msgs = payload.get("messages", [])
    for m in reversed(msgs):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return ""


def extract_assistant_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices", [])
    if not choices:
        return ""
    msg = choices[0].get("message", {})
    return str(msg.get("content", ""))


def run_gateway(config: SubstrateConfig) -> None:
    if not config.flags.gateway_enabled:
        raise RuntimeError("gateway_enabled=false")

    trace_plane = TracePlane(config)

    class _Handler(OpenAIGatewayHandler):
        pass

    _Handler.config = config
    _Handler.trace_plane = trace_plane

    server = ThreadingHTTPServer((config.gateway.host, config.gateway.port), _Handler)
    emit_log(
        "gateway.started",
        {
            "bind": f"{config.gateway.host}:{config.gateway.port}",
            "default_backend": config.gateway.default_backend,
            "target": config.gateway.mlx_chat_url,
        },
    )
    server.serve_forever()

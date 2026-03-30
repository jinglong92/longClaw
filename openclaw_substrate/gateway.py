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
        if self.path == "/v1/chat/completions":
            payload = self._read_json_payload()
            if payload is None:
                return
            self._handle_chat_payload(payload, source_channel="openai")
            return

        if self.path == self.config.wechat.path:
            if not self.config.wechat.enabled:
                self._json_response(HTTPStatus.NOT_FOUND, {"error": "wechat endpoint disabled"})
                return
            if not self._check_wechat_auth():
                self._json_response(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            wx_payload = self._read_json_payload()
            if wx_payload is None:
                return
            chat_payload = self._build_chat_payload_from_wechat(wx_payload)
            self._handle_chat_payload(chat_payload, source_channel="wechat")
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _read_json_payload(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload must be object")
            return payload
        except Exception as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid json payload", "detail": str(exc)})
            return None

    def _check_wechat_auth(self) -> bool:
        token = self.config.wechat.auth_token.strip()
        if not token:
            return True
        got = self.headers.get(self.config.wechat.auth_header, "")
        return got == token

    def _handle_chat_payload(self, payload: dict[str, Any], source_channel: str) -> None:
        metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
        session_id = str(metadata.get("session_id", "local-session"))
        turn_id = str(metadata.get("turn_id", uuid4().hex[:12]))
        policy_version = str(metadata.get("policy_version", self.config.policy.policy_version))
        payload["metadata"] = {
            **metadata,
            "session_id": session_id,
            "turn_id": turn_id,
            "policy_version": policy_version,
            "source_channel": source_channel,
        }
        if not payload.get("model"):
            payload["model"] = self.config.wechat.default_model

        emit_log(
            "gateway.request.received",
            {
                "session_id": session_id,
                "turn_id": turn_id,
                "policy_version": policy_version,
                "model": payload.get("model"),
                "source_channel": source_channel,
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

        response_json = normalize_chat_completion_response(
            response_json,
            fallback_model=str(payload.get("model", "mlx-lm")),
        )
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
                "source_channel": source_channel,
                "quality_score": 0.7,
            },
        )
        self.trace_plane.persist_raw_trace(trace)

        if source_channel == "wechat":
            self._json_response(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "reply": assistant_text,
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "policy_version": policy_version,
                    "openai_response": response_json,
                },
            )
            return
        self._json_response(HTTPStatus.OK, response_json)

    def _build_chat_payload_from_wechat(self, wx_payload: dict[str, Any]) -> dict[str, Any]:
        metadata = wx_payload.get("metadata", {}) if isinstance(wx_payload.get("metadata"), dict) else {}
        user_id = str(
            wx_payload.get("user_id")
            or wx_payload.get("from_user")
            or wx_payload.get("from")
            or metadata.get("user_id")
            or "unknown-user"
        )
        conv_id = str(
            wx_payload.get("conversation_id")
            or wx_payload.get("chat_id")
            or wx_payload.get("room_id")
            or metadata.get("conversation_id")
            or user_id
        )
        message_id = str(
            wx_payload.get("message_id")
            or wx_payload.get("msg_id")
            or metadata.get("message_id")
            or uuid4().hex[:12]
        )
        text = str(
            wx_payload.get("text")
            or wx_payload.get("content")
            or wx_payload.get("message")
            or ""
        ).strip()
        system_prompt = str(
            wx_payload.get("system_prompt")
            or metadata.get("system_prompt")
            or self.config.wechat.system_prompt
        )
        return {
            "model": wx_payload.get("model", self.config.wechat.default_model),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "metadata": {
                **metadata,
                "session_id": f"{self.config.wechat.session_prefix}:{conv_id}",
                "turn_id": message_id,
                "sender_id": user_id,
                "conversation_id": conv_id,
            },
        }

    def _mock_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = "[mock] backend unavailable, generated local fallback response."
        return {
            "id": f"chatcmpl-{uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": 0,
            "model": payload.get("model", "mlx-mock"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "text": content,
                    "finish_reason": "stop",
                }
            ],
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
    if isinstance(choices[0].get("text"), str) and choices[0]["text"].strip():
        return str(choices[0]["text"])
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
            elif isinstance(item, str) and item.strip():
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def normalize_chat_completion_response(response_json: dict[str, Any], fallback_model: str) -> dict[str, Any]:
    if not isinstance(response_json, dict):
        response_json = {}

    response_json.setdefault("id", f"chatcmpl-{uuid4().hex[:12]}")
    response_json.setdefault("object", "chat.completion")
    response_json.setdefault("created", 0)
    response_json.setdefault("model", fallback_model)
    if not isinstance(response_json.get("usage"), dict):
        response_json["usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        response_json["choices"] = [_build_text_choice("[fallback] empty backend response.")]
        return response_json

    first = choices[0]
    if not isinstance(first, dict):
        response_json["choices"] = [_build_text_choice("[fallback] empty backend response.")]
        return response_json

    msg = first.get("message")
    if not isinstance(msg, dict):
        first["message"] = {"role": "assistant", "content": "[fallback] invalid backend response."}
        first["text"] = "[fallback] invalid backend response."
        first.setdefault("finish_reason", "stop")
        return response_json

    content = msg.get("content")
    if isinstance(content, str):
        msg["content"] = content
        first["text"] = content
    elif isinstance(content, list):
        normalized: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    normalized.append(text)
            elif isinstance(item, str):
                normalized.append(item)
        if not normalized:
            normalized = ["[fallback] empty backend response."]
        joined = "\n".join(normalized)
        msg["content"] = joined
        first["text"] = joined
    else:
        msg["content"] = "[fallback] empty backend response."
        first["text"] = "[fallback] empty backend response."

    first.setdefault("finish_reason", "stop")
    return response_json


def _build_text_choice(text: str) -> dict[str, Any]:
    return {
        "index": 0,
        "message": {"role": "assistant", "content": text},
        "text": text,
        "finish_reason": "stop",
    }


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

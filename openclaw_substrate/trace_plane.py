from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import SubstrateConfig
from .jsonlog import append_jsonl, emit_log, read_jsonl
from .schemas import TraceRecord


class TracePlane:
    """Canonical trace persistence + state assembly utilities."""

    def __init__(self, config: SubstrateConfig):
        self.config = config
        self.raw_path = config.resolve_path(config.paths.traces_raw_jsonl)

    def persist_raw_trace(self, trace: TraceRecord) -> None:
        if not self.config.flags.trace_plane_enabled:
            raise RuntimeError("trace_plane_enabled=false")
        append_jsonl(self.raw_path, trace.to_dict())
        emit_log(
            "trace.persisted",
            {
                "trace_id": trace.trace_id,
                "session_id": trace.session_id,
                "turn_id": trace.turn_id,
                "route": trace.route,
                "policy_version": trace.policy_version,
            },
        )

    def load_traces(self) -> list[TraceRecord]:
        records = read_jsonl(self.raw_path)
        out: list[TraceRecord] = []
        for item in records:
            out.append(TraceRecord(**item))
        return out

    def split_mainline_sideline(self, traces: list[TraceRecord] | None = None) -> tuple[list[TraceRecord], list[TraceRecord]]:
        traces = traces if traces is not None else self.load_traces()
        mainline = [t for t in traces if t.is_mainline]
        sideline = [t for t in traces if not t.is_mainline]
        emit_log(
            "trace.split",
            {
                "mainline_count": len(mainline),
                "sideline_count": len(sideline),
            },
        )
        return mainline, sideline

    def assemble_next_state(self, session_id: str, history_turns: int | None = None) -> dict[str, Any]:
        traces = [t for t in self.load_traces() if t.session_id == session_id and t.is_mainline]
        traces.sort(key=lambda x: x.created_at)

        limit = history_turns or self.config.policy.max_state_history_turns
        window = traces[-limit:]

        next_state = {
            "session_id": session_id,
            "policy_version": self.config.policy.policy_version,
            "history": [
                {
                    "turn_id": t.turn_id,
                    "request_text": t.request_text,
                    "response_text": t.response_text,
                    "route": t.route,
                    "metadata": t.metadata,
                }
                for t in window
            ],
            "stats": {
                "turn_count": len(window),
                "avg_retries": (sum(t.retries for t in window) / len(window)) if window else 0.0,
                "explicit_correction_rate": (sum(1 for t in window if t.explicit_correction) / len(window)) if window else 0.0,
                "tool_success_rate": (
                    sum(1 for t in window if t.tool_success is True) / len(window)
                    if window
                    else 0.0
                ),
            },
        }
        emit_log("trace.next_state.assembled", {"session_id": session_id, "turns": len(window)})
        return next_state

    def training_eligible_filter(self, traces: list[TraceRecord]) -> list[TraceRecord]:
        min_q = self.config.policy.eligibility_min_quality
        eligible: list[TraceRecord] = []
        for t in traces:
            quality = float(t.metadata.get("quality_score", 0.0))
            if t.is_mainline and quality >= min_q:
                eligible.append(t)
        emit_log(
            "trace.training_eligibility.filtered",
            {
                "input_count": len(traces),
                "eligible_count": len(eligible),
                "min_quality": min_q,
            },
        )
        return eligible


def save_next_state(next_state: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(__import__("json").dumps(next_state, ensure_ascii=False, indent=2), encoding="utf-8")
    emit_log("trace.next_state.saved", {"path": str(out_path)})


def trace_to_dict(trace: TraceRecord) -> dict[str, Any]:
    return asdict(trace)

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


StatusType = Literal["draft", "shadow", "canary", "active", "archived"]
BackendType = Literal["mlx-lm", "llamafactory"]


@dataclass
class TraceRecord:
    trace_id: str
    session_id: str
    turn_id: str
    policy_version: str
    request_text: str
    response_text: str
    route: str
    model: str
    stage: str = "responded"
    retries: int = 0
    explicit_correction: bool = False
    tool_success: bool | None = None
    wrong_route: bool = False
    sideline_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    @property
    def is_mainline(self) -> bool:
        return not bool(self.sideline_reason)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JudgeResult:
    label: Literal[0, 1]
    reward: float
    reasons: list[str]
    confidence: float
    judged_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RewardRecord:
    trace_id: str
    session_id: str
    turn_id: str
    policy_version: str
    label: Literal[0, 1]
    reward: float
    source: str
    reasons: list[str]
    confidence: float
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JudgedTraceRecord:
    trace: TraceRecord
    judge: JudgeResult
    opd_hint: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace": self.trace.to_dict(),
            "judge": self.judge.to_dict(),
            "opd_hint": self.opd_hint,
        }


@dataclass
class AdapterRecord:
    adapter_id: str
    backend: BackendType
    base_model: str
    task_type: str
    status: StatusType
    metrics: dict[str, float] = field(default_factory=dict)
    path: str = ""
    notes: str = ""
    created_at: str = field(default_factory=utc_now_iso)

    @staticmethod
    def new(backend: BackendType, base_model: str, task_type: str, path: str) -> "AdapterRecord":
        adapter_id = f"adp_{uuid4().hex[:12]}"
        return AdapterRecord(
            adapter_id=adapter_id,
            backend=backend,
            base_model=base_model,
            task_type=task_type,
            status="draft",
            path=path,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

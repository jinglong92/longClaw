from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .jsonlog import emit_log
from .schemas import JudgedTraceRecord


@dataclass
class EvalMetrics:
    wrong_route_rate: float
    retry_rate: float
    explicit_correction_rate: float
    tool_success_proxy: float
    trainable_sample_yield: float

    def to_dict(self) -> dict[str, float]:
        return {
            "wrong_route_rate": self.wrong_route_rate,
            "retry_rate": self.retry_rate,
            "explicit_correction_rate": self.explicit_correction_rate,
            "tool_success_proxy": self.tool_success_proxy,
            "trainable_sample_yield": self.trainable_sample_yield,
        }


def _safe_rate(num: int, den: int) -> float:
    return (num / den) if den > 0 else 0.0


def compute_metrics(records: list[JudgedTraceRecord]) -> EvalMetrics:
    n = len(records)
    wrong_route = sum(1 for r in records if r.trace.wrong_route)
    retries = sum(1 for r in records if r.trace.retries > 0)
    explicit_correction = sum(1 for r in records if r.trace.explicit_correction)
    tool_success = sum(1 for r in records if r.trace.tool_success is True)
    trainable = sum(1 for r in records if r.judge.label == 1)

    return EvalMetrics(
        wrong_route_rate=_safe_rate(wrong_route, n),
        retry_rate=_safe_rate(retries, n),
        explicit_correction_rate=_safe_rate(explicit_correction, n),
        tool_success_proxy=_safe_rate(tool_success, n),
        trainable_sample_yield=_safe_rate(trainable, n),
    )


def compare_baseline_vs_candidate(
    baseline: list[JudgedTraceRecord],
    candidate: list[JudgedTraceRecord],
    out_path: Path,
) -> dict[str, dict[str, float]]:
    base = compute_metrics(baseline)
    cand = compute_metrics(candidate)

    delta = {
        "wrong_route_rate": cand.wrong_route_rate - base.wrong_route_rate,
        "retry_rate": cand.retry_rate - base.retry_rate,
        "explicit_correction_rate": cand.explicit_correction_rate - base.explicit_correction_rate,
        "tool_success_proxy": cand.tool_success_proxy - base.tool_success_proxy,
        "trainable_sample_yield": cand.trainable_sample_yield - base.trainable_sample_yield,
    }

    report = {
        "baseline": base.to_dict(),
        "candidate": cand.to_dict(),
        "delta": delta,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    emit_log(
        "shadow_eval.completed",
        {
            "baseline_count": len(baseline),
            "candidate_count": len(candidate),
            "report": str(out_path),
        },
    )
    return report

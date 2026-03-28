from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import SubstrateConfig
from .jsonlog import append_jsonl, emit_log, read_jsonl
from .schemas import JudgeResult, JudgedTraceRecord, RewardRecord, TraceRecord


class Judge(ABC):
    @abstractmethod
    def judge(self, trace: TraceRecord) -> JudgeResult:
        raise NotImplementedError


class RuleBasedBinaryJudge(Judge):
    """Local-first deterministic judge for binary reward assignment."""

    def judge(self, trace: TraceRecord) -> JudgeResult:
        score = 0.0
        reasons: list[str] = []

        if trace.tool_success is True:
            score += 0.5
            reasons.append("tool_success")
        if trace.retries > 1:
            score -= 0.4
            reasons.append("retry_gt_1")
        if trace.explicit_correction:
            score -= 0.4
            reasons.append("explicit_correction")
        if trace.wrong_route:
            score -= 0.6
            reasons.append("wrong_route")

        quality = float(trace.metadata.get("quality_score", 0.5))
        score += 0.5 * (quality - 0.5)

        label = 1 if score >= 0 else 0
        reward = 1.0 if label == 1 else -1.0
        confidence = min(0.99, max(0.5, 0.5 + abs(score)))

        if not reasons:
            reasons.append("neutral_default")

        return JudgeResult(label=label, reward=reward, reasons=reasons, confidence=confidence)


class LlmJudge(Judge):
    """Pluggable interface placeholder for future local/remote LLM judges."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    def judge(self, trace: TraceRecord) -> JudgeResult:
        # Stub: fallback to neutral binary signal until LLM judge prompt/runtime is wired.
        return JudgeResult(label=1, reward=0.2, reasons=[f"llm_stub:{self.model_name}"], confidence=0.55)


class OpdHintExtractor(ABC):
    @abstractmethod
    def extract(self, trace: TraceRecord, judge_result: JudgeResult) -> dict[str, str]:
        raise NotImplementedError


class HeuristicOpdHintExtractor(OpdHintExtractor):
    """OPD = Observation / Problem / Diagnosis"""

    def extract(self, trace: TraceRecord, judge_result: JudgeResult) -> dict[str, str]:
        observation = f"route={trace.route}, retries={trace.retries}, correction={trace.explicit_correction}"
        problems: list[str] = []

        if trace.wrong_route:
            problems.append("routing_mismatch")
        if trace.explicit_correction:
            problems.append("answer_correction_needed")
        if trace.retries > 1:
            problems.append("high_retry")
        if trace.tool_success is False:
            problems.append("tool_failure")

        problem = ";".join(problems) if problems else "none"

        if problem == "none":
            diagnosis = "keep_policy"
        else:
            diagnosis = "adjust_router_or_prompt"

        if judge_result.label == 0 and trace.wrong_route:
            diagnosis = "prioritize_router_training"

        return {
            "observation": observation,
            "problem": problem,
            "diagnosis": diagnosis,
        }


class JudgePlane:
    def __init__(self, config: SubstrateConfig, judge: Judge | None = None, opd_extractor: OpdHintExtractor | None = None):
        self.config = config
        self.judge = judge or RuleBasedBinaryJudge()
        self.opd_extractor = opd_extractor or HeuristicOpdHintExtractor()
        self.reward_log_path = config.resolve_path(config.paths.rewards_jsonl)

    def run(self, traces: list[TraceRecord]) -> list[JudgedTraceRecord]:
        if not self.config.flags.judge_plane_enabled:
            raise RuntimeError("judge_plane_enabled=false")

        judged: list[JudgedTraceRecord] = []
        for trace in traces:
            result = self.judge.judge(trace)
            opd = self.opd_extractor.extract(trace, result)
            judged_record = JudgedTraceRecord(trace=trace, judge=result, opd_hint=opd)
            judged.append(judged_record)

            reward_record = RewardRecord(
                trace_id=trace.trace_id,
                session_id=trace.session_id,
                turn_id=trace.turn_id,
                policy_version=trace.policy_version,
                label=result.label,
                reward=result.reward,
                source=self.judge.__class__.__name__,
                reasons=result.reasons,
                confidence=result.confidence,
            )
            append_jsonl(self.reward_log_path, reward_record.to_dict())

        emit_log("judge.run.completed", {"input_count": len(traces), "judged_count": len(judged)})
        return judged


def save_judged_records(path: Path, records: list[JudgedTraceRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in records:
            f.write(__import__("json").dumps(item.to_dict(), ensure_ascii=False) + "\n")
    emit_log("judge.records.saved", {"path": str(path), "count": len(records)})


def load_judged_records(path: Path) -> list[JudgedTraceRecord]:
    rows = read_jsonl(path)
    out: list[JudgedTraceRecord] = []
    for row in rows:
        trace = TraceRecord(**row["trace"])
        judge = JudgeResult(**row["judge"])
        out.append(JudgedTraceRecord(trace=trace, judge=judge, opd_hint=row.get("opd_hint", {})))
    return out


def judged_to_dict(item: JudgedTraceRecord) -> dict[str, Any]:
    return asdict(item)

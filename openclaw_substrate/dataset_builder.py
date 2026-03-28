from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import SubstrateConfig
from .jsonlog import emit_log
from .schemas import JudgedTraceRecord


class DatasetBuilder:
    def __init__(self, config: SubstrateConfig):
        self.config = config
        self.out_dir = config.resolve_path(config.paths.datasets_dir)

    def build_all(self, records: list[JudgedTraceRecord], dataset_name: str = "openclaw_trace") -> dict[str, str]:
        if not self.config.flags.dataset_builder_enabled:
            raise RuntimeError("dataset_builder_enabled=false")

        self.out_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "binary_rl": str(self._build_binary_rl(records, dataset_name)),
            "opd": str(self._build_opd(records, dataset_name)),
            "sft": str(self._build_sft(records, dataset_name)),
            "llamafactory_sft": str(self._build_llamafactory_sft(records, dataset_name)),
            "manifest": str(self._build_manifest(dataset_name)),
        }
        emit_log("dataset.build.completed", {"dataset_name": dataset_name, "paths": paths})
        return paths

    def _build_binary_rl(self, records: list[JudgedTraceRecord], dataset_name: str) -> Path:
        path = self.out_dir / f"{dataset_name}.binary_rl.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in records:
                row = {
                    "trace_id": r.trace.trace_id,
                    "session_id": r.trace.session_id,
                    "turn_id": r.trace.turn_id,
                    "state": {
                        "request_text": r.trace.request_text,
                        "route": r.trace.route,
                        "metadata": r.trace.metadata,
                    },
                    "action": r.trace.route,
                    "reward": r.judge.reward,
                    "label": r.judge.label,
                    "policy_version": r.trace.policy_version,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def _build_opd(self, records: list[JudgedTraceRecord], dataset_name: str) -> Path:
        path = self.out_dir / f"{dataset_name}.opd.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in records:
                row = {
                    "trace_id": r.trace.trace_id,
                    "observation": r.opd_hint.get("observation", ""),
                    "problem": r.opd_hint.get("problem", ""),
                    "diagnosis": r.opd_hint.get("diagnosis", ""),
                    "label": r.judge.label,
                    "reward": r.judge.reward,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def _build_sft(self, records: list[JudgedTraceRecord], dataset_name: str) -> Path:
        path = self.out_dir / f"{dataset_name}.sft.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in records:
                row = {
                    "messages": [
                        {"role": "user", "content": r.trace.request_text},
                        {"role": "assistant", "content": r.trace.response_text},
                    ],
                    "meta": {
                        "trace_id": r.trace.trace_id,
                        "policy_version": r.trace.policy_version,
                        "label": r.judge.label,
                    },
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def _build_llamafactory_sft(self, records: list[JudgedTraceRecord], dataset_name: str) -> Path:
        path = self.out_dir / f"{dataset_name}.llamafactory_sft.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in records:
                row = {
                    "instruction": r.trace.request_text,
                    "input": "",
                    "output": r.trace.response_text,
                    "system": f"route={r.trace.route};policy={r.trace.policy_version}",
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def _build_manifest(self, dataset_name: str) -> Path:
        path = self.out_dir / f"{dataset_name}.manifest.json"
        manifest = {
            "dataset_name": dataset_name,
            "binary_rl": f"{dataset_name}.binary_rl.jsonl",
            "opd": f"{dataset_name}.opd.jsonl",
            "sft": f"{dataset_name}.sft.jsonl",
            "llamafactory_sft": f"{dataset_name}.llamafactory_sft.jsonl",
        }
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def export_dataset_info_json(dataset_root: Path, dataset_name: str, sft_filename: str) -> Path:
    info_path = dataset_root / "dataset_info.json"
    info: dict[str, Any] = {}
    if info_path.exists():
        info = json.loads(info_path.read_text(encoding="utf-8"))

    info[dataset_name] = {
        "file_name": sft_filename,
        "formatting": "alpaca",
        "columns": {
            "instruction": "instruction",
            "input": "input",
            "output": "output",
        },
    }
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info_path

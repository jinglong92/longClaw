from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..adapter_registry import AdapterRegistry
from ..config import SubstrateConfig
from ..jsonlog import emit_log
from ..schemas import AdapterRecord
from .base import TrainingBackend


class MlxLmBackend(TrainingBackend):
    name = "mlx-lm"

    def __init__(self, config: SubstrateConfig, registry: AdapterRegistry):
        self.config = config
        self.registry = registry

    def prepare_dataset(self, source_path: Path, out_dir: Path, dataset_name: str) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{dataset_name}.jsonl"
        shutil.copy2(source_path, target)
        ref = {
            "backend": self.name,
            "dataset_name": dataset_name,
            "path": str(target),
        }
        emit_log("backend.mlx.prepare_dataset", ref)
        return ref

    def train_adapter(self, dataset_ref: dict[str, Any], out_dir: Path, run_name: str) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        run_dir = out_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        cfg = {
            "backend": self.name,
            "base_model": self.config.mlx.default_base_model,
            "dataset_path": dataset_ref["path"],
            "lora": {
                "rank": self.config.mlx.lora_rank,
                "alpha": self.config.mlx.lora_alpha,
                "dropout": self.config.mlx.lora_dropout,
            },
            "train": {
                "learning_rate": self.config.mlx.learning_rate,
                "epochs": self.config.mlx.epochs,
            },
            "command_template": (
                "python -m mlx_lm.lora "
                "--model {base_model} --train-data {dataset_path} "
                "--adapter-path {adapter_path} --batch-size 1"
            ),
        }

        cfg_path = run_dir / "mlx_lora_config.json"
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

        adapter_dir = run_dir / "adapter"
        adapter_dir.mkdir(exist_ok=True)

        record = AdapterRecord.new(
            backend="mlx-lm",
            base_model=self.config.mlx.default_base_model,
            task_type="sft-lora",
            path=str(adapter_dir),
        )
        self.registry.register(record)

        payload = {
            "backend": self.name,
            "run_dir": str(run_dir),
            "config": str(cfg_path),
            "adapter_id": record.adapter_id,
            "adapter_path": str(adapter_dir),
        }
        emit_log("backend.mlx.train_adapter.config_generated", payload)
        return payload

    def evaluate_adapter(self, adapter_path: Path, eval_input: Path, out_path: Path) -> dict[str, Any]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "backend": self.name,
            "adapter_path": str(adapter_path),
            "eval_input": str(eval_input),
            "note": "Use shadow replay metrics from openclaw_substrate.shadow_eval for final gating.",
        }
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        emit_log("backend.mlx.evaluate_adapter", report)
        return report

    def export_adapter(self, adapter_path: Path, out_dir: Path) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / adapter_path.name
        if adapter_path.exists():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(adapter_path, target)

        payload = {
            "backend": self.name,
            "source": str(adapter_path),
            "exported_to": str(target),
        }
        emit_log("backend.mlx.export_adapter", payload)
        return payload

    def list_adapters(self) -> list[AdapterRecord]:
        return self.registry.list_adapters(backend=self.name)

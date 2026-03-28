from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..adapter_registry import AdapterRegistry
from ..config import SubstrateConfig
from ..dataset_builder import export_dataset_info_json
from ..jsonlog import emit_log
from ..schemas import AdapterRecord
from .base import TrainingBackend


class LlamaFactoryBackend(TrainingBackend):
    name = "llamafactory"

    def __init__(self, config: SubstrateConfig, registry: AdapterRegistry):
        self.config = config
        self.registry = registry

    def prepare_dataset(self, source_path: Path, out_dir: Path, dataset_name: str) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{dataset_name}.jsonl"
        target.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        info_path = export_dataset_info_json(out_dir, dataset_name, target.name)

        payload = {
            "backend": self.name,
            "dataset_path": str(target),
            "dataset_info": str(info_path),
            "dataset_name": dataset_name,
        }
        emit_log("backend.llamafactory.prepare_dataset", payload)
        return payload

    def train_adapter(self, dataset_ref: dict[str, Any], out_dir: Path, run_name: str) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        run_dir = out_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        train_yaml = self._render_train_yaml(dataset_ref)
        train_yaml_path = run_dir / "llamafactory_lora_sft.yaml"
        train_yaml_path.write_text(train_yaml, encoding="utf-8")

        export_yaml = self._render_export_yaml(run_name)
        export_yaml_path = run_dir / "llamafactory_export.yaml"
        export_yaml_path.write_text(export_yaml, encoding="utf-8")

        chat_yaml = self._render_chat_yaml(run_name)
        chat_yaml_path = run_dir / "llamafactory_chat.yaml"
        chat_yaml_path.write_text(chat_yaml, encoding="utf-8")

        command_templates = {
            "train": f"llamafactory-cli train {train_yaml_path}",
            "chat": f"llamafactory-cli chat {chat_yaml_path}",
            "export": f"llamafactory-cli export {export_yaml_path}",
        }
        (run_dir / "commands.json").write_text(json.dumps(command_templates, ensure_ascii=False, indent=2), encoding="utf-8")

        hooks = {
            "dpo_hook": "TODO: generate DPO YAML from preference dataset",
            "ppo_hook": "TODO: generate PPO YAML from reward model + rollout buffer",
            "rm_hook": "TODO: generate reward model YAML from binary preference pairs",
        }
        (run_dir / "future_hooks.json").write_text(json.dumps(hooks, ensure_ascii=False, indent=2), encoding="utf-8")

        adapter_dir = run_dir / "adapter_stub"
        adapter_dir.mkdir(exist_ok=True)

        record = AdapterRecord.new(
            backend="llamafactory",
            base_model=self.config.mlx.default_base_model,
            task_type="sft-lora",
            path=str(adapter_dir),
        )
        self.registry.register(record)

        payload = {
            "backend": self.name,
            "run_dir": str(run_dir),
            "train_yaml": str(train_yaml_path),
            "export_yaml": str(export_yaml_path),
            "chat_yaml": str(chat_yaml_path),
            "adapter_id": record.adapter_id,
            "commands": command_templates,
        }
        emit_log("backend.llamafactory.train_templates.generated", payload)
        return payload

    def evaluate_adapter(self, adapter_path: Path, eval_input: Path, out_path: Path) -> dict[str, Any]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "backend": self.name,
            "adapter_path": str(adapter_path),
            "eval_input": str(eval_input),
            "note": "Run local shadow evaluation first; remote eval optional.",
        }
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        emit_log("backend.llamafactory.evaluate_adapter", report)
        return report

    def export_adapter(self, adapter_path: Path, out_dir: Path) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "backend": self.name,
            "adapter_path": str(adapter_path),
            "export_dir": str(out_dir),
            "command": f"llamafactory-cli export {out_dir / 'llamafactory_export.yaml'}",
        }
        emit_log("backend.llamafactory.export_template", payload)
        return payload

    def list_adapters(self) -> list[AdapterRecord]:
        return self.registry.list_adapters(backend=self.name)

    def _render_train_yaml(self, dataset_ref: dict[str, Any]) -> str:
        cfg = self.config.llamafactory
        return f"""model_name_or_path: {self.config.mlx.default_base_model}
stage: {cfg.stage}
do_train: true
finetuning_type: {cfg.finetuning_type}
dataset: {dataset_ref['dataset_name']}
dataset_dir: {Path(dataset_ref['dataset_path']).parent}
template: {cfg.template}
cutoff_len: {cfg.cutoff_len}
learning_rate: {cfg.learning_rate}
num_train_epochs: {cfg.num_train_epochs}
per_device_train_batch_size: {cfg.per_device_train_batch_size}
gradient_accumulation_steps: {cfg.gradient_accumulation_steps}
output_dir: artifacts/llamafactory/output
"""

    def _render_export_yaml(self, run_name: str) -> str:
        return f"""model_name_or_path: {self.config.mlx.default_base_model}
adapter_name_or_path: artifacts/llamafactory/{run_name}/adapter_stub
export_dir: artifacts/llamafactory/{run_name}/merged
"""

    def _render_chat_yaml(self, run_name: str) -> str:
        return f"""model_name_or_path: {self.config.mlx.default_base_model}
adapter_name_or_path: artifacts/llamafactory/{run_name}/adapter_stub
template: {self.config.llamafactory.template}
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FeatureFlags:
    gateway_enabled: bool = True
    trace_plane_enabled: bool = True
    judge_plane_enabled: bool = True
    dataset_builder_enabled: bool = True
    shadow_eval_enabled: bool = True
    mlx_backend_enabled: bool = True
    llamafactory_backend_enabled: bool = True


@dataclass
class PathConfig:
    root_dir: str = "."
    traces_raw_jsonl: str = "artifacts/traces/raw_traces.jsonl"
    traces_rewarded_jsonl: str = "artifacts/traces/rewarded_traces.jsonl"
    rewards_jsonl: str = "artifacts/rewards/reward_log.jsonl"
    datasets_dir: str = "artifacts/datasets"
    replay_dir: str = "artifacts/replay"
    adapter_registry_path: str = "artifacts/adapters/registry.jsonl"
    adapter_store_dir: str = "artifacts/adapters"
    backend_export_dir: str = "artifacts/exports"


@dataclass
class GatewayConfig:
    host: str = "127.0.0.1"
    port: int = 8090
    default_backend: str = "mlx-lm"
    mlx_chat_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    timeout_seconds: float = 45.0
    mock_on_backend_error: bool = True


@dataclass
class WechatConfig:
    enabled: bool = False
    path: str = "/wechat/inbound"
    auth_header: str = "X-OpenClaw-Token"
    auth_token: str = ""
    default_model: str = "qwen2.5-local"
    system_prompt: str = "你是 OpenClaw 助手，请直接给出可执行回答。"
    session_prefix: str = "wx"


@dataclass
class PolicyConfig:
    policy_version: str = "v1"
    max_state_history_turns: int = 16
    eligibility_min_quality: float = 0.6


@dataclass
class MlxConfig:
    default_base_model: str = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    learning_rate: float = 2e-4
    epochs: int = 2


@dataclass
class LlamaFactoryConfig:
    stage: str = "sft"
    finetuning_type: str = "lora"
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 1e-4
    num_train_epochs: int = 3
    cutoff_len: int = 2048
    template: str = "qwen"


@dataclass
class SubstrateConfig:
    flags: FeatureFlags = field(default_factory=FeatureFlags)
    paths: PathConfig = field(default_factory=PathConfig)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    wechat: WechatConfig = field(default_factory=WechatConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    mlx: MlxConfig = field(default_factory=MlxConfig)
    llamafactory: LlamaFactoryConfig = field(default_factory=LlamaFactoryConfig)

    def resolve_path(self, rel: str) -> Path:
        root = Path(self.paths.root_dir).expanduser().resolve()
        return (root / rel).resolve()


def _merge_dataclass(dc_obj: Any, updates: dict[str, Any]) -> Any:
    for key, value in updates.items():
        if not hasattr(dc_obj, key):
            continue
        current = getattr(dc_obj, key)
        if hasattr(current, "__dataclass_fields__") and isinstance(value, dict):
            _merge_dataclass(current, value)
        else:
            setattr(dc_obj, key, value)
    return dc_obj


def load_config(path: str | None = None) -> SubstrateConfig:
    config = SubstrateConfig()
    if path is None:
        return config

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    _merge_dataclass(config, data)
    return config


def dump_default_config(path: str) -> None:
    cfg = asdict(SubstrateConfig())
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

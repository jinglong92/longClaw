# OpenClaw Training Substrate Architecture

## Scope

This substrate provides a local-first training workflow for Apple Silicon and keeps export portability to LLaMA-Factory.

## Design Goals

1. Local-first iteration on Mac mini M4 16GB.
2. Backend pluggability: MLX-LM local default, LLaMA-Factory export-ready default for scale-up.
3. Trace-first data model to support replay, judging, and dataset generation.
4. Additive integration with existing OpenClaw docs and routing model.

## Module Layout

- `openclaw_substrate/config.py`: runtime config + feature flags
- `openclaw_substrate/gateway.py`: OpenAI-compatible local chat gateway
- `openclaw_substrate/trace_plane.py`: canonical trace persistence + next-state assembly
- `openclaw_substrate/judge_plane.py`: rule-based judge + pluggable interfaces
- `openclaw_substrate/dataset_builder.py`: binary RL / OPD / SFT / LLaMA-Factory datasets
- `openclaw_substrate/shadow_eval.py`: baseline vs candidate replay metrics
- `openclaw_substrate/backends/*`: backend abstraction and implementations
- `openclaw_substrate/adapter_registry.py`: filesystem registry for adapter lifecycle
- `openclaw_substrate/cli.py`: operational CLI

## Runtime Planes

1. Gateway Plane
- Accepts `/v1/chat/completions` requests.
- Adds `session_id`, `turn_id`, `policy_version` metadata.
- Routes to local MLX endpoint by default.
- Persists canonical trace records.

2. Trace Plane
- Stores raw trace JSONL.
- Supports mainline/sideline split.
- Builds next-state windows for training/replay.
- Applies eligibility filter for trainable samples.

3. Judge Plane
- Rule-based binary rewards for deterministic local loop.
- LLM judge interface and OPD extractor are pluggable.
- Reward log is persisted as structured JSONL.

4. Dataset Plane
- Produces normalized datasets:
  - binary RL-style
  - OPD-style
  - SFT-style
  - LLaMA-Factory SFT export format

5. Backend Plane
- `MlxLmBackend`: local LoRA config generation, local adapter registry integration.
- `LlamaFactoryBackend`: export-ready YAML/config/command generation.

6. Evaluation Plane
- Shadow evaluation compares baseline vs candidate on:
  - wrong-route rate
  - retry rate
  - explicit correction rate
  - tool success proxy
  - trainable sample yield

## Feature Flags

All critical modules are toggleable via `FeatureFlags` in config:

- `gateway_enabled`
- `trace_plane_enabled`
- `judge_plane_enabled`
- `dataset_builder_enabled`
- `shadow_eval_enabled`
- `mlx_backend_enabled`
- `llamafactory_backend_enabled`

## Apple Silicon Assumptions

- Local training/inference path assumes MLX-LM-compatible model/runtime.
- No CUDA-only primitives required in local MVP.
- No bitsandbytes/FlashAttention/Deepspeed requirement for local workflow.

## Risk Notes

1. Gateway currently proxies a single MLX URL; no load balancing.
2. Rule judge is deterministic and lightweight; semantic judge quality is intentionally limited in MVP.
3. LLaMA-Factory backend is export/template-oriented in this phase; not guaranteed runnable on local Mac without environment setup.

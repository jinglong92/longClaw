# Local MLX Workflow (Apple Silicon)

## Goal

Run the full local loop on Mac mini M4 16GB:

1. local gateway
2. trace collection
3. next-state assembly
4. rule-based reward assignment
5. dataset building
6. local MLX LoRA config generation
7. shadow evaluation

## 0) Generate default config

```bash
python3 -m openclaw_substrate.cli config-dump-default \
  --path openclaw_substrate/configs/local.json
```

## 1) Start local MLX-LM serving

```bash
python3 -m openclaw_substrate.cli mlx-serve \
  --config openclaw_substrate/configs/local.json \
  --dry-run
```

Remove `--dry-run` to execute when `mlx_lm` is installed.

## 2) Start gateway

```bash
python3 -m openclaw_substrate.cli gateway-serve \
  --config openclaw_substrate/configs/local.json
```

Gateway endpoint: `http://127.0.0.1:8090/v1/chat/completions`

## 3) Produce traces

Send OpenAI-compatible chat requests through gateway with metadata:

- `session_id`
- `turn_id`
- `policy_version`

Raw traces are written to `artifacts/traces/raw_traces.jsonl`.

## 4) Assemble next-state

```bash
python3 -m openclaw_substrate.cli trace-assemble-next-state \
  --config openclaw_substrate/configs/local.json \
  --session-id sess_demo \
  --out artifacts/replay/next_state.json
```

## 5) Judge + reward

```bash
python3 -m openclaw_substrate.cli judge-run \
  --config openclaw_substrate/configs/local.json
```

Outputs:

- judged traces: `artifacts/traces/rewarded_traces.jsonl`
- reward log: `artifacts/rewards/reward_log.jsonl`

## 6) Build datasets

```bash
python3 -m openclaw_substrate.cli dataset-build \
  --config openclaw_substrate/configs/local.json \
  --dataset-name openclaw_demo
```

Outputs under `artifacts/datasets/`:

- `*.binary_rl.jsonl`
- `*.opd.jsonl`
- `*.sft.jsonl`
- `*.llamafactory_sft.jsonl`
- `*.manifest.json`

## 7) Generate MLX local LoRA config

```bash
python3 -m openclaw_substrate.cli backend-prepare-dataset \
  --config openclaw_substrate/configs/local.json \
  --backend mlx-lm \
  --source artifacts/datasets/openclaw_demo.sft.jsonl \
  --out-dir artifacts/mlx \
  --dataset-name openclaw_demo_sft

python3 -m openclaw_substrate.cli backend-train-adapter \
  --config openclaw_substrate/configs/local.json \
  --backend mlx-lm \
  --dataset-name openclaw_demo_sft \
  --dataset-path artifacts/mlx/openclaw_demo_sft.jsonl \
  --out-dir artifacts/mlx \
  --run-name run_local_mlx
```

Key artifact:

- `artifacts/mlx/run_local_mlx/mlx_lora_config.json`

## 8) Shadow eval

```bash
python3 -m openclaw_substrate.cli shadow-eval \
  --baseline artifacts/traces/rewarded_baseline.jsonl \
  --candidate artifacts/traces/rewarded_candidate.jsonl \
  --out artifacts/replay/shadow_report.json
```

## Notes

- Local path does not require CUDA/FlashAttention/bitsandbytes.
- If MLX backend is not reachable, gateway can return mock response when `mock_on_backend_error=true`.

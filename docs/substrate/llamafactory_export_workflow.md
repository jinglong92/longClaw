# LLaMA-Factory Export Workflow

## Goal

Keep local-first MLX iteration while generating export-ready artifacts for future remote LLaMA-Factory training.

## 1) Prepare dataset for LLaMA-Factory

```bash
python3 -m openclaw_substrate.cli backend-prepare-dataset \
  --config openclaw_substrate/configs/local.json \
  --backend llamafactory \
  --source artifacts/datasets/openclaw_demo.llamafactory_sft.jsonl \
  --out-dir artifacts/llamafactory \
  --dataset-name openclaw_demo_llf
```

This generates:

- `artifacts/llamafactory/openclaw_demo_llf.jsonl`
- `artifacts/llamafactory/dataset_info.json`

## 2) Generate train/export/chat templates

```bash
python3 -m openclaw_substrate.cli backend-train-adapter \
  --config openclaw_substrate/configs/local.json \
  --backend llamafactory \
  --dataset-name openclaw_demo_llf \
  --dataset-path artifacts/llamafactory/openclaw_demo_llf.jsonl \
  --out-dir artifacts/llamafactory \
  --run-name run_export_ready
```

Generated files:

- `llamafactory_lora_sft.yaml`
- `llamafactory_export.yaml`
- `llamafactory_chat.yaml`
- `commands.json` (CLI templates)
- `future_hooks.json` (DPO/PPO/RM hooks)

## 3) Use command templates

Example templates generated in `commands.json`:

- `llamafactory-cli train ...`
- `llamafactory-cli chat ...`
- `llamafactory-cli export ...`

## Notes

- MVP only guarantees export correctness and file generation.
- Local successful execution of LLaMA-Factory is not required on Mac mini M4.
- DPO/PPO/RM are intentionally stubbed via hooks for later extension.

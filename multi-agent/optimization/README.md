# Optimization Subsystem v0.1

This folder contains the internal optimization infrastructure for longClaw.

## Structure

- `instrumentation/`: runtime event emission, sink interfaces, trace aggregation
- `evaluators/`: metric suite and evaluator runner
- `replay/`: offline replay harness and CLI entry
- `registry/`: file-based version/config registry
- `policies/`: baseline route policy helpers
- `traces/`: default local JSONL event storage
- `reports/`: replay/evaluation report output

## Local replay

```bash
node multi-agent/optimization/replay/run-replay.js --mode evaluator-only
node multi-agent/optimization/replay/run-replay.js --mode route-comparison
```

## Notes

- This layer is internal-only and does not change visible routing labels.
- Default hidden mode is observe-only.

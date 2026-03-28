# Reward Design

## Current MVP judge

`RuleBasedBinaryJudge` computes a deterministic score per trace.

### Features

- positive signal:
  - `tool_success == true`
- negative signal:
  - `retries > 1`
  - `explicit_correction == true`
  - `wrong_route == true`
- quality prior:
  - `metadata.quality_score`

### Mapping

- if `score >= 0`: `label=1`, `reward=+1.0`
- if `score < 0`: `label=0`, `reward=-1.0`

## Why binary first

- deterministic
- easy to audit
- low local compute
- supports immediate dataset generation and replay gating

## OPD hints

`HeuristicOpdHintExtractor` outputs:

- Observation
- Problem
- Diagnosis

These fields are written into OPD dataset records for diagnostics-oriented training.

## Future extension points

- replace or augment with `LlmJudge`
- route-specific reward shaping
- pairwise preference conversion for DPO
- reward model training data synthesis

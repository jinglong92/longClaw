# Memory Retrieval Eval Notes (2026-04-21)

## Deliverables
- Sample set: `eval/memory_retrieval_samples_2026-04-21.json`
- Custom evaluator: `tools/eval_memory_retrieval.py`
- Custom baseline output: `eval/memory_retrieval_eval_custom_2026-04-21.json`
- Builtin results output: `eval/builtin_memory_search_results_2026-04-21.json` (pending subagent)
- Builtin eval output: `eval/memory_retrieval_eval_builtin_2026-04-21.json` (pending subagent)

## Sample design
- Total samples: 30
- Domains: JOB=12, ENGINEER=12, META=3, LIFE=3
- Coverage:
  - interview / scheduling / people / relative dates
  - recall-chain architecture / fallback / gateway ops
  - dev mode protocol / routing visibility
  - life preference / hospital preference

## Metrics
- Hit@1: top1 source is in expected_sources
- Hit@3: any of top3 sources is in expected_sources
- MRR: reciprocal rank of first expected source
- Keyword-Hit@1: top1 text contains at least 1-2 expected keywords
- Keyword-Hit@3: any of top3 texts contains expected keywords

## Current custom baseline
From `eval/memory_retrieval_eval_custom_2026-04-21.json`:

```json
{
  "n": 30,
  "hit_at_1": 0.2333,
  "hit_at_3": 0.4667,
  "mrr": 0.3667,
  "keyword_hit_at_1": 0.2,
  "keyword_hit_at_3": 0.3333
}
```

### Domain breakdown
- ENGINEER: Hit@1=0.1667, Hit@3=0.1667, MRR=0.2083
- JOB: Hit@1=0.3333, Hit@3=0.7500, MRR=0.5347
- LIFE: Hit@1=0.0000, Hit@3=0.3333, MRR=0.1944
- META: Hit@1=0.3333, Hit@3=0.6667, MRR=0.5000

## Initial interpretation
- custom chain currently works best on JOB scheduling / people / relative-date memory.
- ENGINEER retrieval is weak, mostly because broad technical terms pull in noisy logs and JD-analysis text.
- LIFE recall is underfit because current tokenization / ranking overweights frequent generic words and underweights preference-style memory.
- The sample set is intentionally strict: source-level matching penalizes semantically-close but wrong-location retrieval.

## Why this is interview-worthy
This eval setup shows:
1. you define a gold set instead of eyeballing examples,
2. you separate retrieval quality by domain,
3. you report both ranking metrics and semantic hit metrics,
4. you can explain failure modes concretely instead of claiming “感觉更准”.

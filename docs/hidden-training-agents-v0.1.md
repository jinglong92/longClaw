# Hidden Training Agents v0.1

## 1) Design goals

Hidden Training Agents v0.1 adds an internal optimization plane to longClaw without changing the visible routing contract.

Primary goals:

- collect runtime structured telemetry automatically from real runs
- derive replayable traces from append-only events
- run evaluator suites and hidden analysis in shadow/offline mode
- persist version metadata for prompts/config/evaluator/hidden policies
- surface optimization artifacts in console observability panels

## 2) Hard constraints preserved

- Visible route contract unchanged: `User -> CTRL -> [visible specialist(s)] -> CTRL -> User`
- Visible labels unchanged: `LIFE/JOB/WORK/PARENT/LEARN/MONEY/BRO/SIS`
- Hidden agents never appear in outward route labels
- Hidden layer defaults to observe-only (no auto-promotion, no auto-mutation)

## 3) Architecture

## 3.1 Planes

1. Visible control plane
   - `multi-agent/agent-console-mvp/server.js`
   - handles ingress, CTRL routing, specialist execution, final response

2. Hidden optimization plane
   - `multi-agent/hidden-agents/*`
   - internal analysis modules:
     - `ROUTER_AGENT`
     - `PLANNER_AGENT`
     - `MEMORY_AGENT`
     - `CRITIC_AGENT`
     - `EVAL_AGENT`
     - `PATCH_AGENT`
     - `SAFETY_AGENT`

3. Event + trace plane
   - `multi-agent/optimization/instrumentation/*`
   - event-first runtime instrumentation + sink abstraction + trace aggregation

4. Evaluation + replay plane
   - `multi-agent/optimization/evaluators/*`
   - `multi-agent/optimization/replay/*`

5. Registry plane
   - `multi-agent/optimization/registry/*`
   - versioned prompt/config/evaluator/hidden-policy artifacts

## 3.2 Runtime data flow

1. request enters `/api/chat`
2. runtime emits required events (append-only)
3. events are buffered and written to sinks (JSONL required, optional PG/Redis)
4. events grouped into traces by `run_id + session_id + request_id`
5. hidden agents analyze traces (shadow mode)
6. evaluator computes metrics
7. replay comparison artifacts generated
8. console endpoints expose events/traces/evaluations/comparisons

## 4) Event schema

Schema file:

- `multi-agent/shared/schemas/optimization-event.schema.json`

Required fields:

- `event_id`
- `run_id`
- `session_id`
- `request_id`
- `timestamp`
- `event_type`
- `actor_type`
- `actor_id`
- `parent_event_id`
- `payload`
- `metrics`
- `version_metadata`

Required event coverage in v0.1:

- `message_received`
- `context_built`
- `route_selected`
- `specialist_invoked`
- `specialist_completed`
- `tool_call_started`
- `tool_call_finished`
- `memory_read`
- `memory_write`
- `risk_audit_started`
- `risk_audit_finished`
- `final_response_emitted`
- `user_followup_received`

Version metadata fields:

- `router_version`
- `prompt_version`
- `memory_policy_version`
- `evaluator_version`
- `hidden_policy_version`

## 5) Trace schema

Schema file:

- `multi-agent/shared/schemas/optimization-trace.schema.json`

Trace fields include:

- identity/time: `trace_id`, `run_id`, `session_id`, `request_id`, `timestamp`
- request summary: `user_input`, `context_snapshot_summary`
- visible route: `selected_visible_route`
- hidden analysis: `hidden_analysis_events`
- execution: `plan_steps`, `tool_calls`
- memory: `memory_events.reads/writes`
- risk: `risk_audit_events.started/finished`
- output/cost/latency: `final_output_summary`, `cost_metrics`, `latency_metrics`
- eval/versioning: `evaluation_scores`, `version_metadata`
- lineage: `event_count`, `event_ids`

## 6) Instrumentation points

Instrumentation is attached in runtime control boundaries in `server.js` (not UI-only):

- ingress boundary (`/api/chat`) -> `message_received`
- context assembly -> `context_built`
- route decision -> `route_selected`
- specialist loop -> `specialist_invoked/completed`
- tool invocation boundaries -> `tool_call_started/finished`
- memory policy boundaries -> `memory_read/write`
- risk audit boundary -> `risk_audit_started/finished`
- final emission boundary -> `final_response_emitted`
- correction/retry/manual intervention signals -> `user_followup_received`

Additional internal events:

- `hidden_analysis_emitted`
- `evaluation_completed`
- `replay_comparison_generated`

## 7) Hidden agent responsibilities in v0.1

- `ROUTER_AGENT`: route quality stats + candidate route suggestions
- `PLANNER_AGENT`: over/under planning diagnostics
- `MEMORY_AGENT`: memory hit/pollution diagnostics
- `CRITIC_AGENT`: structured critique with failure typing
- `EVAL_AGENT`: metric suite runner wrapper
- `PATCH_AGENT`: machine-readable patch proposals (review-only)
- `SAFETY_AGENT`: guardrails for visible contract and patch safety

## 8) Evaluator metrics

Implemented initial suite:

- `task_completion_proxy`
- `unnecessary_clarification_rate`
- `tool_success_rate`
- `memory_hit_quality`
- `memory_pollution_rate`
- `route_confidence`
- `route_regret_proxy`
- `risk_audit_trigger_rate`
- `latency_ms`
- `token_cost_proxy`
- `human_override_needed`
- `failure_type` taxonomy

## 9) Replay modes

`multi-agent/optimization/replay/replay-harness.js` supports:

- `dry-run`
- `evaluator-only`
- `route-comparison`
- `prompt-version-comparison`

Reports are JSON machine-readable and can be persisted under `multi-agent/optimization/reports/`.

## 10) Console integration

Console now surfaces hidden optimization artifacts while preserving existing behavior:

- `/api/events` (with `actor_type=hidden_agent` filter)
- `/api/traces`
- `/api/evaluations`
- `/api/comparisons`
- `/api/replay`

UI additions:

- hidden event stream panel
- evaluation summary panel
- candidate-vs-baseline comparison panel

## 11) Extension points (future-safe)

v0.1 adds immediate-value interfaces for future work:

- policy registry versions (router/prompt/memory/evaluator/hidden)
- replay harness mode abstraction
- candidate route comparison APIs
- patch suggestion artifacts with safety gating

This enables future bandit/offline-RL/scheduler integration without rewriting the control plane.

## 12) Intentionally deferred

- online RL or auto-updating production prompts
- distributed scheduler/runtime
- full production-grade storage/indexing for telemetry
- high-dimensional reward modeling
- auto-deployment of patch proposals

v0.1 is intentionally infrastructure-first, observe-first, and contract-safe.

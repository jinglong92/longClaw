const test = require('node:test');
const assert = require('node:assert/strict');

const { runEvaluationSuite } = require('../../optimization/evaluators');

test('evaluation suite computes core metrics', () => {
  const trace = {
    trace_id: 'trace_eval_1',
    run_id: 'run_eval_1',
    session_id: 'sess_eval_1',
    request_id: 'req_eval_1',
    timestamp: new Date().toISOString(),
    user_input: '帮我做一个计划',
    context_snapshot_summary: 'context ready',
    selected_visible_route: ['WORK'],
    hidden_analysis_events: [],
    plan_steps: [
      {
        step_id: 'step_1',
        specialist: 'WORK',
        status: 'completed'
      }
    ],
    tool_calls: [
      {
        tool_call_id: 'tool_1',
        success: true
      }
    ],
    memory_events: {
      reads: [{ hit: true, relevance_score: 0.9 }],
      writes: [{ value_score: 0.8, pollution_risk: 0.1 }]
    },
    risk_audit_events: {
      started: [{ timestamp: new Date().toISOString() }],
      finished: [{ timestamp: new Date().toISOString(), risk_level: 'low' }]
    },
    final_output_summary: 'done',
    cost_metrics: {
      token_cost_proxy: 42
    },
    latency_metrics: {
      end_to_end_ms: 1200
    },
    evaluation_scores: {
      route_confidence_observed: 0.81
    },
    version_metadata: {
      router_version: 'router_policy_v1',
      prompt_version: 'prompt_bundle_v1',
      memory_policy_version: 'memory_policy_v1',
      evaluator_version: 'evaluator_v1',
      hidden_policy_version: 'hidden_policy_v1'
    },
    event_count: 8,
    event_ids: ['e1']
  };

  const report = runEvaluationSuite([trace]);
  assert.equal(report.trace_count, 1);
  assert.ok(report.summary.task_completion_proxy >= 0);
  assert.ok(report.summary.tool_success_rate >= 0);
  assert.ok(report.per_trace[0].scores.failure_type);
});

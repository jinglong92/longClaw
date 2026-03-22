const test = require('node:test');
const assert = require('node:assert/strict');

const { EVENT_TYPES } = require('../../optimization/instrumentation/event-types');
const { runReplay } = require('../../optimization/replay/replay-harness');

function baseMeta() {
  return {
    router_version: 'router_policy_v1',
    prompt_version: 'prompt_bundle_v1',
    memory_policy_version: 'memory_policy_v1',
    evaluator_version: 'evaluator_v1',
    hidden_policy_version: 'hidden_policy_v1'
  };
}

function mkEvent(eventType, payload = {}, metrics = {}, actorType = 'system', actorId = 'test') {
  return {
    event_id: `evt_${Math.random().toString(36).slice(2, 8)}`,
    run_id: 'run_replay_1',
    session_id: 'sess_replay_1',
    request_id: 'req_replay_1',
    timestamp: new Date().toISOString(),
    sequence: 1,
    event_type: eventType,
    actor_type: actorType,
    actor_id: actorId,
    parent_event_id: null,
    payload,
    metrics,
    version_metadata: baseMeta()
  };
}

test('replay harness supports route-comparison mode', () => {
  const events = [
    mkEvent(EVENT_TYPES.MESSAGE_RECEIVED, { text: '求职和接娃冲突' }, { text_length: 8 }, 'ingress', 'web_console'),
    mkEvent(EVENT_TYPES.CONTEXT_BUILT, { summary: 'context built' }, {}, 'ctrl', 'CTRL'),
    mkEvent(EVENT_TYPES.ROUTE_SELECTED, { visible_route: ['JOB', 'PARENT'] }, { route_confidence: 0.8 }, 'ctrl', 'CTRL'),
    mkEvent(EVENT_TYPES.SPECIALIST_INVOKED, { step_id: 'step_1' }, {}, 'visible_specialist', 'JOB'),
    mkEvent(EVENT_TYPES.SPECIALIST_COMPLETED, { step_id: 'step_1', summary: 'job done' }, { token_cost_proxy: 20 }, 'visible_specialist', 'JOB'),
    mkEvent(EVENT_TYPES.RISK_AUDIT_STARTED, { scope: 'response_validation' }, {}, 'risk_auditor', 'SAFETY_AGENT'),
    mkEvent(EVENT_TYPES.RISK_AUDIT_FINISHED, { risk_level: 'medium' }, {}, 'risk_auditor', 'SAFETY_AGENT'),
    mkEvent(EVENT_TYPES.FINAL_RESPONSE_EMITTED, { summary: 'done' }, { token_cost_proxy: 10 }, 'ctrl', 'CTRL')
  ];

  const report = runReplay({
    mode: 'route-comparison',
    events
  });

  assert.equal(report.payload.mode, 'route-comparison');
  assert.equal(typeof report.payload.route_comparison.match_rate, 'number');
  assert.ok(report.hidden_optimization.agent_results.length >= 6);
});

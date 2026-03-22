const test = require('node:test');
const assert = require('node:assert/strict');

const { EVENT_TYPES } = require('../../optimization/instrumentation/event-types');
const { aggregateEventsToTraces } = require('../../optimization/instrumentation/trace-aggregator');

let tsCounter = 0;

function mkEvent(overrides) {
  const baseVersion = {
    router_version: 'router_policy_v1',
    prompt_version: 'prompt_bundle_v1',
    memory_policy_version: 'memory_policy_v1',
    evaluator_version: 'evaluator_v1',
    hidden_policy_version: 'hidden_policy_v1'
  };
  return {
    event_id: `evt_${Math.random().toString(36).slice(2, 10)}`,
    run_id: 'run_trace_1',
    session_id: 'sess_trace_1',
    request_id: 'req_trace_1',
    timestamp: new Date(Date.now() + tsCounter++).toISOString(),
    sequence: 1,
    event_type: EVENT_TYPES.MESSAGE_RECEIVED,
    actor_type: 'system',
    actor_id: 'test',
    parent_event_id: null,
    payload: {},
    metrics: {},
    version_metadata: baseVersion,
    ...overrides
  };
}

test('aggregates event stream into trace schema', () => {
  const events = [
    mkEvent({
      event_type: EVENT_TYPES.MESSAGE_RECEIVED,
      actor_type: 'ingress',
      actor_id: 'web_console',
      payload: { text: '帮我安排面试和接娃冲突' }
    }),
    mkEvent({
      event_type: EVENT_TYPES.CONTEXT_BUILT,
      actor_type: 'ctrl',
      actor_id: 'CTRL',
      payload: { summary: 'context ready' }
    }),
    mkEvent({
      event_type: EVENT_TYPES.ROUTE_SELECTED,
      actor_type: 'ctrl',
      actor_id: 'CTRL',
      payload: { visible_route: ['JOB', 'PARENT'] },
      metrics: { route_confidence: 0.72 }
    }),
    mkEvent({
      event_type: EVENT_TYPES.SPECIALIST_INVOKED,
      actor_type: 'visible_specialist',
      actor_id: 'JOB',
      payload: { step_id: 'step_job_1' }
    }),
    mkEvent({
      event_type: EVENT_TYPES.SPECIALIST_COMPLETED,
      actor_type: 'visible_specialist',
      actor_id: 'JOB',
      payload: { step_id: 'step_job_1', summary: 'job output' },
      metrics: { token_cost_proxy: 40, latency_ms: 22 }
    }),
    mkEvent({
      event_type: EVENT_TYPES.TOOL_CALL_STARTED,
      actor_type: 'tool',
      actor_id: 'JOB_tool',
      payload: { tool_call_id: 'tool_1', tool_name: 'context_lookup' }
    }),
    mkEvent({
      event_type: EVENT_TYPES.TOOL_CALL_FINISHED,
      actor_type: 'tool',
      actor_id: 'JOB_tool',
      payload: { tool_call_id: 'tool_1', tool_name: 'context_lookup', success: true },
      metrics: { latency_ms: 18 }
    }),
    mkEvent({
      event_type: EVENT_TYPES.MEMORY_READ,
      actor_type: 'memory',
      actor_id: 'memory_store',
      payload: { source: 'memory_store', hit: true, query: '面试' },
      metrics: { relevance_score: 0.8 }
    }),
    mkEvent({
      event_type: EVENT_TYPES.MEMORY_WRITE,
      actor_type: 'memory',
      actor_id: 'memory_store',
      payload: { target: 'memory_store' },
      metrics: { value_score: 0.7, pollution_risk: 0.2 }
    }),
    mkEvent({
      event_type: EVENT_TYPES.RISK_AUDIT_STARTED,
      actor_type: 'risk_auditor',
      actor_id: 'SAFETY_AGENT',
      payload: { scope: 'response_validation' }
    }),
    mkEvent({
      event_type: EVENT_TYPES.RISK_AUDIT_FINISHED,
      actor_type: 'risk_auditor',
      actor_id: 'SAFETY_AGENT',
      payload: { risk_level: 'medium', notes: 'conflict detected' }
    }),
    mkEvent({
      event_type: EVENT_TYPES.FINAL_RESPONSE_EMITTED,
      actor_type: 'ctrl',
      actor_id: 'CTRL',
      payload: { summary: 'final answer' },
      metrics: { token_cost_proxy: 30 }
    })
  ];

  const traces = aggregateEventsToTraces(events);
  assert.equal(traces.length, 1);

  const trace = traces[0];
  assert.deepEqual(trace.selected_visible_route, ['JOB', 'PARENT']);
  assert.equal(trace.user_input.includes('面试'), true);
  assert.equal(trace.tool_calls.length, 1);
  assert.equal(trace.memory_events.reads.length, 1);
  assert.equal(trace.risk_audit_events.finished.length, 1);
  assert.equal(trace.final_output_summary, 'final answer');
  assert.ok(trace.event_count >= 12);
});

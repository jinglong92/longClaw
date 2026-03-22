const { EVENT_TYPE_SET, ACTOR_TYPE_SET } = require('./event-types');
const { isVisibleRouteLabel } = require('../../shared/types/visible-routing');

const REQUIRED_VERSION_FIELDS = [
  'router_version',
  'prompt_version',
  'memory_policy_version',
  'evaluator_version',
  'hidden_policy_version'
];

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function validateVersionMetadata(meta) {
  if (!isPlainObject(meta)) return false;
  for (const key of REQUIRED_VERSION_FIELDS) {
    if (typeof meta[key] !== 'string' || meta[key].length === 0) return false;
  }
  return true;
}

function validateEvent(event) {
  if (!isPlainObject(event)) return { ok: false, reason: 'event must be object' };

  const required = [
    'event_id',
    'run_id',
    'session_id',
    'request_id',
    'timestamp',
    'event_type',
    'actor_type',
    'actor_id',
    'parent_event_id',
    'payload',
    'metrics',
    'version_metadata'
  ];

  for (const key of required) {
    if (!(key in event)) {
      return { ok: false, reason: `missing field: ${key}` };
    }
  }

  if (typeof event.event_id !== 'string' || !event.event_id) {
    return { ok: false, reason: 'event_id must be non-empty string' };
  }
  if (typeof event.run_id !== 'string' || !event.run_id) {
    return { ok: false, reason: 'run_id must be non-empty string' };
  }
  if (typeof event.session_id !== 'string' || !event.session_id) {
    return { ok: false, reason: 'session_id must be non-empty string' };
  }
  if (typeof event.request_id !== 'string' || !event.request_id) {
    return { ok: false, reason: 'request_id must be non-empty string' };
  }
  if (typeof event.timestamp !== 'string' || !event.timestamp) {
    return { ok: false, reason: 'timestamp must be non-empty string' };
  }
  if (!EVENT_TYPE_SET.has(event.event_type)) {
    return { ok: false, reason: `unsupported event_type: ${event.event_type}` };
  }
  if (!ACTOR_TYPE_SET.has(event.actor_type)) {
    return { ok: false, reason: `unsupported actor_type: ${event.actor_type}` };
  }
  if (typeof event.actor_id !== 'string' || !event.actor_id) {
    return { ok: false, reason: 'actor_id must be non-empty string' };
  }
  if (!(event.parent_event_id === null || typeof event.parent_event_id === 'string')) {
    return { ok: false, reason: 'parent_event_id must be string or null' };
  }
  if (!isPlainObject(event.payload)) {
    return { ok: false, reason: 'payload must be object' };
  }
  if (!isPlainObject(event.metrics)) {
    return { ok: false, reason: 'metrics must be object' };
  }
  if (!validateVersionMetadata(event.version_metadata)) {
    return { ok: false, reason: 'version_metadata is invalid' };
  }

  return { ok: true };
}

function validateTrace(trace) {
  if (!isPlainObject(trace)) return { ok: false, reason: 'trace must be object' };

  const required = [
    'trace_id',
    'run_id',
    'session_id',
    'request_id',
    'timestamp',
    'user_input',
    'context_snapshot_summary',
    'selected_visible_route',
    'hidden_analysis_events',
    'plan_steps',
    'tool_calls',
    'memory_events',
    'risk_audit_events',
    'final_output_summary',
    'cost_metrics',
    'latency_metrics',
    'evaluation_scores',
    'version_metadata',
    'event_count',
    'event_ids'
  ];

  for (const key of required) {
    if (!(key in trace)) return { ok: false, reason: `missing field: ${key}` };
  }

  if (!Array.isArray(trace.selected_visible_route) || trace.selected_visible_route.length === 0 || trace.selected_visible_route.length > 2) {
    return { ok: false, reason: 'selected_visible_route must contain 1..2 labels' };
  }

  for (const role of trace.selected_visible_route) {
    if (!isVisibleRouteLabel(role)) {
      return { ok: false, reason: `invalid visible route label in trace: ${role}` };
    }
  }

  if (!Array.isArray(trace.hidden_analysis_events)) {
    return { ok: false, reason: 'hidden_analysis_events must be array' };
  }
  if (!Array.isArray(trace.plan_steps)) return { ok: false, reason: 'plan_steps must be array' };
  if (!Array.isArray(trace.tool_calls)) return { ok: false, reason: 'tool_calls must be array' };
  if (!isPlainObject(trace.memory_events)) return { ok: false, reason: 'memory_events must be object' };
  if (!isPlainObject(trace.risk_audit_events)) return { ok: false, reason: 'risk_audit_events must be object' };
  if (!isPlainObject(trace.cost_metrics)) return { ok: false, reason: 'cost_metrics must be object' };
  if (!isPlainObject(trace.latency_metrics)) return { ok: false, reason: 'latency_metrics must be object' };
  if (!isPlainObject(trace.evaluation_scores)) return { ok: false, reason: 'evaluation_scores must be object' };
  if (!Array.isArray(trace.event_ids)) return { ok: false, reason: 'event_ids must be array' };
  if (!validateVersionMetadata(trace.version_metadata)) {
    return { ok: false, reason: 'trace version_metadata is invalid' };
  }

  return { ok: true };
}

module.exports = {
  validateEvent,
  validateTrace,
  validateVersionMetadata,
  REQUIRED_VERSION_FIELDS,
  isPlainObject
};

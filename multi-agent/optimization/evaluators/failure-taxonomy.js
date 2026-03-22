const FAILURE_TYPES = Object.freeze([
  'none',
  'tool_failure',
  'memory_pollution',
  'route_regret',
  'risk_audit_miss',
  'latency_spike',
  'human_override'
]);

function classifyFailureType(trace) {
  const toolCalls = Array.isArray(trace.tool_calls) ? trace.tool_calls : [];
  const failedTools = toolCalls.filter(call => call.success === false);
  if (failedTools.length > 0) return 'tool_failure';

  const writes = trace.memory_events?.writes || [];
  const polluted = writes.filter(write => Number(write.pollution_risk || 0) >= 0.7);
  if (writes.length > 0 && polluted.length / writes.length >= 0.5) {
    return 'memory_pollution';
  }

  if (trace.evaluation_scores?.user_dissatisfied === true) {
    return 'route_regret';
  }

  const riskTriggered = (trace.risk_audit_events?.started || []).length > 0;
  if (!riskTriggered && trace.evaluation_scores?.high_impact_request === true) {
    return 'risk_audit_miss';
  }

  if (Number(trace.latency_metrics?.end_to_end_ms || 0) > 15_000) {
    return 'latency_spike';
  }

  if (trace.evaluation_scores?.human_override_needed === true) {
    return 'human_override';
  }

  return 'none';
}

module.exports = {
  FAILURE_TYPES,
  classifyFailureType
};

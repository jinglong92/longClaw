const { classifyFailureType } = require('./failure-taxonomy');

function safeDivide(a, b, fallback = 0) {
  if (!b) return fallback;
  return a / b;
}

function taskCompletionProxy(trace) {
  return trace.final_output_summary && trace.final_output_summary.trim().length > 0 ? 1 : 0;
}

function unnecessaryClarificationRate(trace) {
  const steps = trace.plan_steps || [];
  const clarificationSteps = steps.filter(step =>
    String(step.notes || '').toLowerCase().includes('clarif') ||
    String(step.output_summary || '').toLowerCase().includes('clarif')
  );
  return safeDivide(clarificationSteps.length, Math.max(1, steps.length), 0);
}

function toolSuccessRate(trace) {
  const calls = trace.tool_calls || [];
  if (!calls.length) return 1;
  const success = calls.filter(call => call.success === true).length;
  return safeDivide(success, calls.length, 0);
}

function memoryHitQuality(trace) {
  const reads = trace.memory_events?.reads || [];
  if (!reads.length) return 0.5;
  const hits = reads.filter(read => read.hit === true);
  const quality = hits.reduce((acc, read) => acc + Number(read.relevance_score || 0), 0);
  return safeDivide(quality, Math.max(1, hits.length), 0);
}

function memoryPollutionRate(trace) {
  const writes = trace.memory_events?.writes || [];
  if (!writes.length) return 0;
  const polluted = writes.filter(write => Number(write.pollution_risk || 0) >= 0.7);
  return safeDivide(polluted.length, writes.length, 0);
}

function routeConfidence(trace) {
  return Number(trace.evaluation_scores?.route_confidence_observed || 0.5);
}

function routeRegretProxy(trace) {
  const confidence = routeConfidence(trace);
  const dissatisfied = trace.evaluation_scores?.user_dissatisfied === true ? 1 : 0;
  const override = trace.evaluation_scores?.human_override_needed === true ? 1 : 0;
  return Math.min(1, (1 - confidence) * 0.6 + dissatisfied * 0.3 + override * 0.3);
}

function riskAuditTriggerRate(trace) {
  return (trace.risk_audit_events?.started || []).length > 0 ? 1 : 0;
}

function latencyMs(trace) {
  return Number(trace.latency_metrics?.end_to_end_ms || 0);
}

function tokenCostProxy(trace) {
  return Number(trace.cost_metrics?.token_cost_proxy || 0);
}

function humanOverrideNeeded(trace) {
  return trace.evaluation_scores?.human_override_needed === true ? 1 : 0;
}

function computeMetrics(trace) {
  const failureType = classifyFailureType(trace);

  return {
    task_completion_proxy: taskCompletionProxy(trace),
    unnecessary_clarification_rate: unnecessaryClarificationRate(trace),
    tool_success_rate: toolSuccessRate(trace),
    memory_hit_quality: memoryHitQuality(trace),
    memory_pollution_rate: memoryPollutionRate(trace),
    route_confidence: routeConfidence(trace),
    route_regret_proxy: routeRegretProxy(trace),
    risk_audit_trigger_rate: riskAuditTriggerRate(trace),
    latency_ms: latencyMs(trace),
    token_cost_proxy: tokenCostProxy(trace),
    human_override_needed: humanOverrideNeeded(trace),
    failure_type: failureType
  };
}

module.exports = {
  computeMetrics
};

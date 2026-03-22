const { classifyFailureType } = require('../../optimization/evaluators/failure-taxonomy');

const ID = 'CRITIC_AGENT';
const VERSION = 'critic_agent_v0.1';

function analyze(traces) {
  const critiques = traces.map(trace => {
    const failureType = classifyFailureType(trace);
    const topRisk = trace.risk_audit_events?.finished?.[0]?.risk_level || 'low';
    const gap =
      failureType === 'tool_failure'
        ? 'tool execution path is unstable'
        : failureType === 'route_regret'
          ? 'route decision confidence is weak'
          : failureType === 'memory_pollution'
            ? 'memory write policy is too permissive'
            : 'no obvious critical failure';

    return {
      trace_id: trace.trace_id,
      verdict: failureType === 'none' ? 'pass' : 'needs_attention',
      failure_type: failureType,
      top_risk: topRisk,
      critique: gap
    };
  });

  return {
    agent_id: ID,
    version: VERSION,
    summary: `critic generated ${critiques.length} critique(s)`,
    critiques
  };
}

module.exports = {
  ID,
  VERSION,
  analyze
};

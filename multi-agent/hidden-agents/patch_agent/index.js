const ID = 'PATCH_AGENT';
const VERSION = 'patch_agent_v0.1';

function clusterFailures(perTraceScores) {
  const groups = {};
  for (const item of perTraceScores || []) {
    const type = item.scores?.failure_type || 'none';
    if (type === 'none') continue;
    groups[type] = groups[type] || [];
    groups[type].push(item);
  }
  return groups;
}

function analyze({ evaluationReport }) {
  const clusters = clusterFailures(evaluationReport?.per_trace || []);
  const patches = [];

  for (const [type, items] of Object.entries(clusters)) {
    if (type === 'route_regret') {
      patches.push({
        patch_id: `patch_route_${Date.now()}`,
        target: 'router_policy',
        kind: 'keyword_weight_adjustment',
        confidence: 0.62,
        evidence_traces: items.map(item => item.trace_id).slice(0, 10),
        safety_review_required: true,
        proposal: {
          action: 'increase route confidence threshold for dual-specialist routing',
          suggested_change: {
            route_confidence_floor: 0.65
          }
        }
      });
    }

    if (type === 'memory_pollution') {
      patches.push({
        patch_id: `patch_memory_${Date.now()}`,
        target: 'memory_policy',
        kind: 'write_threshold',
        confidence: 0.71,
        evidence_traces: items.map(item => item.trace_id).slice(0, 10),
        safety_review_required: true,
        proposal: {
          action: 'tighten memory write threshold',
          suggested_change: {
            min_value_score_for_write: 0.5,
            max_pollution_risk_for_write: 0.4
          }
        }
      });
    }
  }

  return {
    agent_id: ID,
    version: VERSION,
    summary: `generated ${patches.length} patch proposal(s) from failure clusters`,
    patch_suggestions: patches
  };
}

module.exports = {
  ID,
  VERSION,
  analyze
};

const { candidateRouteFromTrace, isValidVisibleRoute } = require('../../optimization/policies/router-policy');

const ID = 'ROUTER_AGENT';
const VERSION = 'router_agent_v0.1';

function scoreTraceRouteQuality(trace) {
  const confidence = Number(trace.evaluation_scores?.route_confidence_observed || 0.5);
  const regret = Number(trace.evaluation_scores?.route_regret_proxy || 0);
  const dissatisfied = trace.evaluation_scores?.user_dissatisfied === true ? 1 : 0;
  return Math.max(0, Math.min(1, confidence - regret * 0.7 - dissatisfied * 0.4));
}

function analyze(traces) {
  const routeStats = {};
  const suggestions = [];

  for (const trace of traces) {
    const route = (trace.selected_visible_route || []).join('+') || 'unknown';
    routeStats[route] = routeStats[route] || {
      count: 0,
      avg_quality: 0
    };
    const quality = scoreTraceRouteQuality(trace);
    const stat = routeStats[route];
    stat.count += 1;
    stat.avg_quality = stat.avg_quality + (quality - stat.avg_quality) / stat.count;

    const candidate = candidateRouteFromTrace(trace);
    if (
      isValidVisibleRoute(candidate.visible_route) &&
      candidate.visible_route.join('+') !== (trace.selected_visible_route || []).join('+') &&
      quality < 0.4
    ) {
      suggestions.push({
        trace_id: trace.trace_id,
        baseline_route: trace.selected_visible_route,
        candidate_route: candidate.visible_route,
        reason: candidate.rationale
      });
    }
  }

  return {
    agent_id: ID,
    version: VERSION,
    summary: `analyzed ${traces.length} trace(s), route patterns=${Object.keys(routeStats).length}`,
    route_stats: routeStats,
    route_patch_candidates: suggestions.slice(0, 20)
  };
}

module.exports = {
  ID,
  VERSION,
  analyze,
  scoreTraceRouteQuality
};

const routerAgent = require('./router_agent');
const plannerAgent = require('./planner_agent');
const memoryAgent = require('./memory_agent');
const criticAgent = require('./critic_agent');
const evalAgent = require('./eval_agent');
const patchAgent = require('./patch_agent');
const safetyAgent = require('./safety_agent');

function runHiddenOptimization(traces, {
  evaluatorConfig = {}
} = {}) {
  const router = routerAgent.analyze(traces);
  const planner = plannerAgent.analyze(traces);
  const memory = memoryAgent.analyze(traces);
  const critic = criticAgent.analyze(traces);
  const evalResult = evalAgent.analyze(traces, evaluatorConfig);
  const patch = patchAgent.analyze({ evaluationReport: evalResult.report });

  const latestRoute = traces[traces.length - 1]?.selected_visible_route || ['LIFE'];
  const safety = safetyAgent.analyze({
    route: latestRoute,
    patchSuggestions: patch.patch_suggestions
  });

  return {
    generated_at: new Date().toISOString(),
    traces_analyzed: traces.length,
    agent_results: [router, planner, memory, critic, evalResult, patch, safety],
    evaluation_report: evalResult.report,
    patch_suggestions_safe: safety.safe_patch_suggestions,
    patch_suggestions_rejected: safety.rejected_patch_suggestions,
    route_contract_valid: safety.route_check?.ok === true
  };
}

module.exports = {
  runHiddenOptimization
};

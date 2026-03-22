const ID = 'PLANNER_AGENT';
const VERSION = 'planner_agent_v0.1';

function analyze(traces) {
  const findings = [];
  for (const trace of traces) {
    const steps = trace.plan_steps || [];
    const routeSize = (trace.selected_visible_route || []).length || 1;
    const stepCount = steps.length;
    const stepRatio = stepCount / routeSize;

    let status = 'balanced';
    if (stepRatio > 3) status = 'over_planning';
    else if (stepRatio < 1) status = 'under_planning';

    findings.push({
      trace_id: trace.trace_id,
      step_count: stepCount,
      route_size: routeSize,
      status,
      suggestion:
        status === 'over_planning'
          ? 'reduce decomposition depth and merge redundant specialist subtasks'
          : status === 'under_planning'
            ? 'add explicit decomposition step before specialist invocation'
            : 'keep current plan template'
    });
  }

  return {
    agent_id: ID,
    version: VERSION,
    summary: `planner reviewed ${traces.length} trace(s)`,
    findings
  };
}

module.exports = {
  ID,
  VERSION,
  analyze
};

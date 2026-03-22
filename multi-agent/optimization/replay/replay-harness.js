const fs = require('fs');
const path = require('path');
const { aggregateEventsToTraces } = require('../instrumentation/trace-aggregator');
const { loadEventsFromJsonl } = require('../instrumentation/sinks/jsonl-sink');
const { runEvaluationSuite } = require('../evaluators');
const { candidateRouteFromTrace } = require('../policies/router-policy');
const { runHiddenOptimization } = require('../../hidden-agents');

function summarizeTracePopulation(traces) {
  const routeHistogram = {};
  for (const trace of traces) {
    const key = (trace.selected_visible_route || []).join('+') || 'none';
    routeHistogram[key] = (routeHistogram[key] || 0) + 1;
  }
  return {
    trace_count: traces.length,
    route_histogram: routeHistogram
  };
}

function compareRoutes(traces) {
  const details = [];
  let matched = 0;
  for (const trace of traces) {
    const baseline = trace.selected_visible_route || [];
    const candidate = candidateRouteFromTrace(trace).visible_route;
    const same = baseline.join('+') === candidate.join('+');
    if (same) matched += 1;
    details.push({
      trace_id: trace.trace_id,
      baseline_route: baseline,
      candidate_route: candidate,
      same
    });
  }

  return {
    match_rate: traces.length ? matched / traces.length : 0,
    compared: traces.length,
    details
  };
}

function comparePromptVersions(traces, { baseline = null, candidate = null } = {}) {
  const grouped = {};
  for (const trace of traces) {
    const promptVersion = trace.version_metadata?.prompt_version || 'unknown';
    grouped[promptVersion] = grouped[promptVersion] || [];
    grouped[promptVersion].push(trace);
  }

  const versions = Object.keys(grouped);
  const baselineVersion = baseline || versions[0] || 'unknown';
  const candidateVersion = candidate || versions.find(v => v !== baselineVersion) || baselineVersion;

  const baseEval = runEvaluationSuite(grouped[baselineVersion] || []);
  const candEval = runEvaluationSuite(grouped[candidateVersion] || []);

  return {
    baseline_version: baselineVersion,
    candidate_version: candidateVersion,
    baseline_summary: baseEval.summary,
    candidate_summary: candEval.summary,
    baseline_trace_count: baseEval.trace_count,
    candidate_trace_count: candEval.trace_count
  };
}

function writeReport(report, reportPath) {
  if (!reportPath) return null;
  const absPath = path.resolve(reportPath);
  fs.mkdirSync(path.dirname(absPath), { recursive: true });
  fs.writeFileSync(absPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  return absPath;
}

function runReplay({
  mode = 'dry-run',
  events = null,
  traces = null,
  evaluatorConfig = {},
  baseline = {},
  candidate = {},
  reportPath = null
} = {}) {
  const materializedTraces = Array.isArray(traces)
    ? traces
    : aggregateEventsToTraces(Array.isArray(events) ? events : []);

  let payload;
  if (mode === 'dry-run') {
    payload = {
      mode,
      summary: summarizeTracePopulation(materializedTraces)
    };
  } else if (mode === 'evaluator-only') {
    payload = {
      mode,
      evaluation: runEvaluationSuite(materializedTraces, evaluatorConfig)
    };
  } else if (mode === 'route-comparison') {
    payload = {
      mode,
      route_comparison: compareRoutes(materializedTraces),
      evaluation: runEvaluationSuite(materializedTraces, evaluatorConfig)
    };
  } else if (mode === 'prompt-version-comparison') {
    payload = {
      mode,
      prompt_version_comparison: comparePromptVersions(materializedTraces, {
        baseline: baseline.prompt_version,
        candidate: candidate.prompt_version
      }),
      evaluation: runEvaluationSuite(materializedTraces, evaluatorConfig)
    };
  } else {
    throw new Error(`unsupported replay mode: ${mode}`);
  }

  const hiddenOptimization = runHiddenOptimization(materializedTraces, {
    evaluatorConfig
  });

  const report = {
    replay_version: 'replay_v0.1',
    generated_at: new Date().toISOString(),
    trace_count: materializedTraces.length,
    payload,
    hidden_optimization: hiddenOptimization
  };

  const savedPath = writeReport(report, reportPath);
  if (savedPath) report.report_path = savedPath;
  return report;
}

function runReplayFromJsonl({ jsonlPath, ...rest }) {
  const events = loadEventsFromJsonl(jsonlPath);
  return runReplay({ ...rest, events });
}

module.exports = {
  runReplay,
  runReplayFromJsonl,
  summarizeTracePopulation,
  compareRoutes,
  comparePromptVersions
};

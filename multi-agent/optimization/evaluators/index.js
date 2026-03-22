const { computeMetrics } = require('./metrics');

function aggregateMetricValues(perTraceScores, metricKey) {
  const values = perTraceScores
    .map(item => item.scores[metricKey])
    .filter(value => typeof value === 'number' && Number.isFinite(value));
  if (!values.length) return null;
  return values.reduce((acc, value) => acc + value, 0) / values.length;
}

function runEvaluationSuite(traces, {
  evaluator_version = 'evaluator_v1',
  enabled_metrics = null
} = {}) {
  const per_trace = [];

  for (const trace of traces) {
    const scores = computeMetrics(trace);
    if (Array.isArray(enabled_metrics) && enabled_metrics.length > 0) {
      for (const key of Object.keys(scores)) {
        if (!enabled_metrics.includes(key)) {
          delete scores[key];
        }
      }
    }
    per_trace.push({
      trace_id: trace.trace_id,
      run_id: trace.run_id,
      request_id: trace.request_id,
      scores
    });
  }

  const metricKeys = new Set();
  for (const item of per_trace) {
    for (const key of Object.keys(item.scores)) metricKeys.add(key);
  }

  const summary = {};
  for (const key of metricKeys) {
    if (key === 'failure_type') {
      const counts = {};
      for (const item of per_trace) {
        const type = item.scores.failure_type || 'none';
        counts[type] = (counts[type] || 0) + 1;
      }
      summary.failure_type = counts;
      continue;
    }
    summary[key] = aggregateMetricValues(per_trace, key);
  }

  return {
    evaluator_version,
    generated_at: new Date().toISOString(),
    trace_count: traces.length,
    summary,
    per_trace
  };
}

module.exports = {
  runEvaluationSuite
};

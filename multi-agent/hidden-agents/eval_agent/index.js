const { runEvaluationSuite } = require('../../optimization/evaluators');

const ID = 'EVAL_AGENT';
const VERSION = 'eval_agent_v0.1';

function analyze(traces, config = {}) {
  const report = runEvaluationSuite(traces, config);
  return {
    agent_id: ID,
    version: VERSION,
    summary: `evaluation completed on ${report.trace_count} trace(s)`,
    report
  };
}

module.exports = {
  ID,
  VERSION,
  analyze
};

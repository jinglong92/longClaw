const ID = 'MEMORY_AGENT';
const VERSION = 'memory_agent_v0.1';

function analyze(traces) {
  const findings = [];

  for (const trace of traces) {
    const reads = trace.memory_events?.reads || [];
    const writes = trace.memory_events?.writes || [];
    const hitCount = reads.filter(read => read.hit === true).length;
    const lowValueWrites = writes.filter(write => Number(write.value_score || 0) < 0.4).length;
    const pollutionWrites = writes.filter(write => Number(write.pollution_risk || 0) > 0.6).length;

    findings.push({
      trace_id: trace.trace_id,
      memory_hit_quality: reads.length ? hitCount / reads.length : 0,
      low_value_write_rate: writes.length ? lowValueWrites / writes.length : 0,
      memory_pollution_rate: writes.length ? pollutionWrites / writes.length : 0,
      recommendation:
        pollutionWrites > 0
          ? 'raise write threshold and require value_score>=0.5 for auto-write'
          : 'current memory policy acceptable'
    });
  }

  return {
    agent_id: ID,
    version: VERSION,
    summary: `memory policy reviewed over ${traces.length} trace(s)`,
    findings
  };
}

module.exports = {
  ID,
  VERSION,
  analyze
};

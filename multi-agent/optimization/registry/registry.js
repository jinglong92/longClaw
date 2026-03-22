const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');

const DEFAULT_FILES = {
  'prompt-registry.json': {
    current: 'prompt_bundle_v1',
    items: [
      {
        id: 'prompt_bundle_v1',
        description: 'Baseline prompt bundle aligned with visible routing contract',
        created_at: '2026-03-22T00:00:00.000Z'
      }
    ]
  },
  'config-registry.json': {
    current: 'router_policy_v2',
    items: [
      {
        id: 'router_policy_v1',
        description: 'Keyword+risk constrained route policy',
        created_at: '2026-03-22T00:00:00.000Z'
      },
      {
        id: 'router_policy_v2',
        description: 'Conservative dual-route threshold to reduce low-confidence parallel routing',
        created_at: '2026-03-22T12:45:00.000Z'
      }
    ]
  },
  'evaluator-registry.json': {
    current: 'evaluator_v1',
    items: [
      {
        id: 'evaluator_v1',
        description: 'Initial metric suite for hidden training layer',
        created_at: '2026-03-22T00:00:00.000Z'
      }
    ]
  },
  'hidden-policy-registry.json': {
    current: 'hidden_policy_v1',
    items: [
      {
        id: 'hidden_policy_v1',
        description: 'Observe-only hidden optimization policy',
        created_at: '2026-03-22T00:00:00.000Z'
      }
    ]
  },
  'hidden-agent-registry.json': {
    current: 'hidden_agents_v1',
    items: [
      {
        id: 'hidden_agents_v1',
        agents: [
          'ROUTER_AGENT',
          'PLANNER_AGENT',
          'MEMORY_AGENT',
          'CRITIC_AGENT',
          'EVAL_AGENT',
          'PATCH_AGENT',
          'SAFETY_AGENT'
        ],
        mode: 'observe_only',
        created_at: '2026-03-22T00:00:00.000Z'
      }
    ]
  },
  'evaluator.config.json': {
    version: 'evaluator_v1',
    enabled_metrics: [
      'task_completion_proxy',
      'unnecessary_clarification_rate',
      'tool_success_rate',
      'memory_hit_quality',
      'memory_pollution_rate',
      'route_confidence',
      'route_regret_proxy',
      'risk_audit_trigger_rate',
      'latency_ms',
      'token_cost_proxy',
      'human_override_needed',
      'failure_type'
    ]
  },
  'instrumentation.config.json': {
    version: 'instrumentation_v1',
    jsonl_enabled: true,
    jsonl_path: 'multi-agent/optimization/traces/events.jsonl',
    flush_mode: 'buffered_non_blocking',
    strict_validation: true
  }
};

function ensureRegistryFiles(baseDir = DATA_DIR) {
  fs.mkdirSync(baseDir, { recursive: true });
  for (const [filename, content] of Object.entries(DEFAULT_FILES)) {
    const fp = path.join(baseDir, filename);
    if (!fs.existsSync(fp)) {
      fs.writeFileSync(fp, `${JSON.stringify(content, null, 2)}\n`, 'utf8');
    }
  }
}

function readRegistryFile(filename, baseDir = DATA_DIR) {
  ensureRegistryFiles(baseDir);
  const fp = path.join(baseDir, filename);
  const content = fs.readFileSync(fp, 'utf8');
  return JSON.parse(content);
}

function writeRegistryFile(filename, data, baseDir = DATA_DIR) {
  ensureRegistryFiles(baseDir);
  const fp = path.join(baseDir, filename);
  fs.writeFileSync(fp, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  return fp;
}

function getActiveVersions(baseDir = DATA_DIR) {
  const config = readRegistryFile('config-registry.json', baseDir);
  const prompt = readRegistryFile('prompt-registry.json', baseDir);
  const evaluator = readRegistryFile('evaluator-registry.json', baseDir);
  const hidden = readRegistryFile('hidden-policy-registry.json', baseDir);

  return {
    router_version: config.current,
    prompt_version: prompt.current,
    memory_policy_version: 'memory_policy_v1',
    evaluator_version: evaluator.current,
    hidden_policy_version: hidden.current
  };
}

function listRegistryState(baseDir = DATA_DIR) {
  ensureRegistryFiles(baseDir);
  const result = {};
  for (const filename of Object.keys(DEFAULT_FILES)) {
    result[filename] = readRegistryFile(filename, baseDir);
  }
  return result;
}

module.exports = {
  DATA_DIR,
  DEFAULT_FILES,
  ensureRegistryFiles,
  readRegistryFile,
  writeRegistryFile,
  getActiveVersions,
  listRegistryState
};

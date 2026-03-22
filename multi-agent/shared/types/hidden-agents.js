const HIDDEN_AGENT_IDS = Object.freeze([
  'ROUTER_AGENT',
  'PLANNER_AGENT',
  'MEMORY_AGENT',
  'CRITIC_AGENT',
  'EVAL_AGENT',
  'PATCH_AGENT',
  'SAFETY_AGENT'
]);

const HIDDEN_AGENT_SET = new Set(HIDDEN_AGENT_IDS);

function isHiddenAgentId(value) {
  return typeof value === 'string' && HIDDEN_AGENT_SET.has(value);
}

module.exports = {
  HIDDEN_AGENT_IDS,
  HIDDEN_AGENT_SET,
  isHiddenAgentId
};

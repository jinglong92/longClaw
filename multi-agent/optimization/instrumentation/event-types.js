const EVENT_TYPES = Object.freeze({
  MESSAGE_RECEIVED: 'message_received',
  CONTEXT_BUILT: 'context_built',
  ROUTE_SELECTED: 'route_selected',
  SPECIALIST_INVOKED: 'specialist_invoked',
  SPECIALIST_COMPLETED: 'specialist_completed',
  TOOL_CALL_STARTED: 'tool_call_started',
  TOOL_CALL_FINISHED: 'tool_call_finished',
  MEMORY_READ: 'memory_read',
  MEMORY_WRITE: 'memory_write',
  RISK_AUDIT_STARTED: 'risk_audit_started',
  RISK_AUDIT_FINISHED: 'risk_audit_finished',
  FINAL_RESPONSE_EMITTED: 'final_response_emitted',
  USER_FOLLOWUP_RECEIVED: 'user_followup_received',
  HIDDEN_ANALYSIS_EMITTED: 'hidden_analysis_emitted',
  EVALUATION_COMPLETED: 'evaluation_completed',
  REPLAY_COMPARISON_GENERATED: 'replay_comparison_generated'
});

const EVENT_TYPE_SET = new Set(Object.values(EVENT_TYPES));

const ACTOR_TYPES = Object.freeze({
  INGRESS: 'ingress',
  CTRL: 'ctrl',
  VISIBLE_SPECIALIST: 'visible_specialist',
  HIDDEN_AGENT: 'hidden_agent',
  TOOL: 'tool',
  MEMORY: 'memory',
  RISK_AUDITOR: 'risk_auditor',
  SYSTEM: 'system',
  USER: 'user'
});

const ACTOR_TYPE_SET = new Set(Object.values(ACTOR_TYPES));

module.exports = {
  EVENT_TYPES,
  EVENT_TYPE_SET,
  ACTOR_TYPES,
  ACTOR_TYPE_SET
};

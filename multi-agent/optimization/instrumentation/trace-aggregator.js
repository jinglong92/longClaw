const { validateTrace } = require('./validator');
const { isVisibleRouteLabel } = require('../../shared/types/visible-routing');
const { EVENT_TYPES } = require('./event-types');

function eventTimeMs(event) {
  const t = Date.parse(event.timestamp || '');
  return Number.isFinite(t) ? t : 0;
}

function groupKey(event) {
  const requestId = event.request_id || 'req_unknown';
  const sessionId = event.session_id || 'sess_unknown';
  const runId = event.run_id || 'run_unknown';
  return `${runId}::${sessionId}::${requestId}`;
}

function mkTraceSeed(event) {
  const route = ['LIFE'];
  return {
    trace_id: `trace_${event.run_id}_${event.request_id}`,
    run_id: event.run_id,
    session_id: event.session_id,
    request_id: event.request_id,
    timestamp: event.timestamp,
    user_input: '',
    context_snapshot_summary: '',
    selected_visible_route: route,
    hidden_analysis_events: [],
    plan_steps: [],
    tool_calls: [],
    memory_events: {
      reads: [],
      writes: []
    },
    risk_audit_events: {
      started: [],
      finished: []
    },
    final_output_summary: '',
    cost_metrics: {
      token_cost_proxy: 0
    },
    latency_metrics: {
      end_to_end_ms: 0
    },
    evaluation_scores: {},
    version_metadata: {
      ...event.version_metadata
    },
    event_count: 0,
    event_ids: []
  };
}

function aggregateEventsToTraces(events) {
  const sorted = [...events].sort((a, b) => eventTimeMs(a) - eventTimeMs(b));
  const grouped = new Map();

  for (const event of sorted) {
    const key = groupKey(event);
    if (!grouped.has(key)) {
      grouped.set(key, {
        trace: mkTraceSeed(event),
        specialistMap: new Map(),
        toolMap: new Map(),
        firstMs: eventTimeMs(event),
        finalMs: null
      });
    }

    const bucket = grouped.get(key);
    const trace = bucket.trace;
    trace.event_count += 1;
    trace.event_ids.push(event.event_id);
    trace.version_metadata = {
      ...trace.version_metadata,
      ...event.version_metadata
    };

    const tokenCost = Number(event.metrics?.token_cost_proxy || 0);
    if (Number.isFinite(tokenCost)) {
      trace.cost_metrics.token_cost_proxy += tokenCost;
    }

    switch (event.event_type) {
      case EVENT_TYPES.MESSAGE_RECEIVED:
        if (!trace.user_input) {
          trace.user_input = String(event.payload?.text || event.payload?.message || '');
        }
        break;

      case EVENT_TYPES.CONTEXT_BUILT:
        trace.context_snapshot_summary = String(event.payload?.summary || '');
        break;

      case EVENT_TYPES.ROUTE_SELECTED: {
        const route = Array.isArray(event.payload?.visible_route) ? event.payload.visible_route : [];
        const filtered = route.filter(isVisibleRouteLabel).slice(0, 2);
        if (filtered.length > 0) {
          trace.selected_visible_route = filtered;
        }
        const confidence = Number(event.metrics?.route_confidence || event.payload?.confidence || 0);
        if (Number.isFinite(confidence) && confidence > 0) {
          trace.evaluation_scores.route_confidence_observed = confidence;
        }
        break;
      }

      case EVENT_TYPES.SPECIALIST_INVOKED: {
        const stepId = event.payload?.step_id || `${event.actor_id}_${trace.plan_steps.length + 1}`;
        const step = {
          step_id: stepId,
          specialist: event.actor_id,
          status: 'running',
          started_at: event.timestamp,
          completed_at: null,
          notes: event.payload?.notes || ''
        };
        trace.plan_steps.push(step);
        bucket.specialistMap.set(stepId, step);
        break;
      }

      case EVENT_TYPES.SPECIALIST_COMPLETED: {
        const stepId = event.payload?.step_id;
        if (stepId && bucket.specialistMap.has(stepId)) {
          const step = bucket.specialistMap.get(stepId);
          step.status = 'completed';
          step.completed_at = event.timestamp;
          step.output_summary = event.payload?.summary || '';
          step.latency_ms = Number(event.metrics?.latency_ms || 0);
        } else {
          trace.plan_steps.push({
            step_id: stepId || `${event.actor_id}_${trace.plan_steps.length + 1}`,
            specialist: event.actor_id,
            status: 'completed',
            started_at: null,
            completed_at: event.timestamp,
            output_summary: event.payload?.summary || '',
            latency_ms: Number(event.metrics?.latency_ms || 0)
          });
        }
        break;
      }

      case EVENT_TYPES.TOOL_CALL_STARTED: {
        const toolCallId = event.payload?.tool_call_id || `tool_${trace.tool_calls.length + 1}`;
        const call = {
          tool_call_id: toolCallId,
          tool_name: event.payload?.tool_name || 'unknown_tool',
          status: 'running',
          started_at: event.timestamp,
          finished_at: null,
          success: null,
          intent: event.payload?.intent || ''
        };
        trace.tool_calls.push(call);
        bucket.toolMap.set(toolCallId, call);
        break;
      }

      case EVENT_TYPES.TOOL_CALL_FINISHED: {
        const toolCallId = event.payload?.tool_call_id;
        const success = Boolean(event.payload?.success);
        if (toolCallId && bucket.toolMap.has(toolCallId)) {
          const call = bucket.toolMap.get(toolCallId);
          call.status = success ? 'completed' : 'failed';
          call.finished_at = event.timestamp;
          call.success = success;
          call.result_summary = event.payload?.result_summary || '';
          call.latency_ms = Number(event.metrics?.latency_ms || 0);
        } else {
          trace.tool_calls.push({
            tool_call_id: toolCallId || `tool_${trace.tool_calls.length + 1}`,
            tool_name: event.payload?.tool_name || 'unknown_tool',
            status: success ? 'completed' : 'failed',
            started_at: null,
            finished_at: event.timestamp,
            success,
            result_summary: event.payload?.result_summary || '',
            latency_ms: Number(event.metrics?.latency_ms || 0)
          });
        }
        break;
      }

      case EVENT_TYPES.MEMORY_READ:
        trace.memory_events.reads.push({
          timestamp: event.timestamp,
          source: event.payload?.source || 'memory_store',
          hit: Boolean(event.payload?.hit),
          query: event.payload?.query || '',
          relevance_score: Number(event.metrics?.relevance_score || 0)
        });
        break;

      case EVENT_TYPES.MEMORY_WRITE:
        trace.memory_events.writes.push({
          timestamp: event.timestamp,
          target: event.payload?.target || 'memory_store',
          write_type: event.payload?.write_type || 'note',
          value_score: Number(event.metrics?.value_score || 0),
          pollution_risk: Number(event.metrics?.pollution_risk || 0)
        });
        break;

      case EVENT_TYPES.RISK_AUDIT_STARTED:
        trace.risk_audit_events.started.push({
          timestamp: event.timestamp,
          scope: event.payload?.scope || 'general'
        });
        break;

      case EVENT_TYPES.RISK_AUDIT_FINISHED:
        trace.risk_audit_events.finished.push({
          timestamp: event.timestamp,
          risk_level: event.payload?.risk_level || 'low',
          notes: event.payload?.notes || ''
        });
        break;

      case EVENT_TYPES.FINAL_RESPONSE_EMITTED:
        trace.final_output_summary = String(event.payload?.summary || event.payload?.text || '');
        bucket.finalMs = eventTimeMs(event);
        break;

      case EVENT_TYPES.USER_FOLLOWUP_RECEIVED:
        trace.evaluation_scores.user_dissatisfied = true;
        if (event.payload?.manual_override || ['retry', 'reroute', 'cancel'].includes(event.payload?.action)) {
          trace.evaluation_scores.human_override_needed = true;
        }
        break;

      case EVENT_TYPES.HIDDEN_ANALYSIS_EMITTED:
        trace.hidden_analysis_events.push({
          agent_id: event.actor_id,
          summary: String(event.payload?.summary || ''),
          details: event.payload?.details || {}
        });
        break;

      case EVENT_TYPES.EVALUATION_COMPLETED:
        if (event.payload?.scores && typeof event.payload.scores === 'object') {
          trace.evaluation_scores = {
            ...trace.evaluation_scores,
            ...event.payload.scores
          };
        }
        break;

      default:
        break;
    }
  }

  const traces = [];
  for (const bucket of grouped.values()) {
    const trace = bucket.trace;
    if (bucket.finalMs && bucket.firstMs) {
      trace.latency_metrics.end_to_end_ms = Math.max(0, bucket.finalMs - bucket.firstMs);
    }

    const valid = validateTrace(trace);
    if (valid.ok) {
      traces.push(trace);
    }
  }

  return traces;
}

module.exports = {
  aggregateEventsToTraces
};

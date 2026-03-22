require('dotenv').config();
const express = require('express');
const path = require('path');
const http = require('http');
const fs = require('fs');
const { WebSocketServer } = require('ws');
const { Pool } = require('pg');
const Redis = require('ioredis');

const {
  TelemetryRuntime,
  EVENT_TYPES,
  ACTOR_TYPES,
  MemoryEventSink,
  JsonlEventSink,
  PgEventSink,
  RedisEventSink,
  aggregateEventsToTraces,
  loadEventsFromJsonl
} = require('../optimization/instrumentation');
const { selectVisibleRoute } = require('../optimization/policies/router-policy');
const { runEvaluationSuite } = require('../optimization/evaluators');
const { runReplay } = require('../optimization/replay/replay-harness');
const {
  ensureRegistryFiles,
  getActiveVersions,
  readRegistryFile
} = require('../optimization/registry/registry');
const safetyAgent = require('../hidden-agents/safety_agent');
const { runHiddenOptimization } = require('../hidden-agents');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const hasPg = Boolean(process.env.DATABASE_URL);
const hasRedis = Boolean(process.env.REDIS_URL);
const pool = hasPg ? new Pool({ connectionString: process.env.DATABASE_URL }) : null;
const redis = hasRedis ? new Redis(process.env.REDIS_URL) : null;

const workspaceRoot = path.resolve(__dirname, '..', '..');
const registryDataDir = path.join(__dirname, '..', 'optimization', 'registry', 'data');
ensureRegistryFiles(registryDataDir);

const instrumentationConfig = readRegistryFile('instrumentation.config.json', registryDataDir);
const evaluatorConfig = readRegistryFile('evaluator.config.json', registryDataDir);
const jsonlPathFromConfig = process.env.INSTRUMENTATION_JSONL_PATH || instrumentationConfig.jsonl_path;
const instrumentationJsonlPath = path.isAbsolute(jsonlPathFromConfig)
  ? jsonlPathFromConfig
  : path.join(workspaceRoot, jsonlPathFromConfig);

const state = {
  runs: [
    {
      id: 'run_001',
      sessionId: 'sess_001',
      status: 'running',
      startedAt: Date.now() - 90_000,
      title: '用户请求: 设计并开发控制台'
    }
  ],
  nodes: [
    {
      id: 'node_router_1',
      runId: 'run_001',
      attempt: 1,
      agentId: 'agent_router',
      nodeType: 'router',
      status: 'completed'
    },
    {
      id: 'node_agent_ui',
      runId: 'run_001',
      attempt: 1,
      agentId: 'agent_ui',
      nodeType: 'agent',
      status: 'running'
    }
  ],
  messages: [
    {
      id: 'msg_1',
      role: 'user',
      type: 'chat',
      text: '帮我设计一个可实时控制 agent 的页面',
      ts: Date.now() - 120_000
    },
    {
      id: 'msg_2',
      role: 'system',
      type: 'router',
      text: 'Router: 拆分为 UI 设计 / 事件模型 / 后端 API 三条子任务',
      ts: Date.now() - 110_000
    }
  ],
  logs: [
    { level: 'INFO', text: 'RunCreated run_001', ts: Date.now() - 90_000, seq: 1 },
    { level: 'INFO', text: 'NodeStarted node_router_1', ts: Date.now() - 89_000, seq: 2 },
    { level: 'INFO', text: 'NodeStarted node_agent_ui', ts: Date.now() - 88_000, seq: 3 }
  ],
  seq: 3,
  audit: [],
  events: [],
  memoryStore: [],
  optimization: {
    evaluations: [],
    hiddenAnalyses: [],
    comparisons: []
  }
};

const memoryEventSink = new MemoryEventSink({ maxItems: 20_000 });
const telemetrySinks = [memoryEventSink];
if (instrumentationConfig.jsonl_enabled !== false) {
  telemetrySinks.push(new JsonlEventSink(instrumentationJsonlPath));
}
if (pool) telemetrySinks.push(new PgEventSink(pool));
if (redis) telemetrySinks.push(new RedisEventSink(redis));

const telemetry = new TelemetryRuntime({
  sinks: telemetrySinks,
  strictValidation: instrumentationConfig.strict_validation !== false,
  versionResolver: () => getActiveVersions(registryDataDir),
  onError: err => {
    console.warn('[telemetry-warning]', err.message || String(err));
  }
});

const historicalEvents = loadEventsFromJsonl(instrumentationJsonlPath).slice(-5_000);
if (historicalEvents.length > 0) {
  state.events = historicalEvents;
}

async function initStorage() {
  if (!pool) return;
  const schemaPath = path.join(__dirname, 'schema.sql');
  const sql = fs.readFileSync(schemaPath, 'utf8');
  await pool.query(sql);
}

function emitTelemetryEvent(event) {
  const emitted = telemetry.emit(event);
  if (!emitted) return null;
  state.events.push(emitted);
  if (state.events.length > 20_000) {
    const overflow = state.events.length - 20_000;
    state.events.splice(0, overflow);
  }
  broadcast({ type: 'event.new', data: emitted });
  return emitted;
}

function appendLog(level, text, meta = {}) {
  const log = { level, text, ts: Date.now(), seq: ++state.seq, ...meta };
  state.logs.push(log);
  broadcast({ type: 'log.new', data: log });
}

function addAudit(action, before, after, reason = '') {
  const item = { id: `audit_${state.audit.length + 1}`, action, before, after, reason, ts: Date.now() };
  state.audit.push(item);
  return item;
}

function ensureRun(runId, sessionId = 'sess_001') {
  let run = state.runs.find(r => r.id === runId);
  if (!run) {
    run = {
      id: runId,
      sessionId,
      status: 'running',
      startedAt: Date.now(),
      title: '自动创建运行'
    };
    state.runs.unshift(run);
    appendLog('INFO', `RunCreated ${runId}`, { runId });
  }
  return run;
}

function detectFollowupSignal(text) {
  const lowered = String(text || '').toLowerCase();
  const followupKeywords = ['不对', '不是', '重试', '再来', '你错', '不满意', 'retry', 'reroute', '修正'];
  return followupKeywords.some(keyword => lowered.includes(keyword));
}

function buildContextSummary(text) {
  const lastMessages = state.messages.slice(-4).map(msg => `${msg.role}:${msg.type}`).join(' | ');
  const memorySize = state.memoryStore.length;
  return `input_len=${text.length}; last_msgs=[${lastMessages || 'none'}]; memory_size=${memorySize}`;
}

function readMemory(query) {
  const normalized = String(query || '').trim();
  if (!normalized) return [];
  const tokens = normalized.split(/\s+/).filter(Boolean);
  const matches = state.memoryStore.filter(item =>
    tokens.some(token => item.text.includes(token))
  );
  return matches.slice(-3);
}

function assessRisk(text) {
  const highImpactKeywords = ['投资', '离职', '医疗', '合同', '法律', '借贷'];
  const mediumImpactKeywords = ['面试', '预算', '育儿', '晋升'];
  const lowered = String(text || '').toLowerCase();
  if (highImpactKeywords.some(keyword => lowered.includes(keyword))) {
    return { level: 'high', score: 0.88, notes: 'high impact keyword matched' };
  }
  if (mediumImpactKeywords.some(keyword => lowered.includes(keyword))) {
    return { level: 'medium', score: 0.63, notes: 'medium impact keyword matched' };
  }
  return { level: 'low', score: 0.32, notes: 'no high impact signal' };
}

function estimateMemoryWriteValue(text, specialistCount, riskScore) {
  const hasExplicitMemoryIntent = /记住|remember/i.test(text);
  const base = Math.min(0.9, 0.3 + text.length / 180 + specialistCount * 0.08 + riskScore * 0.2);
  const valueScore = hasExplicitMemoryIntent ? Math.min(1, base + 0.2) : base;
  const pollutionRisk = Math.max(0.05, Math.min(0.95, 0.75 - valueScore + (text.length < 12 ? 0.15 : 0)));
  return {
    valueScore,
    pollutionRisk,
    shouldWrite: valueScore >= 0.5 && pollutionRisk <= 0.7
  };
}

function mockToolCall({ role, text }) {
  const startedAt = Date.now();
  const failSignal = /失败|error|超时/i.test(text);
  const success = !failSignal;
  const latencyMs = 30 + (text.length % 40);

  return {
    tool_name: 'context_lookup',
    success,
    latency_ms: latencyMs,
    result_summary: success
      ? `${role} tool returned context hints`
      : `${role} tool failed by simulated signal`,
    startedAt,
    finishedAt: startedAt + latencyMs
  };
}

function specialistSummary(role, text, toolResult, memoryHits) {
  const prefix = {
    LIFE: '给出可执行生活安排',
    JOB: '聚焦求职推进动作',
    WORK: '提供职场策略方案',
    PARENT: '给出育儿稳定方案',
    LEARN: '提供学习路径建议',
    MONEY: '给出风险优先理财建议',
    BRO: '轻松但直接地反馈',
    SIS: '从女性视角给沟通建议'
  }[role] || '提供通用建议';

  return `${prefix}；tool=${toolResult.success ? 'ok' : 'fail'}；memory_hits=${memoryHits.length}；input=${text.slice(0, 24)}`;
}

function trimList(list, maxSize = 100) {
  if (list.length > maxSize) {
    list.splice(maxSize);
  }
}

app.get('/api/runs', (req, res) => res.json({ items: state.runs }));
app.get('/api/messages', (req, res) => res.json({ items: state.messages }));
app.get('/api/logs', (req, res) => res.json({ items: state.logs.slice(-300) }));
app.get('/api/nodes', (req, res) => res.json({ items: state.nodes }));
app.get('/api/audit', (req, res) => res.json({ items: state.audit.slice(-100) }));

app.get('/api/events', (req, res) => {
  const limit = Math.max(1, Math.min(Number(req.query.limit || 200), 5000));
  const actorType = req.query.actor_type ? String(req.query.actor_type) : null;
  const runId = req.query.run_id ? String(req.query.run_id) : null;

  let items = state.events;
  if (actorType) items = items.filter(event => event.actor_type === actorType);
  if (runId) items = items.filter(event => event.run_id === runId);

  res.json({ items: items.slice(-limit) });
});

app.get('/api/traces', (req, res) => {
  const limit = Math.max(1, Math.min(Number(req.query.limit || 50), 1000));
  const traces = aggregateEventsToTraces(state.events);
  res.json({ items: traces.slice(-limit) });
});

app.get('/api/evaluations', (req, res) => {
  res.json({
    latest: state.optimization.evaluations[0] || null,
    items: state.optimization.evaluations.slice(0, 50)
  });
});

app.get('/api/comparisons', (req, res) => {
  res.json({
    latest: state.optimization.comparisons[0] || null,
    items: state.optimization.comparisons.slice(0, 50)
  });
});

app.post('/api/replay', (req, res) => {
  try {
    const mode = String(req.body?.mode || 'dry-run');
    const shouldPersist = Boolean(req.body?.persist);
    const traces = aggregateEventsToTraces(state.events);
    const reportPath = shouldPersist
      ? path.join(__dirname, '..', 'optimization', 'reports', `replay-${Date.now()}.json`)
      : null;

    const report = runReplay({
      mode,
      traces,
      evaluatorConfig,
      baseline: req.body?.baseline || {},
      candidate: req.body?.candidate || {},
      reportPath
    });

    state.optimization.comparisons.unshift({
      generated_at: report.generated_at,
      mode,
      payload: report.payload
    });
    trimList(state.optimization.comparisons, 200);
    res.json({ ok: true, report });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.post('/api/chat', async (req, res) => {
  const text = (req.body?.text || '').trim();
  if (!text) return res.status(400).json({ error: 'text is required' });

  const runId = String(req.body?.runId || 'run_001');
  const sessionId = String(req.body?.sessionId || 'sess_001');
  const requestId = `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  ensureRun(runId, sessionId);

  const t0 = Date.now();

  const messageReceived = emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.MESSAGE_RECEIVED,
    actor_type: ACTOR_TYPES.INGRESS,
    actor_id: 'web_console',
    parent_event_id: null,
    payload: {
      channel: 'web_console',
      text,
      role: 'user'
    },
    metrics: {
      text_length: text.length
    }
  });

  const maybeLastAssistant = [...state.messages].reverse().find(msg => msg.role === 'assistant');
  const isFollowup = Boolean(maybeLastAssistant && detectFollowupSignal(text));
  if (isFollowup) {
    emitTelemetryEvent({
      run_id: runId,
      session_id: sessionId,
      request_id: requestId,
      event_type: EVENT_TYPES.USER_FOLLOWUP_RECEIVED,
      actor_type: ACTOR_TYPES.USER,
      actor_id: 'user_feedback',
      parent_event_id: messageReceived?.event_id || null,
      payload: {
        signal: 'correction_or_retry',
        text
      },
      metrics: {
        dissatisfaction_signal: 1
      }
    });
  }

  const contextSummary = buildContextSummary(text);
  const contextBuilt = emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.CONTEXT_BUILT,
    actor_type: ACTOR_TYPES.CTRL,
    actor_id: 'CTRL',
    parent_event_id: messageReceived?.event_id || null,
    payload: {
      summary: contextSummary
    },
    metrics: {
      context_items: 1
    }
  });

  const memoryHits = readMemory(text);
  emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.MEMORY_READ,
    actor_type: ACTOR_TYPES.MEMORY,
    actor_id: 'memory_store',
    parent_event_id: contextBuilt?.event_id || null,
    payload: {
      source: 'in_memory_store',
      query: text,
      hit: memoryHits.length > 0,
      hit_items: memoryHits.map(item => ({ id: item.id, text: item.text.slice(0, 80) }))
    },
    metrics: {
      hit_count: memoryHits.length,
      relevance_score: memoryHits.length ? 0.7 : 0.2
    }
  });

  const routeDecision = selectVisibleRoute(text, { maxParallel: 2 });
  const routeSafety = safetyAgent.validateVisibleRoute(routeDecision.visible_route);
  if (!routeSafety.ok) {
    routeDecision.visible_route = ['LIFE'];
    routeDecision.confidence = 0.2;
    routeDecision.rationale = `fallback due to safety violation: ${routeSafety.reason}`;
  }

  const routeSelected = emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.ROUTE_SELECTED,
    actor_type: ACTOR_TYPES.CTRL,
    actor_id: 'CTRL',
    parent_event_id: contextBuilt?.event_id || null,
    payload: {
      visible_route: routeDecision.visible_route,
      rationale: routeDecision.rationale
    },
    metrics: {
      route_confidence: routeDecision.confidence
    }
  });

  const specialistOutputs = [];
  let totalTokenCostProxy = 0;

  for (const role of routeDecision.visible_route) {
    const stepId = `step_${requestId}_${role.toLowerCase()}`;

    let node = state.nodes.find(item => item.id === stepId);
    if (!node) {
      node = {
        id: stepId,
        runId,
        attempt: 1,
        agentId: role,
        nodeType: 'agent',
        status: 'running'
      };
      state.nodes.unshift(node);
      trimList(state.nodes, 500);
    }

    const specialistInvoked = emitTelemetryEvent({
      run_id: runId,
      session_id: sessionId,
      request_id: requestId,
      event_type: EVENT_TYPES.SPECIALIST_INVOKED,
      actor_type: ACTOR_TYPES.VISIBLE_SPECIALIST,
      actor_id: role,
      parent_event_id: routeSelected?.event_id || null,
      payload: {
        step_id: stepId,
        notes: `specialist ${role} started`
      },
      metrics: {}
    });

    const toolCallId = `tool_${requestId}_${role.toLowerCase()}`;
    const toolStart = emitTelemetryEvent({
      run_id: runId,
      session_id: sessionId,
      request_id: requestId,
      event_type: EVENT_TYPES.TOOL_CALL_STARTED,
      actor_type: ACTOR_TYPES.TOOL,
      actor_id: `${role}_tool`,
      parent_event_id: specialistInvoked?.event_id || null,
      payload: {
        tool_call_id: toolCallId,
        tool_name: 'context_lookup',
        intent: `support ${role} reasoning`
      },
      metrics: {}
    });

    const toolResult = mockToolCall({ role, text });
    emitTelemetryEvent({
      run_id: runId,
      session_id: sessionId,
      request_id: requestId,
      event_type: EVENT_TYPES.TOOL_CALL_FINISHED,
      actor_type: ACTOR_TYPES.TOOL,
      actor_id: `${role}_tool`,
      parent_event_id: toolStart?.event_id || null,
      payload: {
        tool_call_id: toolCallId,
        tool_name: toolResult.tool_name,
        success: toolResult.success,
        result_summary: toolResult.result_summary
      },
      metrics: {
        latency_ms: toolResult.latency_ms
      }
    });

    const summary = specialistSummary(role, text, toolResult, memoryHits);
    const specialistLatency = Math.max(10, Date.now() - t0 - Math.floor(Math.random() * 15));
    const tokenCostProxy = 30 + Math.floor(text.length / 4) + role.length;

    emitTelemetryEvent({
      run_id: runId,
      session_id: sessionId,
      request_id: requestId,
      event_type: EVENT_TYPES.SPECIALIST_COMPLETED,
      actor_type: ACTOR_TYPES.VISIBLE_SPECIALIST,
      actor_id: role,
      parent_event_id: specialistInvoked?.event_id || null,
      payload: {
        step_id: stepId,
        summary
      },
      metrics: {
        latency_ms: specialistLatency,
        token_cost_proxy: tokenCostProxy
      }
    });

    node.status = 'completed';
    specialistOutputs.push({ role, summary });
    totalTokenCostProxy += tokenCostProxy;
    appendLog('INFO', `SpecialistCompleted ${role}`, { runId, nodeId: stepId });
  }

  const riskAuditStarted = emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.RISK_AUDIT_STARTED,
    actor_type: ACTOR_TYPES.RISK_AUDITOR,
    actor_id: 'SAFETY_AGENT',
    parent_event_id: routeSelected?.event_id || null,
    payload: {
      scope: 'response_validation'
    },
    metrics: {}
  });

  const risk = assessRisk(text);
  emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.RISK_AUDIT_FINISHED,
    actor_type: ACTOR_TYPES.RISK_AUDITOR,
    actor_id: 'SAFETY_AGENT',
    parent_event_id: riskAuditStarted?.event_id || null,
    payload: {
      risk_level: risk.level,
      notes: risk.notes
    },
    metrics: {
      risk_score: risk.score
    }
  });

  const writeDecision = estimateMemoryWriteValue(text, routeDecision.visible_route.length, risk.score);
  if (writeDecision.shouldWrite) {
    state.memoryStore.push({
      id: `mem_${Date.now().toString(36)}`,
      text: `${text.slice(0, 120)} | route=${routeDecision.visible_route.join('+')}`,
      createdAt: Date.now()
    });
    trimList(state.memoryStore, 1000);
  }

  emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.MEMORY_WRITE,
    actor_type: ACTOR_TYPES.MEMORY,
    actor_id: 'memory_store',
    parent_event_id: routeSelected?.event_id || null,
    payload: {
      target: 'in_memory_store',
      write_type: 'summary',
      accepted: writeDecision.shouldWrite
    },
    metrics: {
      value_score: writeDecision.valueScore,
      pollution_risk: writeDecision.pollutionRisk
    }
  });

  const routeLine = routeDecision.visible_route.length === 1
    ? `Routing: User -> CTRL -> [${routeDecision.visible_route[0]}] -> CTRL -> User`
    : `Routing: User -> CTRL -> ([${routeDecision.visible_route[0]}] || [${routeDecision.visible_route[1]}]) -> CTRL -> User`;

  const assistantSummary = specialistOutputs.map(item => `${item.role}: ${item.summary}`).join(' | ');
  const assistantText = `结论：${assistantSummary}\n${routeLine}`;
  const latencyMs = Date.now() - t0;

  const finalResponse = emitTelemetryEvent({
    run_id: runId,
    session_id: sessionId,
    request_id: requestId,
    event_type: EVENT_TYPES.FINAL_RESPONSE_EMITTED,
    actor_type: ACTOR_TYPES.CTRL,
    actor_id: 'CTRL',
    parent_event_id: routeSelected?.event_id || null,
    payload: {
      summary: assistantSummary,
      text: assistantText
    },
    metrics: {
      latency_ms: latencyMs,
      token_cost_proxy: totalTokenCostProxy,
      route_confidence: routeDecision.confidence
    }
  });

  const userMsg = {
    id: `msg_${state.messages.length + 1}`,
    role: 'user',
    type: 'chat',
    text,
    ts: Date.now()
  };
  state.messages.push(userMsg);

  const assistantMsg = {
    id: `msg_${state.messages.length + 1}`,
    role: 'assistant',
    type: 'chat',
    text: assistantText,
    ts: Date.now() + 5
  };
  state.messages.push(assistantMsg);
  trimList(state.messages, 5000);

  const requestEvents = state.events.filter(
    event => event.run_id === runId && event.request_id === requestId
  );
  const traces = aggregateEventsToTraces(requestEvents);
  const trace = traces[0];

  if (trace) {
    trace.evaluation_scores.route_confidence_observed = routeDecision.confidence;
    trace.evaluation_scores.user_dissatisfied = isFollowup;
    trace.evaluation_scores.high_impact_request = risk.level !== 'low';

    const evaluation = runEvaluationSuite([trace], evaluatorConfig);
    const scorePayload = evaluation.per_trace[0]?.scores || {};

    emitTelemetryEvent({
      run_id: runId,
      session_id: sessionId,
      request_id: requestId,
      event_type: EVENT_TYPES.EVALUATION_COMPLETED,
      actor_type: ACTOR_TYPES.HIDDEN_AGENT,
      actor_id: 'EVAL_AGENT',
      parent_event_id: finalResponse?.event_id || null,
      payload: {
        scores: scorePayload
      },
      metrics: {
        latency_ms: 1
      }
    });

    state.optimization.evaluations.unshift({
      generated_at: evaluation.generated_at,
      trace_id: trace.trace_id,
      report: evaluation
    });
    trimList(state.optimization.evaluations, 200);

    const hiddenAnalysis = runHiddenOptimization([trace], { evaluatorConfig });
    state.optimization.hiddenAnalyses.unshift(hiddenAnalysis);
    trimList(state.optimization.hiddenAnalyses, 200);

    for (const agentResult of hiddenAnalysis.agent_results) {
      if (agentResult.agent_id === 'EVAL_AGENT') continue;
      emitTelemetryEvent({
        run_id: runId,
        session_id: sessionId,
        request_id: requestId,
        event_type: EVENT_TYPES.HIDDEN_ANALYSIS_EMITTED,
        actor_type: ACTOR_TYPES.HIDDEN_AGENT,
        actor_id: agentResult.agent_id,
        parent_event_id: finalResponse?.event_id || null,
        payload: {
          summary: agentResult.summary,
          details: agentResult
        },
        metrics: {}
      });
    }

    const comparisonReport = runReplay({
      mode: 'route-comparison',
      traces: [trace],
      evaluatorConfig
    });

    state.optimization.comparisons.unshift({
      generated_at: comparisonReport.generated_at,
      payload: comparisonReport.payload
    });
    trimList(state.optimization.comparisons, 200);

    emitTelemetryEvent({
      run_id: runId,
      session_id: sessionId,
      request_id: requestId,
      event_type: EVENT_TYPES.REPLAY_COMPARISON_GENERATED,
      actor_type: ACTOR_TYPES.HIDDEN_AGENT,
      actor_id: 'ROUTER_AGENT',
      parent_event_id: finalResponse?.event_id || null,
      payload: {
        mode: 'route-comparison',
        summary: comparisonReport.payload?.route_comparison || {}
      },
      metrics: {}
    });
  }

  broadcast({ type: 'chat.new', data: [userMsg, assistantMsg] });
  broadcast({
    type: 'optimization.updated',
    data: {
      latestEvaluation: state.optimization.evaluations[0] || null,
      latestComparison: state.optimization.comparisons[0] || null
    }
  });
  res.json({ ok: true, items: [userMsg, assistantMsg] });
});

app.post('/api/runs/:runId/pause', (req, res) => {
  const run = state.runs.find(r => r.id === req.params.runId);
  if (!run) return res.status(404).json({ error: 'run not found' });
  const before = { ...run };
  run.status = 'paused';
  const requestId = `req_ctrl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  emitTelemetryEvent({
    run_id: run.id,
    session_id: run.sessionId || 'sess_001',
    request_id: requestId,
    event_type: EVENT_TYPES.USER_FOLLOWUP_RECEIVED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: 'manual_control',
    parent_event_id: null,
    payload: {
      action: 'pause',
      reason: req.body?.reason || 'manual'
    },
    metrics: {
      manual_override: 1
    }
  });
  addAudit('pause', before, run, req.body?.reason || 'manual');
  appendLog('WARN', `RunPaused ${run.id}`, { runId: run.id });
  broadcast({ type: 'run.updated', data: run });
  res.json({ ok: true, run });
});

app.post('/api/runs/:runId/resume', (req, res) => {
  const run = state.runs.find(r => r.id === req.params.runId);
  if (!run) return res.status(404).json({ error: 'run not found' });
  const before = { ...run };
  run.status = 'running';
  const requestId = `req_ctrl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  emitTelemetryEvent({
    run_id: run.id,
    session_id: run.sessionId || 'sess_001',
    request_id: requestId,
    event_type: EVENT_TYPES.USER_FOLLOWUP_RECEIVED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: 'manual_control',
    parent_event_id: null,
    payload: {
      action: 'resume',
      reason: req.body?.reason || 'manual'
    },
    metrics: {
      manual_override: 1
    }
  });
  addAudit('resume', before, run, req.body?.reason || 'manual');
  appendLog('INFO', `RunResumed ${run.id}`, { runId: run.id });
  broadcast({ type: 'run.updated', data: run });
  res.json({ ok: true, run });
});

app.post('/api/runs/:runId/cancel', (req, res) => {
  const run = state.runs.find(r => r.id === req.params.runId);
  if (!run) return res.status(404).json({ error: 'run not found' });
  const before = { ...run };
  run.status = 'canceled';
  const requestId = `req_ctrl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  emitTelemetryEvent({
    run_id: run.id,
    session_id: run.sessionId || 'sess_001',
    request_id: requestId,
    event_type: EVENT_TYPES.USER_FOLLOWUP_RECEIVED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: 'manual_control',
    parent_event_id: null,
    payload: {
      action: 'cancel',
      reason: req.body?.reason || 'manual'
    },
    metrics: {
      manual_override: 1
    }
  });
  addAudit('cancel', before, run, req.body?.reason || 'manual');
  appendLog('ERROR', `RunCanceled ${run.id}`, { runId: run.id });
  broadcast({ type: 'run.updated', data: run });
  res.json({ ok: true, run });
});

app.post('/api/nodes/:nodeId/retry', (req, res) => {
  const node = state.nodes.find(n => n.id === req.params.nodeId);
  if (!node) return res.status(404).json({ error: 'node not found' });
  const requestId = `req_ctrl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const retryNode = {
    ...node,
    id: `${node.id}_retry_${Date.now().toString().slice(-5)}`,
    attempt: (node.attempt || 1) + 1,
    status: 'running'
  };
  const before = { ...node };
  node.status = 'failed';
  state.nodes.push(retryNode);
  emitTelemetryEvent({
    run_id: node.runId,
    session_id: 'sess_001',
    request_id: requestId,
    event_type: EVENT_TYPES.USER_FOLLOWUP_RECEIVED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: 'manual_control',
    parent_event_id: null,
    payload: {
      action: 'retry',
      node_id: node.id,
      retry_node_id: retryNode.id,
      manual_override: true
    },
    metrics: {
      manual_override: 1
    }
  });
  addAudit('retry', before, retryNode, req.body?.reason || 'manual retry');
  appendLog('INFO', `NodeRetried ${node.id} -> ${retryNode.id}`, { runId: node.runId, nodeId: retryNode.id });
  broadcast({ type: 'node.retried', data: { from: node, to: retryNode } });
  res.json({ ok: true, node: retryNode });
});

app.post('/api/nodes/:nodeId/reroute', (req, res) => {
  const node = state.nodes.find(n => n.id === req.params.nodeId);
  if (!node) return res.status(404).json({ error: 'node not found' });
  const requestId = `req_ctrl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const targetAgentId = (req.body?.targetAgentId || '').trim();
  if (!targetAgentId) return res.status(400).json({ error: 'targetAgentId is required' });
  const targetCheck = safetyAgent.validateVisibleRoute([targetAgentId]);
  if (!targetCheck.ok) {
    return res.status(400).json({ error: `targetAgentId must be visible specialist label: ${targetCheck.reason}` });
  }
  const before = { ...node };
  node.agentId = targetAgentId;
  node.status = 'running';
  emitTelemetryEvent({
    run_id: node.runId,
    session_id: 'sess_001',
    request_id: requestId,
    event_type: EVENT_TYPES.USER_FOLLOWUP_RECEIVED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: 'manual_control',
    parent_event_id: null,
    payload: {
      action: 'reroute',
      node_id: node.id,
      target_agent_id: targetAgentId,
      manual_override: true
    },
    metrics: {
      manual_override: 1
    }
  });
  addAudit('reroute', before, node, req.body?.reason || 'manual reroute');
  appendLog('WARN', `RouteChanged ${node.id} -> ${targetAgentId}`, { runId: node.runId, nodeId: node.id });
  broadcast({ type: 'node.rerouted', data: node });
  res.json({ ok: true, node });
});

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

function broadcast(payload) {
  const msg = JSON.stringify(payload);
  for (const client of wss.clients) {
    if (client.readyState === 1) client.send(msg);
  }
}

wss.on('connection', socket => {
  socket.send(JSON.stringify({
    type: 'hello',
    data: {
      now: Date.now(),
      mode: hasPg || hasRedis ? 'hybrid' : 'memory',
      hasPg,
      hasRedis,
      telemetry: {
        jsonlPath: instrumentationJsonlPath,
        eventCount: state.events.length
      }
    }
  }));
});

setInterval(() => {
  const run = state.runs[0];
  if (!run || run.status !== 'running') return;
  appendLog('INFO', `ToolOutputChunk node_agent_ui seq=${state.seq + 1}`, { runId: run.id, nodeId: 'node_agent_ui' });
}, 4000);

const PORT = process.env.PORT || 3799;
const HOST = process.env.HOST || '0.0.0.0';

process.on('SIGINT', async () => {
  await telemetry.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await telemetry.close();
  process.exit(0);
});

initStorage()
  .then(() => {
    server.listen(PORT, HOST, () => {
      console.log(`agent-console-mvp running at http://${HOST}:${PORT}`);
      console.log(`storage mode => pg:${hasPg ? 'on' : 'off'} redis:${hasRedis ? 'on' : 'off'}`);
      console.log(`instrumentation jsonl => ${instrumentationJsonlPath}`);
    });
  })
  .catch(err => {
    console.error('failed to init storage', err);
    process.exit(1);
  });

const runListEl = document.getElementById('runList');
const chatStreamEl = document.getElementById('chatStream');
const logStreamEl = document.getElementById('logStream');
const nodeListEl = document.getElementById('nodeList');
const traceRunStreamEl = document.getElementById('traceRunStream');
const controlConsolePanelEl = document.getElementById('controlConsolePanel');
const controlConsoleToggleEl = document.getElementById('controlConsoleToggle');
const activeRouteNodeEl = document.getElementById('activeRouteNode');
const specialistRelationGridEl = document.getElementById('specialistRelationGrid');
const modeSummaryEl = document.getElementById('modeSummary');
const hiddenEventStreamEl = document.getElementById('hiddenEventStream');
const evaluationSummaryEl = document.getElementById('evaluationSummary');
const comparisonSummaryEl = document.getElementById('comparisonSummary');
const kpiAgentsEl = document.getElementById('kpiAgents');
const kpiRunsEl = document.getElementById('kpiRuns');
const kpiRiskEl = document.getElementById('kpiRisk');
const kpiLatencyEl = document.getElementById('kpiLatency');
const todayTimelineEl = document.getElementById('todayTimeline');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');

let VISIBLE_SPECIALISTS = ['LIFE', 'JOB', 'WORK', 'PARENT', 'LEARN', 'MONEY', 'BRO', 'SIS'];
let SPECIALIST_META = {};
let MODE_META = null;
const CONTROL_PANEL_STATE_KEY = 'longclaw.controlConsoleCollapsed';

let currentRunId = 'run_001';

async function init() {
  const [runsRes, msgRes, logsRes, nodesRes, tracesRes, eventsRes, evalRes, cmpRes, modeRes] = await Promise.all([
    fetch('/api/runs').then(r => r.json()),
    fetch('/api/messages').then(r => r.json()),
    fetch('/api/logs').then(r => r.json()),
    fetch('/api/nodes').then(r => r.json()),
    fetch('/api/traces?limit=80').then(r => r.json()),
    fetch('/api/events?actor_type=hidden_agent&limit=120').then(r => r.json()),
    fetch('/api/evaluations').then(r => r.json()),
    fetch('/api/comparisons').then(r => r.json()),
    fetch('/api/multi-agent/mode').then(r => r.json())
  ]);

  MODE_META = modeRes;
  VISIBLE_SPECIALISTS = Array.isArray(modeRes?.specialists)
    ? modeRes.specialists.map(item => item.id)
    : VISIBLE_SPECIALISTS;
  SPECIALIST_META = Object.fromEntries((modeRes?.specialists || []).map(item => [item.id, item]));

  renderRuns(runsRes.items || []);
  renderNodes(nodesRes.items || []);
  renderTraceRuns(tracesRes.items || []);
  renderTimeline(logsRes.items || []);
  renderModeSummary();
  renderOverview(modeRes, runsRes.items || [], tracesRes.items || []);
  renderControlConsole(nodesRes.items || [], tracesRes.items || []);
  (msgRes.items || []).forEach(pushMessage);
  (logsRes.items || []).forEach(pushLog);
  (eventsRes.items || []).forEach(pushHiddenEvent);
  renderEvaluationSummary(evalRes.latest || null);
  renderComparisonSummary(cmpRes.latest || null);

  bindToolbar();
  bindControlConsoleToggle();
  bindChat();
  connectWs();
}

function setControlConsoleCollapsed(collapsed) {
  if (collapsed) {
    controlConsolePanelEl.classList.add('collapsed');
    controlConsoleToggleEl.textContent = '展开';
  } else {
    controlConsolePanelEl.classList.remove('collapsed');
    controlConsoleToggleEl.textContent = '折叠';
  }
}

function bindControlConsoleToggle() {
  const stored = localStorage.getItem(CONTROL_PANEL_STATE_KEY);
  const initCollapsed = stored === '1';
  setControlConsoleCollapsed(initCollapsed);

  controlConsoleToggleEl.addEventListener('click', () => {
    const collapsed = !controlConsolePanelEl.classList.contains('collapsed');
    setControlConsoleCollapsed(collapsed);
    localStorage.setItem(CONTROL_PANEL_STATE_KEY, collapsed ? '1' : '0');
  });
}

function renderRuns(items) {
  runListEl.innerHTML = '';
  for (const run of items) {
    const li = document.createElement('li');
    li.innerHTML = `
      <div><strong>${run.id}</strong> <span class="badge ${run.status}">${run.status}</span></div>
      <div style="margin-top:6px;color:#9ca3af;font-size:12px">${run.title || ''}</div>
    `;
    runListEl.appendChild(li);
  }
}

function renderNodes(items) {
  nodeListEl.innerHTML = '';
  for (const node of items) {
    const div = document.createElement('div');
    div.className = 'node-item';
    div.innerHTML = `
      <div><strong>${node.id}</strong></div>
      <div style="color:#9ca3af;margin-top:4px">${node.agentId} · ${node.status}</div>
      <div class="actions">
        <button data-retry="${node.id}">Retry</button>
        <button data-reroute="${node.id}">Reroute</button>
      </div>
    `;
    nodeListEl.appendChild(div);
  }

  nodeListEl.querySelectorAll('button[data-retry]').forEach(btn => {
    btn.addEventListener('click', () => retryNode(btn.dataset.retry));
  });
  nodeListEl.querySelectorAll('button[data-reroute]').forEach(btn => {
    btn.addEventListener('click', () => rerouteNode(btn.dataset.reroute));
  });
}

function renderTraceRuns(items) {
  traceRunStreamEl.innerHTML = '';
  const latest = [...items].slice(-8).reverse();
  for (const trace of latest) {
    const div = document.createElement('div');
    div.className = 'trace-row';
    const route = Array.isArray(trace.selected_visible_route)
      ? trace.selected_visible_route.join('+')
      : 'unknown';
    div.textContent = `${trace.trace_id} | route=${route} | latency=${Math.round(trace.latency_metrics?.end_to_end_ms || 0)}ms`;
    traceRunStreamEl.appendChild(div);
  }
}

function renderModeSummary() {
  if (!MODE_META) {
    modeSummaryEl.textContent = '多代理模式元数据加载失败';
    return;
  }

  modeSummaryEl.innerHTML = `
    <div class="line"><strong>Mode:</strong> ${MODE_META.version || 'unknown'} | <strong>CTRL:</strong> ${MODE_META.ctrl?.id || 'CTRL'}</div>
    <div class="line"><strong>Contract:</strong> ${MODE_META.ctrl?.contract || 'N/A'}</div>
    <div class="line"><strong>Routing:</strong> ${MODE_META.routing?.default || 'N/A'}</div>
    <div class="line"><strong>Risk Audit:</strong> ${MODE_META.routing?.riskAudit || 'N/A'} | <strong>并行上限:</strong> ${MODE_META.routing?.parallelLimit || 1}</div>
  `;
}

function renderOverview(modeMeta, runs, traces) {
  kpiAgentsEl.textContent = Array.isArray(modeMeta?.specialists) ? modeMeta.specialists.length : '-';
  kpiRunsEl.textContent = runs.length;
  const latest = [...traces].slice(-10);
  const p95 = latest.length
    ? Math.max(...latest.map(item => Number(item?.latency_metrics?.end_to_end_ms || 0)))
    : 0;
  kpiLatencyEl.textContent = `${Math.round(p95)} ms`;

  const riskScore = latest.length
    ? latest.reduce((acc, item) => acc + Number(item?.evaluation_scores?.risk_score || 0), 0) / latest.length
    : 0;
  const riskLabel = riskScore >= 0.75 ? 'HIGH' : riskScore >= 0.45 ? 'MED' : 'LOW';
  kpiRiskEl.textContent = riskLabel;
}

function renderTimeline(logs) {
  todayTimelineEl.innerHTML = '';
  const items = [...logs].slice(-6).reverse();
  for (const log of items) {
    const row = document.createElement('div');
    row.className = 'timeline-row';
    const ts = new Date(log.ts).toLocaleTimeString();
    row.textContent = `${ts} · ${log.text}`;
    todayTimelineEl.appendChild(row);
  }
}

function latestNodeStatusBySpecialist(nodes) {
  const result = {};
  for (const specialist of VISIBLE_SPECIALISTS) {
    result[specialist] = 'idle';
  }

  for (const node of nodes) {
    if (!VISIBLE_SPECIALISTS.includes(node.agentId)) continue;
    if (node.runId !== currentRunId) continue;
    if (result[node.agentId] === 'idle') {
      result[node.agentId] = node.status || 'idle';
    }
  }
  return result;
}

function renderControlConsole(nodes, traces) {
  const latestTrace = [...traces].reverse().find(trace => trace.run_id === currentRunId) || [...traces].reverse()[0];
  const route = Array.isArray(latestTrace?.selected_visible_route)
    ? latestTrace.selected_visible_route
    : ['LIFE'];

  activeRouteNodeEl.textContent = route.length === 1
    ? `[${route[0]}]`
    : `([${route[0]}] || [${route[1]}])`;

  const statusMap = latestNodeStatusBySpecialist(nodes);
  specialistRelationGridEl.innerHTML = '';

  for (const specialist of VISIBLE_SPECIALISTS) {
    const status = statusMap[specialist] || 'idle';
    const meta = SPECIALIST_META[specialist] || {};
    const card = document.createElement('div');
    card.className = 'specialist-card';
    card.innerHTML = `
      <div class="specialist-name">${specialist}</div>
      <div class="specialist-link">${meta.domain || 'CTRL -> specialist -> CTRL'}</div>
      <div class="specialist-link">${meta.style || '默认风格'}</div>
      <span class="specialist-status ${status}">${status}</span>
    `;
    specialistRelationGridEl.appendChild(card);
  }
}

function pushMessage(msg) {
  const div = document.createElement('div');
  const roleClass = ['user', 'assistant', 'system'].includes(msg.role) ? msg.role : 'system';
  div.className = `msg ${roleClass}`;
  div.textContent = msg.text;
  chatStreamEl.appendChild(div);
  chatStreamEl.scrollTop = chatStreamEl.scrollHeight;
}

function pushLog(log) {
  const div = document.createElement('div');
  div.className = 'log-row';
  const t = new Date(log.ts).toLocaleTimeString();
  div.textContent = `[${t}] ${log.level} ${log.text}`;
  logStreamEl.appendChild(div);
  logStreamEl.scrollTop = logStreamEl.scrollHeight;
}

function pushHiddenEvent(event) {
  if (!event || event.actor_type !== 'hidden_agent') return;
  const div = document.createElement('div');
  div.className = 'hidden-event-row';
  const ts = new Date(event.timestamp || Date.now()).toLocaleTimeString();
  div.textContent = `[${ts}] ${event.actor_id} :: ${event.event_type}`;
  hiddenEventStreamEl.appendChild(div);
  hiddenEventStreamEl.scrollTop = hiddenEventStreamEl.scrollHeight;
}

function renderEvaluationSummary(item) {
  if (!item || !item.report) {
    evaluationSummaryEl.textContent = '暂无评估数据';
    return;
  }
  const report = item.report;
  evaluationSummaryEl.textContent = JSON.stringify(
    {
      generated_at: report.generated_at,
      trace_count: report.trace_count,
      summary: report.summary
    },
    null,
    2
  );
}

function renderComparisonSummary(item) {
  if (!item || !item.payload) {
    comparisonSummaryEl.textContent = '暂无候选对比';
    return;
  }
  comparisonSummaryEl.textContent = JSON.stringify(item.payload, null, 2);
}

async function refreshAll() {
  const [runsRes, nodesRes, tracesRes, evalRes, cmpRes, logsRes] = await Promise.all([
    fetch('/api/runs').then(r => r.json()),
    fetch('/api/nodes').then(r => r.json()),
    fetch('/api/traces?limit=80').then(r => r.json()),
    fetch('/api/evaluations').then(r => r.json()),
    fetch('/api/comparisons').then(r => r.json()),
    fetch('/api/logs').then(r => r.json())
  ]);
  renderRuns(runsRes.items || []);
  renderNodes(nodesRes.items || []);
  renderTraceRuns(tracesRes.items || []);
  renderTimeline(logsRes.items || []);
  renderModeSummary();
  renderOverview(MODE_META, runsRes.items || [], tracesRes.items || []);
  renderControlConsole(nodesRes.items || [], tracesRes.items || []);
  renderEvaluationSummary(evalRes.latest || null);
  renderComparisonSummary(cmpRes.latest || null);
}

function bindToolbar() {
  document.querySelectorAll('.toolbar button').forEach(btn => {
    btn.addEventListener('click', async () => {
      const action = btn.dataset.action;
      await fetch(`/api/runs/${currentRunId}/${action}`, { method: 'POST' });
      await refreshAll();
    });
  });
}

async function retryNode(nodeId) {
  await fetch(`/api/nodes/${nodeId}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy: 'from_input', reason: 'ui click retry' })
  });
  await refreshAll();
}

async function rerouteNode(nodeId) {
  const target = prompt('输入目标专职标签（LIFE/JOB/WORK/PARENT/LEARN/MONEY/BRO/SIS）', 'WORK');
  if (!target) return;
  await fetch(`/api/nodes/${nodeId}/reroute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ targetAgentId: target, reason: 'ui click reroute' })
  });
  await refreshAll();
}

function bindChat() {
  chatForm.addEventListener('submit', async e => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    if (text.startsWith('/pause')) {
      await fetch(`/api/runs/${currentRunId}/pause`, { method: 'POST' });
      chatInput.value = '';
      return refreshAll();
    }
    if (text.startsWith('/resume')) {
      await fetch(`/api/runs/${currentRunId}/resume`, { method: 'POST' });
      chatInput.value = '';
      return refreshAll();
    }
    if (text.startsWith('/cancel')) {
      await fetch(`/api/runs/${currentRunId}/cancel`, { method: 'POST' });
      chatInput.value = '';
      return refreshAll();
    }
    if (text.startsWith('/retry')) {
      const [, nodeId] = text.split(/\s+/);
      if (nodeId) await retryNode(nodeId);
      chatInput.value = '';
      return;
    }
    if (text.startsWith('/reroute')) {
      const [, nodeId, targetAgentId] = text.split(/\s+/);
      if (nodeId && targetAgentId) {
        await fetch(`/api/nodes/${nodeId}/reroute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ targetAgentId, reason: 'slash command' })
        });
        await refreshAll();
      }
      chatInput.value = '';
      return;
    }

    await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, runId: currentRunId })
    });
    chatInput.value = '';
  });
}

function connectWs() {
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.type === 'chat.new') {
      msg.data.forEach(pushMessage);
      return;
    }
    if (msg.type === 'run.updated') {
      refreshAll();
      pushMessage({ role: 'system', text: `Run ${msg.data.id} -> ${msg.data.status}` });
      return;
    }
    if (msg.type === 'node.retried') {
      refreshAll();
      pushMessage({ role: 'system', text: `Retried ${msg.data.from.id} -> ${msg.data.to.id}` });
      return;
    }
    if (msg.type === 'node.rerouted') {
      refreshAll();
      pushMessage({ role: 'system', text: `Rerouted ${msg.data.id} -> ${msg.data.agentId}` });
      return;
    }
    if (msg.type === 'log.new') {
      pushLog(msg.data);
      return;
    }
    if (msg.type === 'event.new') {
      pushHiddenEvent(msg.data);
      return;
    }
    if (msg.type === 'optimization.updated') {
      refreshAll();
    }
  };
}

init();

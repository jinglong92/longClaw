const runListEl = document.getElementById('runList');
const chatStreamEl = document.getElementById('chatStream');
const logStreamEl = document.getElementById('logStream');
const nodeListEl = document.getElementById('nodeList');
const traceRunStreamEl = document.getElementById('traceRunStream');
const hiddenEventStreamEl = document.getElementById('hiddenEventStream');
const evaluationSummaryEl = document.getElementById('evaluationSummary');
const comparisonSummaryEl = document.getElementById('comparisonSummary');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');

let currentRunId = 'run_001';

async function init() {
  const [runsRes, msgRes, logsRes, nodesRes, tracesRes, eventsRes, evalRes, cmpRes] = await Promise.all([
    fetch('/api/runs').then(r => r.json()),
    fetch('/api/messages').then(r => r.json()),
    fetch('/api/logs').then(r => r.json()),
    fetch('/api/nodes').then(r => r.json()),
    fetch('/api/traces?limit=80').then(r => r.json()),
    fetch('/api/events?actor_type=hidden_agent&limit=120').then(r => r.json()),
    fetch('/api/evaluations').then(r => r.json()),
    fetch('/api/comparisons').then(r => r.json())
  ]);

  renderRuns(runsRes.items || []);
  renderNodes(nodesRes.items || []);
  renderTraceRuns(tracesRes.items || []);
  (msgRes.items || []).forEach(pushMessage);
  (logsRes.items || []).forEach(pushLog);
  (eventsRes.items || []).forEach(pushHiddenEvent);
  renderEvaluationSummary(evalRes.latest || null);
  renderComparisonSummary(cmpRes.latest || null);

  bindToolbar();
  bindChat();
  connectWs();
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
  const [runsRes, nodesRes, tracesRes, evalRes, cmpRes] = await Promise.all([
    fetch('/api/runs').then(r => r.json()),
    fetch('/api/nodes').then(r => r.json()),
    fetch('/api/traces?limit=80').then(r => r.json()),
    fetch('/api/evaluations').then(r => r.json()),
    fetch('/api/comparisons').then(r => r.json())
  ]);
  renderRuns(runsRes.items || []);
  renderNodes(nodesRes.items || []);
  renderTraceRuns(tracesRes.items || []);
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

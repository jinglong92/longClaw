const runListEl = document.getElementById('runList');
const chatStreamEl = document.getElementById('chatStream');
const logStreamEl = document.getElementById('logStream');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');

let currentRunId = 'run_001';

async function init() {
  const [runsRes, msgRes, logsRes] = await Promise.all([
    fetch('/api/runs').then(r => r.json()),
    fetch('/api/messages').then(r => r.json()),
    fetch('/api/logs').then(r => r.json())
  ]);

  renderRuns(runsRes.items || []);
  (msgRes.items || []).forEach(pushMessage);
  (logsRes.items || []).forEach(pushLog);

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

function bindToolbar() {
  document.querySelectorAll('.toolbar button').forEach(btn => {
    btn.addEventListener('click', async () => {
      const action = btn.dataset.action;
      await fetch(`/api/runs/${currentRunId}/${action}`, { method: 'POST' });
    });
  });
}

function bindChat() {
  chatForm.addEventListener('submit', async e => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    if (text.startsWith('/pause')) {
      await fetch(`/api/runs/${currentRunId}/pause`, { method: 'POST' });
      chatInput.value = '';
      return;
    }
    if (text.startsWith('/resume')) {
      await fetch(`/api/runs/${currentRunId}/resume`, { method: 'POST' });
      chatInput.value = '';
      return;
    }
    if (text.startsWith('/cancel')) {
      await fetch(`/api/runs/${currentRunId}/cancel`, { method: 'POST' });
      chatInput.value = '';
      return;
    }

    await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
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
      fetch('/api/runs').then(r => r.json()).then(d => renderRuns(d.items || []));
      pushMessage({ role: 'system', text: `Run ${msg.data.id} -> ${msg.data.status}` });
      return;
    }
    if (msg.type === 'log.new') {
      pushLog(msg.data);
    }
  };
}

init();

const express = require('express');
const path = require('path');
const http = require('http');
const { WebSocketServer } = require('ws');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const runs = [
  {
    id: 'run_001',
    sessionId: 'sess_001',
    status: 'running',
    startedAt: Date.now() - 90_000,
    title: '用户请求: 设计并开发控制台'
  }
];

const messages = [
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
];

const eventState = {
  seq: 100,
  logs: [
    { level: 'INFO', text: 'RunCreated run_001', ts: Date.now() - 90_000 },
    { level: 'INFO', text: 'NodeStarted node_router_1', ts: Date.now() - 89_000 },
    { level: 'INFO', text: 'NodeStarted node_agent_ui', ts: Date.now() - 88_000 }
  ]
};

app.get('/api/runs', (req, res) => {
  res.json({ items: runs });
});

app.get('/api/messages', (req, res) => {
  res.json({ items: messages });
});

app.get('/api/logs', (req, res) => {
  res.json({ items: eventState.logs.slice(-200) });
});

app.post('/api/chat', (req, res) => {
  const text = (req.body?.text || '').trim();
  if (!text) return res.status(400).json({ error: 'text is required' });

  const userMsg = {
    id: `msg_${messages.length + 1}`,
    role: 'user',
    type: 'chat',
    text,
    ts: Date.now()
  };
  messages.push(userMsg);

  const assistantMsg = {
    id: `msg_${messages.length + 1}`,
    role: 'assistant',
    type: 'chat',
    text: `已接收指令：${text}。建议先执行 /retry 或 /reroute 等控制命令。`,
    ts: Date.now() + 5
  };
  messages.push(assistantMsg);

  broadcast({
    type: 'chat.new',
    data: [userMsg, assistantMsg]
  });

  res.json({ ok: true, items: [userMsg, assistantMsg] });
});

app.post('/api/runs/:runId/pause', (req, res) => {
  const run = runs.find(r => r.id === req.params.runId);
  if (!run) return res.status(404).json({ error: 'run not found' });
  run.status = 'paused';
  appendLog('WARN', `RunPaused ${run.id}`);
  broadcast({ type: 'run.updated', data: run });
  res.json({ ok: true, run });
});

app.post('/api/runs/:runId/resume', (req, res) => {
  const run = runs.find(r => r.id === req.params.runId);
  if (!run) return res.status(404).json({ error: 'run not found' });
  run.status = 'running';
  appendLog('INFO', `RunResumed ${run.id}`);
  broadcast({ type: 'run.updated', data: run });
  res.json({ ok: true, run });
});

app.post('/api/runs/:runId/cancel', (req, res) => {
  const run = runs.find(r => r.id === req.params.runId);
  if (!run) return res.status(404).json({ error: 'run not found' });
  run.status = 'canceled';
  appendLog('ERROR', `RunCanceled ${run.id}`);
  broadcast({ type: 'run.updated', data: run });
  res.json({ ok: true, run });
});

function appendLog(level, text) {
  const log = { level, text, ts: Date.now(), seq: ++eventState.seq };
  eventState.logs.push(log);
  broadcast({ type: 'log.new', data: log });
}

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

function broadcast(payload) {
  const msg = JSON.stringify(payload);
  for (const client of wss.clients) {
    if (client.readyState === 1) client.send(msg);
  }
}

wss.on('connection', socket => {
  socket.send(JSON.stringify({ type: 'hello', data: { now: Date.now() } }));
});

setInterval(() => {
  const run = runs[0];
  if (!run || run.status !== 'running') return;
  const text = `ToolOutputChunk node_agent_ui seq=${++eventState.seq}`;
  appendLog('INFO', text);
}, 4000);

const PORT = process.env.PORT || 3799;
server.listen(PORT, () => {
  console.log(`agent-console-mvp running at http://localhost:${PORT}`);
});

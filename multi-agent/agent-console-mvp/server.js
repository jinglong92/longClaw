require('dotenv').config();
const express = require('express');
const path = require('path');
const http = require('http');
const fs = require('fs');
const { WebSocketServer } = require('ws');
const { Pool } = require('pg');
const Redis = require('ioredis');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const hasPg = Boolean(process.env.DATABASE_URL);
const hasRedis = Boolean(process.env.REDIS_URL);
const pool = hasPg ? new Pool({ connectionString: process.env.DATABASE_URL }) : null;
const redis = hasRedis ? new Redis(process.env.REDIS_URL) : null;

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
  audit: []
};

async function initStorage() {
  if (!pool) return;
  const schemaPath = path.join(__dirname, 'schema.sql');
  const sql = fs.readFileSync(schemaPath, 'utf8');
  await pool.query(sql);
}

async function publishEvent(event) {
  if (redis) {
    await redis.xadd('agent_events', '*', 'data', JSON.stringify(event));
  }
  if (pool) {
    await pool.query(
      `INSERT INTO events (run_id, session_id, node_id, agent_id, seq, event_type, payload_json)
       VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)`,
      [
        event.runId,
        event.sessionId || 'sess_001',
        event.nodeId || null,
        event.agentId || null,
        event.seq,
        event.type,
        JSON.stringify(event.payload || {})
      ]
    );
  }
}

function appendLog(level, text, meta = {}) {
  const log = { level, text, ts: Date.now(), seq: ++state.seq, ...meta };
  state.logs.push(log);
  broadcast({ type: 'log.new', data: log });
  publishEvent({
    type: 'LogAppended',
    seq: log.seq,
    runId: meta.runId || 'run_001',
    nodeId: meta.nodeId,
    payload: { level, text }
  }).catch(() => {});
}

function addAudit(action, before, after, reason = '') {
  const item = { id: `audit_${state.audit.length + 1}`, action, before, after, reason, ts: Date.now() };
  state.audit.push(item);
  return item;
}

app.get('/api/runs', (req, res) => res.json({ items: state.runs }));
app.get('/api/messages', (req, res) => res.json({ items: state.messages }));
app.get('/api/logs', (req, res) => res.json({ items: state.logs.slice(-300) }));
app.get('/api/nodes', (req, res) => res.json({ items: state.nodes }));
app.get('/api/audit', (req, res) => res.json({ items: state.audit.slice(-100) }));

app.post('/api/chat', (req, res) => {
  const text = (req.body?.text || '').trim();
  if (!text) return res.status(400).json({ error: 'text is required' });

  const userMsg = { id: `msg_${state.messages.length + 1}`, role: 'user', type: 'chat', text, ts: Date.now() };
  state.messages.push(userMsg);

  const assistantMsg = {
    id: `msg_${state.messages.length + 1}`,
    role: 'assistant',
    type: 'chat',
    text: `已接收：${text}。你可继续用 /retry node_agent_ui 或 /reroute node_agent_ui agent_research。`,
    ts: Date.now() + 5
  };
  state.messages.push(assistantMsg);

  broadcast({ type: 'chat.new', data: [userMsg, assistantMsg] });
  res.json({ ok: true, items: [userMsg, assistantMsg] });
});

app.post('/api/runs/:runId/pause', (req, res) => {
  const run = state.runs.find(r => r.id === req.params.runId);
  if (!run) return res.status(404).json({ error: 'run not found' });
  const before = { ...run };
  run.status = 'paused';
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
  addAudit('cancel', before, run, req.body?.reason || 'manual');
  appendLog('ERROR', `RunCanceled ${run.id}`, { runId: run.id });
  broadcast({ type: 'run.updated', data: run });
  res.json({ ok: true, run });
});

app.post('/api/nodes/:nodeId/retry', (req, res) => {
  const node = state.nodes.find(n => n.id === req.params.nodeId);
  if (!node) return res.status(404).json({ error: 'node not found' });
  const retryNode = {
    ...node,
    id: `${node.id}_retry_${Date.now().toString().slice(-5)}`,
    attempt: (node.attempt || 1) + 1,
    status: 'running'
  };
  const before = { ...node };
  node.status = 'failed';
  state.nodes.push(retryNode);
  addAudit('retry', before, retryNode, req.body?.reason || 'manual retry');
  appendLog('INFO', `NodeRetried ${node.id} -> ${retryNode.id}`, { runId: node.runId, nodeId: retryNode.id });
  broadcast({ type: 'node.retried', data: { from: node, to: retryNode } });
  res.json({ ok: true, node: retryNode });
});

app.post('/api/nodes/:nodeId/reroute', (req, res) => {
  const node = state.nodes.find(n => n.id === req.params.nodeId);
  if (!node) return res.status(404).json({ error: 'node not found' });
  const targetAgentId = (req.body?.targetAgentId || '').trim();
  if (!targetAgentId) return res.status(400).json({ error: 'targetAgentId is required' });
  const before = { ...node };
  node.agentId = targetAgentId;
  node.status = 'running';
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
      hasRedis
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

initStorage()
  .then(() => {
    server.listen(PORT, HOST, () => {
      console.log(`agent-console-mvp running at http://${HOST}:${PORT}`);
      console.log(`storage mode => pg:${hasPg ? 'on' : 'off'} redis:${hasRedis ? 'on' : 'off'}`);
    });
  })
  .catch(err => {
    console.error('failed to init storage', err);
    process.exit(1);
  });

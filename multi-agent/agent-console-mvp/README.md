# Agent Console MVP (Chat-first)

一个可运行的开发起点：
- 中间主区域是对话流
- 右侧是运行控制 + 实时日志
- 左侧是 run 列表
- 支持 WebSocket 实时推送
- 支持基础控制动作（pause/resume/cancel）

## 快速启动

```bash
cd multi-agent/agent-console-mvp
npm install
npm run dev
# 打开 http://localhost:3799
```

## 当前能力（v0.2 prototype）

- [x] Chat-first 三栏 UI
- [x] REST API 基础接口
- [x] WebSocket 实时事件更新
- [x] slash 控制命令（/pause /resume /cancel /retry /reroute）
- [x] 节点列表 + Retry / Reroute 按钮
- [x] 审计记录 API（/api/audit）
- [x] 可选 Postgres + Redis Streams 接入（有环境变量就启用）
- [x] 深色主题与基础审美样式

## 环境变量

复制 `.env.example` 到 `.env` 并按需填写：

- `DATABASE_URL`：启用 Postgres 持久化
- `REDIS_URL`：启用 Redis Streams 事件总线
- `HOST` / `PORT`：监听地址和端口

## 下一步（你拍板后继续）

1. 把日志/事件全部改成真实 run/node event schema（目前仍有演示事件）
2. 加入控制流图（React Flow）
3. 加入 Agent 配置管理页（版本与回滚）
4. 增加操作确认弹窗 + 失败回滚策略

## 文档

- `schema.sql`：数据库草案
- `openapi.yaml`：接口草案

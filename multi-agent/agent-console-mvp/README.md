# Agent Console MVP (Chat-first)

一个可运行的开发起点：
- 中间主区域是对话流
- 右侧是运行控制 + 实时日志 + 隐藏层事件 + 评估摘要
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
- [x] 运行时结构化事件采集（event-first）
- [x] JSONL 本地事件落盘（默认）
- [x] 事件聚合为 trace（/api/traces）
- [x] 评估结果查看（/api/evaluations）
- [x] 候选对比查看（/api/comparisons）
- [x] 离线 replay API（/api/replay）

## 环境变量

复制 `.env.example` 到 `.env` 并按需填写：

- `DATABASE_URL`：启用 Postgres 持久化
- `REDIS_URL`：启用 Redis Streams 事件总线
- `HOST` / `PORT`：监听地址和端口
- `INSTRUMENTATION_JSONL_PATH`：可选，覆盖默认事件 JSONL 输出路径

## 运行测试

```bash
cd multi-agent/agent-console-mvp
npm test
```

## 下一步（你拍板后继续）

1. 为事件/trace 增加更细粒度的 DB 索引和归档策略
2. 将 replay 报告接入可视化趋势图
3. 增加 prompt/config 差分审计视图
4. 增加人工审批流（patch proposal -> review -> apply）

## 文档

- `schema.sql`：数据库草案
- `openapi.yaml`：接口草案
- `../optimization/README.md`：优化子系统入口
- `../../docs/hidden-training-agents-v0.1.md`：设计说明

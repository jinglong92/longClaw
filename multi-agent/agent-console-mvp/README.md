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

## 当前能力（v0.1 prototype）

- [x] Chat-first 三栏 UI
- [x] REST API 基础接口
- [x] WebSocket 实时事件更新
- [x] slash 控制命令（/pause /resume /cancel）
- [x] 深色主题与基础审美样式

## 下一步（你拍板后继续）

1. 接 Postgres + Redis Streams，替换当前内存存储
2. 加入节点级控制：retry/reroute
3. 加入控制流图（React Flow）
4. 加入 Agent 配置管理页（版本与回滚）
5. 增加审计日志与操作确认弹窗

## 文档

- `schema.sql`：数据库草案
- `openapi.yaml`：接口草案

---
name: proactive-heartbeat
description: 主动心跳——由 cron 定期触发 heartbeat-agent 巡检，发现有价值信息写入 heartbeat-state.json；用户下次开口时 CTRL 读取并在回复开头呈现待处理事项。
version: 1.0.0
author: jinglong92
license: MIT
requires: ["file_read", "file_write"]
---

# Proactive Heartbeat

两个独立机制配合：
1. **定期巡检**（cron 驱动）：heartbeat-agent 静默扫描，结果写入 heartbeat-state.json
2. **开口呈现**（SessionStart/每轮首次）：CTRL 读取 heartbeat-state.json，有 pending 时在回复开头展示

## 触发条件

**巡检触发**（cron，不是用户触发）：
- 每天早上 8:30 自动巡检（`30 8 * * *`）
- 每天下午 18:00 自动巡检（`0 18 * * *`）
- 用户说"做一次心跳巡检" / "检查一下我的待办"

**呈现触发**（每次 session 开始时）：
- SessionStart hook 读取 heartbeat-state.json
- 若 `has_pending: true` 且有未过期的 P0/P1 事项，在本轮回复开头呈现
- 呈现后清空已展示的 pending_items（避免重复提醒）

## 巡检流程

### Step 1：spawn heartbeat-agent
```
Agent(heartbeat-agent): 执行巡检，写入 heartbeat-state.json
```

### Step 2：静默等待
heartbeat-agent 在后台执行，不打断任何进行中的对话。

## 呈现流程（用户开口时）

### Step 1：读取 heartbeat-state.json
CTRL 在每次 session 开始或用户第一条消息时读取：
```
memory/heartbeat-state.json
```

### Step 2：判断是否呈现
- `has_pending: false` → 不呈现，直接回复用户
- `has_pending: true` 且所有 items 都是 P2 → 不呈现（系统健康信息不打断）
- `has_pending: true` 且有 P0/P1 → 呈现

### Step 3：呈现格式（在正常回复前，简短）

```
💡 [心跳提醒]
• [P0] <内容> → <建议行动>
• [P1] <内容>
---
```

呈现后在 heartbeat-state.json 中将已展示的 items 标记为 `shown: true`。

### Step 4：正常回复用户请求

## DEV LOG 约定
```
🧩 Skill proactive-heartbeat | trigger=<cron|session_start|manual>
🛠️ 工具 Agent(heartbeat-agent) → pending=<N>项 | status=ok
```

## 边界
- heartbeat-agent 只读+写 heartbeat-state.json，不写其他文件
- P2 系统健康信息只写入日志，不向用户呈现
- 同一事项最多提醒 2 次（`shown_count` 字段控制）
- 过期事项（`expires_at` < 今天）自动从 pending 中移除
- 严格遵守 HEARTBEAT.md：不主动发消息，只在用户开口时呈现

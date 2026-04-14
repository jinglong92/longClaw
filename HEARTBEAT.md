# HEARTBEAT.md

## Silent Heartbeat Policy

Heartbeat polling is an internal maintenance action, not a user-facing interaction.

Default behavior: **silence**.

---

## Core Rule

When heartbeat polling is triggered:

- Do **not** send any proactive outbound message to WeChat, email, SMS, Slack, or any other user-facing channel.
- Do **not** send placeholder texts such as `HEARTBEAT_OK`, `心跳正常`, `all good`, `still alive`, or any equivalent status ping.
- Do **not** acknowledge to the user that heartbeat polling occurred.
- If there is **no critical emergency**, produce **no outbound user-facing message**.

---

## Allowed Internal Actions

Heartbeat may still perform internal work, including:
- checking inbox / calendar / notifications
- reading or updating memory files
- reviewing workspace files
- recording internal logs or state
- preparing a future recommendation internally

These actions must remain silent unless a critical emergency exists.

---

## Proactive Heartbeat Agent

longClaw 扩展：在静默策略基础上增加"发现 → 准备 → 等用户开口时呈现"机制。

### 运行方式

**巡检**（cron 驱动，Mac mini M4 后台）：
- 每天 08:30 和 18:00 自动触发
- spawn `heartbeat-agent` 子代理执行只读巡检
- 结果写入 `memory/heartbeat-state.json`
- 全程静默，不发任何消息

**呈现**（SessionStart hook 驱动）：
- 每次用户开启新 session 时，hook 检查 `heartbeat-state.json`
- 有 P0/P1 未展示事项 → 在本轮回复开头简短呈现
- 呈现后标记为 `shown: true`，不重复提醒

### 巡检优先级

| 级别 | 内容 | 是否呈现给用户 |
|------|------|--------------|
| P0 | 今日/明日截止（面试/deadline） | ✅ 开口即提醒 |
| P1 | 近7天跟进事项（投递无回复等） | ✅ 开口即提醒 |
| P2 | 系统健康（日志缺失/压缩异常） | ❌ 只写日志 |

### 状态文件

`memory/heartbeat-state.json` — 巡检结果，SessionStart hook 读取

### 安装 cron

```bash
bash setup_heartbeat_cron.sh
```

---

## What Counts as a Critical Emergency

A user-facing alert is allowed **only** if immediate human action is required to prevent one of the following:

1. Security incident
2. Irreversible destructive failure
3. Production outage requiring human intervention
4. High-risk financial / operational failure
5. Safety-critical issue

If the issue is recoverable, transient, low-confidence, retryable, or can be handled automatically, it is **not** a critical emergency.

---

## Non-Emergencies (Must Stay Silent)

The following are **not** reasons to send a message:

- heartbeat succeeded normally
- no new events were found
- temporary timeout or retryable API failure
- one source failed but alternatives still exist
- minor warning or uncertainty
- “just keeping the user informed”
- “it has been a while since the last message”
- “something interesting was found”
- routine background polling result

All of the above must produce **no outbound message**.

---

## Output Contract

### If no critical emergency
- perform internal checks if needed
- optionally update internal files/logs
- send **nothing**
- return **empty / no-op / no outbound user-facing message**

### If critical emergency exists
Send exactly **one concise alert**, containing:
- what happened
- why it is critical
- what immediate action is required

---

## Enforcement Rule

If there is any ambiguity, choose **silence**.

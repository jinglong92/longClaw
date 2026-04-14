# longClaw Subagent & Harness 改造学习文档

> 版本：2026-04-14
> 对应 commits：77b0121 / a1982c9 / 6e328b6

---

## 一、为什么要做这些改造

### 原来的问题

longClaw 原来的架构是**角色（Specialist）模式**：

```
用户请求 → CTRL 路由 → 专职角色（JOB/BRO/SEARCH...）→ 回复
```

这个模式有三个天花板：

1. **被动响应**：角色只能等用户开口，没有主动发现能力
2. **串行执行**：SEARCH 角色每次只能搜一个来源，无法并发
3. **无状态陪伴**：BRO/SIS 每次对话都从零开始，不记得上次说了什么

Subagent 解决的是**主动性**和**并发性**两个问题。

---

## 二、核心概念：Subagent vs 角色

| 维度   | 角色（Specialist）  | Subagent              |
| ---- | --------------- | --------------------- |
| 触发方式 | 用户开口 → CTRL 路由  | CTRL 主动 spawn         |
| 执行方式 | 串行，在主 context 里 | 独立 context window，可并发 |
| 工具权限 | 继承主 session     | 独立配置，可严格限制            |
| 生命周期 | 跟随对话            | 任务完成即退出               |
| 典型用途 | 推理、建议、分析        | 搜索、读文件、巡检             |

**关键理解**：Subagent 是"派出去干活的工人"，角色是"坐在桌前思考的顾问"。两者互补，不是替代关系。

---

## 三、AI 搜索：并发 SearchAgent

### 设计思路

传统 SEARCH 角色的问题：

```
用户："帮我调研 Agent+OR 进展"
→ SEARCH 搜来源A（等待）
→ SEARCH 搜来源B（等待）
→ SEARCH 搜来源C（等待）
→ 汇总（总耗时 = A + B + C）
```

并发 SearchAgent 的方案：

```
用户："帮我深度调研 Agent+OR 进展"
→ deep-research skill 拆解问题
→ 同时 spawn 3 个 search-agent
   ├── agent-A 搜 arXiv（独立运行）
   ├── agent-B 搜 GitHub（独立运行）
   └── agent-C 搜招聘动态（独立运行）
→ 三路并发，总耗时 ≈ max(A, B, C)
→ CTRL 做 RRF 融合，输出综合报告
```

### 架构细节

**search-agent 的设计原则**：

1. **最小权限**：只有 `WebFetch`、`WebSearch`、`Read`、`Grep`，不能写文件
2. **单一职责**：每个 agent 只执行一个搜索任务，不做综合分析
3. **结构化输出**：返回 `URL + 逐字摘录 + 相关性分数`，不是自然语言总结
4. **轻量模型**：用 Haiku，成本低，速度快

**为什么用结构化输出而不是总结**：

如果每个 agent 都输出自然语言总结，CTRL 在汇总时会面对"总结的总结"，信息损耗大。结构化的 `URL + verbatim snippet + score` 让 CTRL 能做真正的 RRF（Reciprocal Rank Fusion）融合：

```python
# RRF 核心思想（伪代码）
for doc in all_results:
    rrf_score += 1 / (k + rank_in_agent_A)
    rrf_score += 1 / (k + rank_in_agent_B)
    rrf_score += 1 / (k + rank_in_agent_C)
# 跨 agent 都排名靠前的文档得分最高
```

**deep-research skill 的编排逻辑**：

```
Step 1：问题拆解
  → 把"调研 X"拆成 2-3 个独立维度
  → 原则：每个维度可以独立搜索，不依赖其他维度的结果

Step 2：并发 spawn
  → Agent(search-agent): 任务A
  → Agent(search-agent): 任务B
  → Agent(search-agent): 任务C

Step 3：RRF 融合
  → 去重（相同 URL 只保留一条）
  → 相关性排序
  → 冲突标注（不同来源有矛盾时显式标注）

Step 4：输出综合报告
  → 按维度组织，每条信息标注 [F]确定 / [I]推断
  → 来源列表 + 时效说明
```

### 文件位置

```
.claude/agents/search-agent.md          ← subagent 定义（OpenClaw 自动发现）
skills/search/deep-research/SKILL.md    ← 编排 skill
```

---

## 四、AI 陪伴：MemoryAgent 注入

### 设计思路

BRO/SIS 的核心问题：**无状态**。每次对话都像第一次见面。

MemoryAgent 解决的是"让 BRO/SIS 在回复前先'想起'你最近的状态"：

```
用户发消息（情绪信号）
    ↓
CTRL 路由到 BRO
    ↓
后台 spawn memory-agent（不打断主流程）
    ↓
memory-agent 读取近 3 天日志 + MEMORY.md[BRO/SIS]
    ↓
提取：近期情绪 / 上次话题 / 持续关注点
    ↓
注入给 BRO：
  "[背景] 近期情绪: 压力大 | 上次话题: Shopee面试 | 持续关注: 求职进展"
    ↓
BRO 基于这个背景回复
  "上次聊到 Shopee 面试，最近还在等消息吗？..."
```

### 架构细节

**为什么是"后台 spawn"而不是"先查后答"**：

如果是串行（先查记忆，再回复），用户会感受到延迟。后台 spawn 让 memory-agent 和主流程并发：

```
用户发消息
    ├── 主流程：CTRL 开始思考路由
    └── 后台：memory-agent 开始读文件

memory-agent 完成（通常比 CTRL 思考快）
    ↓
注入上下文
    ↓
BRO 回复时已经有背景
```

**memory-agent 的设计原则**：

1. **只读**：绝对不写文件，防止陪伴场景污染记忆
2. **提取而非复述**：不把原始日志给 BRO，而是提炼"情绪状态、话题、关注点"
3. **失败静默**：超时或读取失败时直接跳过，BRO 正常回复，不报错
4. **隐私保护**：不向用户暴露原始日志内容

**记忆注入的信息层次**：

```
Layer 1（最近）：memory/YYYY-MM-DD.md 近3天
  → 情绪信号词（压力/兴奋/疲惫/...）
  → 话题关键词

Layer 2（中期）：MEMORY.md [BRO/SIS] 块
  → 长期情绪模式
  → 持续关注的事项

Layer 3（跨域，可选）：MEMORY.md [JOB] 块
  → 求职进展（BRO 经常需要知道这个背景）
```

### 文件位置

```
.claude/agents/memory-agent.md                    ← subagent 定义
skills/companion/memory-companion/SKILL.md         ← 编排 skill
```

---

## 五、Proactive Heartbeat：主动发现机制

### 设计思路

这是三个改造里最复杂的，涉及三个独立机制的协作：

```
机制1：cron 定时触发（Mac mini M4 后台）
机制2：heartbeat-agent 静默巡检（写入状态文件）
机制3：SessionStart hook 呈现（用户开口时读取）
```

**为什么不直接主动推消息**：

HEARTBEAT.md 的核心约束是"不主动打断用户"。这是合理的——如果 AI 随时给你发消息，会制造焦虑感而不是帮助感。

正确的设计是：**AI 主动发现，但等你开口时才告诉你**。这就像一个好助理——他会提前准备好信息，但不会在你开会时突然敲门。

### 三个机制的协作流程

```
每天 08:30 / 18:00
    ↓
cron 触发 openclaw --print "heartbeat巡检"
    ↓
spawn heartbeat-agent（Haiku，只读+写state）
    ↓
heartbeat-agent 巡检：
  P0：今日/明日截止（面试、deadline）
  P1：近7天跟进（投递无回复>5天）
  P2：系统健康（日志缺失、压缩异常）
    ↓
写入 memory/heartbeat-state.json：
  {
    "has_pending": true,
    "pending_items": [
      {"priority": "P0", "content": "今天15:00 Shopee面试", "shown": false}
    ]
  }
    ↓
静默退出（不发任何消息）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

用户下次开口（可能是几小时后）
    ↓
SessionStart hook 触发
    ↓
读取 heartbeat-state.json
    ↓
有 P0/P1 未展示项？
    ├── 是 → 在本轮回复开头展示：
    │         "💡 [心跳提醒]
    │          • [P0] 今天15:00 Shopee面试"
    └── 否 → 正常回复，不展示
    ↓
标记 shown: true，下次不重复
```

### heartbeat-state.json 的设计

这个文件是三个机制的"共享黑板"：

```json
{
  "last_check": "2026-04-14T08:30:00Z",
  "has_pending": true,
  "pending_items": [
    {
      "priority": "P0",
      "type": "deadline",
      "content": "今天15:00 Shopee面试",
      "action": "提前30分钟准备",
      "expires_at": "2026-04-14",
      "shown": false,
      "shown_count": 0
    }
  ],
  "check_summary": "检查了3天日志，发现1个P0事项"
}
```

**关键字段设计**：
- `shown`：防止重复提醒
- `shown_count`：最多提醒 2 次（防止骚扰）
- `expires_at`：过期自动移除（防止陈旧信息积累）

### 文件位置

```
.claude/agents/heartbeat-agent.md              ← subagent 定义
skills/meta/proactive-heartbeat/SKILL.md       ← 编排 skill
setup_heartbeat_cron.sh                        ← 一键安装 cron
memory/heartbeat-state.json                    ← 共享黑板（运行时生成）
```

---

## 六、P0 Harness 改造

### 什么是 Harness Engineering

Harness（线束）的核心思想：**把规则放在基础设施层执行，而不是靠 LLM 自觉遵守**。

```
❌ 靠 LLM 自觉：在 AGENTS.md 写"请用 trash 代替 rm"
                 → LLM 可能忘记，可能忽略

✅ Harness 层执行：PreToolUse hook 拦截 rm，自动改写为 trash
                   → 无论 LLM 说什么，实际执行的都是 trash
```

### PostCompact Hook

**问题**：OpenClaw 原生压缩后，只有项目根目录的 `CLAUDE.md` 会自动重注入。`CTRL_PROTOCOLS.md` 和 `DEV_LOG.md` 压缩后会丢失，CTRL 可能"忘记"检索协议和 DEV LOG 格式规则。

**解决方案**：PostCompact hook 在压缩完成后立即把这两个文件追加到 `$CLAUDE_ENV_FILE`：

```json
"PostCompact": [{
  "matcher": "auto",
  "hooks": [{"type": "command",
    "command": "cat CTRL_PROTOCOLS.md DEV_LOG.md >> \"$CLAUDE_ENV_FILE\""}]
}]
```

`$CLAUDE_ENV_FILE` 是 OpenClaw 提供的环境注入文件，写入的内容会被注入到下一轮的 context 里。

**压缩后的保留/丢失规则**（OpenClaw 原生行为）：

| 内容 | 压缩后状态 |
|------|-----------|
| 项目根目录 CLAUDE.md | ✅ 自动重注入 |
| MEMORY.md（前200行） | ✅ 自动重注入 |
| 已调用的 SKILL.md | ✅ 重注入（每个≤5K token） |
| CTRL_PROTOCOLS.md / DEV_LOG.md | ❌ 丢失 → PostCompact hook 补救 |
| 子目录 CLAUDE.md | ❌ 丢失，重新进入目录时才重读 |
| 对话历史 | ❌ 压缩为结构化摘要 |

### FileChanged Hook

**问题**：修改了 `AGENTS.md` 等配置文件后，当前 session 不知道文件变了，还在用旧规则。

**解决方案**：监听配置文件变更，通知 CTRL 重读：

```json
"FileChanged": [{
  "matcher": "AGENTS.md|MULTI_AGENTS.md|CTRL_PROTOCOLS.md|DEV_LOG.md",
  "hooks": [{"type": "command",
    "command": "echo '[Config changed: ...] Re-read before next response.'"}]
}]
```

### PreToolUse Hook（updatedInput）

**问题**：LLM 可能执行 `rm file.txt`，即使规则里写了"trash > rm"，LLM 也可能忘记。

**解决方案**：在 harness 层拦截并改写工具输入：

```
LLM 发出: rm file.txt
    ↓
PreToolUse hook 检测到 rm 开头
    ↓
返回 updatedInput: { "command": "trash file.txt" }
    ↓
实际执行: trash file.txt（LLM 不知道被改写了）
```

`updatedInput` 是 OpenClaw hook 的特殊返回字段，可以在工具执行前修改工具的输入参数。

### SessionStart Hook（Heartbeat 呈现）

```json
"SessionStart": [{
  "hooks": [{"type": "command",
    "command": "检查 heartbeat-state.json，有 P0/P1 时提示 CTRL 呈现"}]
}]
```

每次 session 开始时自动触发，是 Heartbeat 呈现机制的入口。

---

## 七、整体架构图

```
用户开口
    │
    ▼
SessionStart hook
  → 读 heartbeat-state.json
  → 有 P0/P1 → 提示 CTRL 在本轮回复开头呈现
    │
    ▼
CTRL 路由决策
    │
    ├── 路由到 BRO/SIS
    │     → spawn memory-agent（后台并发）
    │     → 注入近期记忆上下文
    │     → BRO/SIS 带记忆回复
    │
    ├── 路由到 SEARCH（复杂调研）
    │     → deep-research skill
    │     → spawn search-agent × 2-3（并发）
    │     → RRF 融合
    │     → 综合报告
    │
    └── 其他路由 → 正常专职回复
    │
    ▼
工具调用
  → PreToolUse hook: rm → trash
  → PostToolUse: 结果注入 DEV LOG 🛠️ 工具字段
    │
    ▼
回复输出
    │
    ▼
压缩检查（如触发）
  → PostCompact hook: 重注入 CTRL_PROTOCOLS.md + DEV_LOG.md

━━━━━━━━━ 后台（cron，与对话无关）━━━━━━━━━

每天 08:30 / 18:00
  → cron 触发 openclaw --print "heartbeat巡检"
  → spawn heartbeat-agent
  → 巡检 P0/P1/P2 事项
  → 写入 heartbeat-state.json
  → 静默退出
```

---

## 八、文件清单

```
.claude/
├── settings.json                          ← hooks 配置（PostCompact/FileChanged/PreToolUse/SessionStart）
└── agents/
    ├── search-agent.md                    ← 并发搜索子代理（Haiku，WebFetch only）
    ├── memory-agent.md                    ← 记忆检索子代理（Haiku，只读）
    └── heartbeat-agent.md                 ← 心跳巡检子代理（Haiku，只读+写state）

skills/
├── search/
│   └── deep-research/SKILL.md             ← AI搜索编排 skill
├── companion/
│   └── memory-companion/SKILL.md          ← AI陪伴记忆注入 skill
└── meta/
    └── proactive-heartbeat/SKILL.md       ← 主动心跳编排 skill

setup_heartbeat_cron.sh                    ← 一键安装 cron job（在 Mac mini M4 上运行一次）
HEARTBEAT.md                               ← 心跳策略（已扩展 Proactive Agent 章节）
```

---

## 九、在 Mac mini M4 上激活

### settings.json 和 agents/ 自动生效

`.claude/settings.json` 和 `.claude/agents/` 放在 workspace 根目录，OpenClaw 启动时自动加载，无需额外操作。

### 安装 cron（需手动执行一次）

```bash
cd ~/longClaw   # 你的 workspace 目录
bash setup_heartbeat_cron.sh
```

验证：
```bash
crontab -l | grep longclaw
# 应看到两条：08:30 和 18:00
```

### 手动验证各模块

```bash
# 1. 验证 heartbeat 巡检
openclaw --print "heartbeat巡检：spawn heartbeat-agent，执行巡检并写入 memory/heartbeat-state.json"
cat memory/heartbeat-state.json

# 2. 验证 deep-research（在 OpenClaw 对话中）
"帮我深度调研最近 Agent+OR 融合的进展，多个来源"

# 3. 验证 memory-companion（在 OpenClaw 对话中）
"随便聊聊"  # 路由到 BRO，应该能看到 DEV LOG 里有 memory-agent 注入
```

---

## 十、设计原则总结

| 原则 | 体现 |
|------|------|
| **最小权限** | 每个 subagent 只有完成任务所需的最少工具 |
| **失败静默** | subagent 超时/失败时主流程正常继续，不报错打断 |
| **结构化输出** | subagent 返回结构化数据，不是自然语言总结，便于 CTRL 融合 |
| **harness 层执行** | 安全规则在 hook 层强制，不依赖 LLM 自觉 |
| **不主动打断** | Heartbeat 发现信息后等用户开口，不主动推送 |
| **轻量模型** | subagent 全部用 Haiku，降低成本和延迟 |

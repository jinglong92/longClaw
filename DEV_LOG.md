# DEV_LOG.md — DEV LOG 格式规范

> 本文件管：**DEV LOG 的字段、格式、示例、强制规则**。
> 它是展示协议，不是执行证据。
> 全局安全约束 → `AGENTS.md` | 专职定义 → `MULTI_AGENTS.md` | CTRL 协议 → `CTRL_PROTOCOLS.md`

---

## 字段顺序（9 个）

```
[DEV LOG]
🔀 路由     <routing decision>
🧩 Skill    <skill match result>
🛠️ 工具     <tool call results — PostToolUse>
🧠 Memory   <domain injected + token savings>
📂 Session  <round + compression state>
🔍 检索     <retrieval scope + recall>
⚖️ 置信度   <confidence + basis + conflict>
🤝 A2A      <cross-agent communication>
🏷️ 实体     <new/updated entities>
```

---

## 字段规范

### 🔀 路由
```
🔀 路由 <ROLE> | 触发: "<keyword>" | 模式: <normal debug|blocked/fix-now> / <单专职|双并行>
```

### 🧩 Skill
```
🧩 Skill 命中: <name> | trigger=<reason> | loaded=yes | step=<N/total|completed>
🧩 Skill 命中: none | 原因: <why>
```
- 执行期间每步更新 step 字段
- 执行完写 `completed | output=<摘要>`

### 🛠️ 工具（PostToolUse 注入）
```
🛠️ 工具 <tool>(<target>) → <result_summary> | status=<ok|failed|blocked>
```
- 多次工具调用各占一行
- `status=failed`：附失败原因
- `status=blocked`：附原因（missing_tool / deny_rule / need_auth）
- 无工具调用：`🛠️ 工具 无`
- **LLM fallback 命中时必须明确标注**：
  ```
  🛠️ 工具 llm_fallback → [兜底模型] primary=openai:gpt-5.4 不可用（rate_limit），已切换至 ollama:gemma4:e2b | status=ok(degraded)
  ```
  结果 JSON 里 `fallback_triggered=true` 时，此行不得省略

### 🧠 Memory
```
🧠 Memory <domains> | ~<N> tokens | 节省 <X>%
```
- 若 MEMORY.md 未加载（SEARCH 域等），写 `🧠 Memory (SYSTEM) only`
- 若 token 数未知，写 `~ephemeral`（不写 unavailable）

### 📂 Session
```
📂 Session 第 <N> 轮 | recent_turns=<n/8> | <未触发压缩|Layer 2 已触发>
```
- `第 <N> 轮` 指本次 session 内的轮次（ephemeral，不跨 session 累积）
- 若 session-state.json 不存在或未写入，写 `ephemeral session`（不写 unavailable）
- 跨 session 统计由 heartbeat-agent 负责，不在此字段体现

### 🔍 检索
```
🔍 检索 scope=<DOMAIN> | level=<同域近期|同域归档|跨域> | 召回 <N> 条 | top=[<scores>]
```
- 若未触发检索工具（Level 1 context 已足够），写 `🔍 检索 scope=context | level=L1 | 无需工具`
- 若分数未知，写 `top=ephemeral`（不写 unavailable）

### ⚖️ 置信度
```
⚖️ 置信度 <X.XX> [依据: <data|inference|experience>] | 冲突: <无|描述>
```

### 🤝 A2A
```
🤝 A2A <FROM> → <TO> <task> | confidence=<X.XX> | needs_ctrl=<true|false>
🤝 A2A 无
```

### 🏷️ 实体
```
🏷️ 实体 检测到新实体: <entity>=<value>（<date>）→ 已更新 [<DOMAIN>]
```

---

## 输出分档

| 档位 | 使用场景 |
|------|---------|
| `normal debug` | 普通执行、检索、审查、改写、读回、非阻塞推进 |
| `blocked/fix-now` | 卡住、证据缺失、用户质疑"是不是没执行"、需要立即补救 |

---

## 示例 A：normal debug

```
[DEV LOG]
🔀 路由 ENGINEER | 触发: "改配置" | 模式: normal debug / 单专职
🧩 Skill 命中: agent-review | trigger=workspace 配置审查 | loaded=yes | step=completed
🛠️ 工具 Edit(AGENTS.md) → 插入 Immutable Rules 节，+18行 | status=ok
        Bash(git commit) → hash=f951b9a | status=ok
🧠 Memory (SYSTEM)+[ENGINEER] | ~210 tokens | 节省 72%
📂 Session 第 15 轮 | recent_turns=7/8 | 未触发压缩
🔍 检索 scope=ENGINEER | level=同域近期 | 召回 2 条 | top=[0.91, 0.78]
⚖️ 置信度 0.99 [依据: 文件改写+原文读回] | 冲突: 无
🤝 A2A 无
🏷️ 实体 检测到新实体: AGENTS_version=v2（2026-04-14）→ 已更新 [ENGINEER]
```

## 示例 B：blocked/fix-now

```
[DEV LOG]
🔀 路由 SEARCH | 触发: "查最新论文" | 模式: blocked/fix-now / 单专职
🧩 Skill 命中: public-evidence-fetch | trigger=公开网页证据抓取 | loaded=yes | step=2/4
🛠️ 工具 WebFetch(arxiv.org) → 403 Forbidden | status=blocked(missing_tool)
🧠 Memory (SYSTEM) | ~80 tokens
📂 Session 第 8 轮 | recent_turns=8/8 | 未触发压缩
🔍 检索 scope=LEARN | level=同域近期 | 召回 0 条
⚖️ 置信度 unavailable [依据: 工具不可用] | 冲突: 无
🤝 A2A 无
🏷️ 实体 无
```

---

## 最低合格线

- **强制项**（不得省略）：`🔀 路由`、`🧩 Skill`、`🛠️ 工具`、`📂 Session`、`⚖️ 置信度`
- 至少输出 9 个字段中的 6 个
- 有文件改动或校验时，`🔍 检索` 不得省略
- 无 A2A 时必须写 `🤝 A2A 无`
- 无工具调用时必须写 `🛠️ 工具 无`

---

## 强制输出规则（Immutable，来自 AGENTS.md）

DEV LOG 每轮必须输出，以下情况下不得省略或缩减：

1. Skill 执行期间（每一轮）
2. 复杂任务执行中（涉及多步/文件修改/工具调用）
3. 用户质疑"是不是没执行"或"为什么没做"
4. 发生阻塞、证据缺失、需要补救

**禁止**：
- 以"输出太长"为由省略
- 以"Skill 已执行完"为由省略
- 只输出 Routing 行跳过其他字段
- 把计划、意图、猜测写入字段（必须是 runtime-produced 或 tool-returned 值）
- 字段无真实来源时，写 `unavailable`，不得编造

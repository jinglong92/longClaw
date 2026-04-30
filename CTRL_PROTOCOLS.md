# CTRL_PROTOCOLS.md — CTRL 运行协议

> 本文件管：**Skill 加载、压缩、检索、Skill 提议**。
> 专职代理定义 & 路由 → `MULTI_AGENTS.md`
> DEV LOG 格式 → `DEV_LOG.md`
> 全局安全约束 → `AGENTS.md`

---

## Skill 加载（OpenClaw 原生执行）

OpenClaw 运行时原生支持 Progressive Disclosure：会话启动时扫描 `skills/` 目录建立 index，命中触发条件时加载全文，执行完退出 context。longClaw 在此基础上扩展了 `requires` 依赖检查和强制触发规则。

### Skill Index（当前 15 个）

完整清单移至 `skills/INDEX.md`。本节只保留运行协议，避免索引与协议双份维护导致漂移。

### 依赖检查（命中前必须通过）

`requires` 字段声明所需工具能力，不满足时返回 `blocked: missing_tool(<tool_name>)`，不得空转。

```
requires: []                      → 直接执行
requires: ["web_fetch"]           → 检查 WebFetch 可用性
requires: ["file_write"]          → 检查文件写入可用性
requires: ["file_write", "shell_exec"] → 两项都需满足
```

### 冲突优先级

`skill-safety-audit`（最高）> `research-execution-protocol` > `research-build`（最低）

### 命中即触发（硬规则）

匹配触发条件且依赖检查通过 → 当轮立即执行 Step 1，不得推迟到下轮。

- 未命中：DEV LOG 写 `🧩 Skill 命中: none | 原因: <why>`
- 执行完：SKILL.md 退出 context，但 DEV LOG 每轮继续输出

### Skill vs 角色

- 角色定义（JOB/WORK/LEARN 等）在 `MULTI_AGENTS.md`
- Skill 是具体可复用工作流，同一角色可有多个 skill

### 优先级

`AGENTS.md`（安全）> `SKILL.md`（工作流）> `MULTI_AGENTS.md`（路由）

---

## Context Compression（三层）

优先级：原生 compaction > Layer 1（Trim）> Layer 2（Summarize）。Layer 4（Archive）独立触发，不受前三层影响。

> **编号说明**：Layer 3 即原生 compaction（OpenClaw 运行时内置，不在 workspace 层实现），故 workspace 层编号从 Layer 1 跳到 Layer 2 再到 Layer 4，无 Layer 3。

### Session 形态说明（影响 Layer 2 触发逻辑）

longClaw 存在两种 session 形态，压缩策略不同：

| 形态 | 描述 | Layer 2 触发 |
|------|------|-------------|
| **Persistent**（持久型）| Claude Code / OpenClaw 桌面端，单 session 多轮 | 工具事件数 > 30，或本 session 内 trim_event 累计 > 10 |
| **Ephemeral**（短暂型）| 微信 bot / Telegram / 每条消息新 session | **不触发 Layer 2**（单轮无法积累），依赖 Layer 4 Archive 跨 session 归档 |

session 形态由 `memory/session-state.json` 的 `session_type` 字段标识（`persistent` / `ephemeral`，默认 `persistent`）。

> 兼容说明（渠道会话）：
> 在部分 openclaw-weixin / 第三方渠道会话中，UserPromptSubmit hook 可能未触发，
> 导致 `tool_events` / `trim_events` 注入缺失。此时 DEV LOG 按 `DEV_LOG.md` 降级为
> `tool_events=0 | trim_events=0 | source=hook-offline`，不要写 `ephemeral`。

### Layer 1：Trim（工具输出实时截断）（借鉴 Claude Code Tool Result Budgeting）

**触发**：任意一条工具输出 > 500 字符，当轮立即执行，无需等待轮数累积。

**执行**：
- 保留工具输出前 500 字符
- 追加截断尾注：`[截断：原始输出 N 字符，已保留前 500 字符。如需完整内容请说"展开上一条工具输出"。]`
- 静默执行，不写入 session-state.json，不计入 compression_count
- **执行链**：由 PostToolUse hook 触发（`scripts/hooks/hook_dispatcher_post_tool_use.sh`），sidecar 写 `trim_event` note 到 SQLite

**设计理由**：工具输出截断不依赖轮数，任何 session 形态下均有效。

### Layer 2：Summarize（轻量摘要）（token 压力驱动，仅 persistent session）

**触发条件**（满足任一，且原生 compaction 未触发，且 `session_type=persistent`）：
- 本 session 内 **工具事件数 > 30**（由 `runtime_sidecar/state/readers.py` 的 `count_session_tool_events()` 查询）
- 本 session 内 **trim_event 累计 > 10**（Layer 1 已截断 10 次，说明上下文压力已高）

**不触发条件**：
- `session_type=ephemeral`（每条消息新 session，工具事件无法跨轮积累）
- 原生 compaction 已触发

**执行**：
- 生成压缩摘要块替换中间历史，保留关键结论
- 保护：system prompt + 前 3 条 + 后 8 条不摘要
- 摘要格式：`目标 / 进展 / 决策 / 下一步 / 关键实体（字段名：值（日期））`
- 写入 session-state.json：`compression_count += 1`，`last_compression_at = <ISO>`
- DEV LOG 显示：压缩原因 / 累计次数 / 级别
- 失败时退化为最小裁剪，不得声称"已完成压缩"

### Layer 4：Archive（话题归档）（话题边界驱动，主动）

**触发**（满足任一）：
- 用户说"新话题" / "换个话题" / "搞定了" / "好了就这样"
- CTRL 判断当前话题已有明确结论
- 用户连续 2 轮未追问上一话题

**执行**：
1. 提炼 key_conclusions（≤5条，每条一句话）
2. 提取关键实体（公司名/面试状态/学习内容等）
3. 写入 MEMORY.md 对应域（格式：`字段名：值（YYYY-MM-DD）`）
4. 告知用户："已将[话题]的结论保存到长期记忆"

---

## Memory Retrieval（4 级作用域）

**核心原则**：先决定搜哪里，再决定怎么搜。

```
Level 1：当前 session / recent turns
  → Codex 上下文窗口天然覆盖，无需调用工具
  → Level 1 不足时才进入 Level 2

Level 2：同域 7 天内
  → memory/YYYY-MM-DD.md（过去 7 天）domain 匹配条目
  → MEMORY.md 对应 [DOMAIN] 块

Level 3：同域全量
  → memory/YYYY-MM-DD.md 全量 domain 匹配条目
  → tools/artifacts/memory_entries.jsonl domain 匹配条目

Level 4：跨域兜底
  → 仅当 Level 2+3 结果数 < 2 时触发
  → 结果标注 [跨域]
```

**扩展到下一级的条件**（满足任一）：
- 结果数 < 2
- top1 分数 < 0.3
- query 中的关键实体在结果里未出现

**打分权重**：同域 +0.3 / 跨域 -0.2 / 7天内 +0.2 / 30天内 +0.1

**Query Rewrite**（先改写再检索）：
1. 原始 query
2. 原始 + domain hints（JOB 域自动加 "job career offer interview"）
3. 实体提取版（公司名/技术词/项目名）

**工具调用**：
```bash
python3 tools/memory_search.py --query "<改写后query>" --domain <ROLE>
```

**memory_search 失败自动 fallback（强制）**：
- 若首选 `memory_search` 返回 `disabled=true`、`unavailable=true`、provider/embedding timeout、quota error、或其他工具级错误，不得表述为“没搜到”。
- 必须立即切换到降级链路：
  1. `memory_get` 读取 `MEMORY.md` 对应域块
  2. `memory_get` 读取今天/昨天 `memory/YYYY-MM-DD.md`
  3. 如仍不足，再做直接文件检索（workspace 内 `read` / `rg`）
- 降级后回复必须明确区分：
  - `检索成功但 0 条`
  - `检索工具不可用，已 fallback`
- DEV LOG 必须显式写：`fallback engaged`，并说明使用了哪条降级路径。
- 若本机 `tools/memory_search.py` 可用，可将其作为只读降级检索路径；若其 hybrid embedding 不可用，则自动退回 fts-only，不得再把 embedding 失败升级成整条 recall 失败。

DEV LOG 显示：检索级别 / query 变体 / 召回数 / 是否触发跨域 / 是否 fallback

---

## Session Recap（结构化会话压缩层）

> recap = 会话压缩与 agent handoff 的中间状态，不是日志层、审计层或 memory 本体。

### 四层结构（层级职责严格不可互换）

```
raw_events 表 / raw-events.jsonl  →  工具调用事实源（不可篡改）
session-state.json                →  当前 session 结构化状态
memory/recap.json                 →  模型压缩上下文（lossy，给模型看）
MEMORY.md                         →  长期稳定记忆（跨 session）
```

**DEV_LOG.md** 是人类研发日志，可引用 recap，但不被 recap 替代。

### 硬约束（不可违反）

1. `authoritative` 字段**永远为 `false`**：recap 不是事实源，不得用于审计
2. **工具调用验证必须查 `raw_events` 表**，不得以 recap 内容代替（如 `tool_events=0` 问题必须看原始 hook log）
3. **recap 不得直接写入 `MEMORY.md`**：路径为 `recap → memory candidate → 人工/CTRL 确认 → MEMORY.md`
4. 假设不得写成已确认事实，必须放入 `uncertainty` 字段
5. 失败路径必须写入 `failed_attempts`，不得只保留成功路径

### 触发时机（满足任一）

- Layer 2 Summarize 触发时（自动，同步生成）
- 原生 compaction 触发前（pre_compaction）
- agent handoff 前（handoff）
- 用户发送 `/recap`（manual）

不建议每轮生成，过高频率造成摘要漂移且消耗 token。

### recap.json schema（必填字段）

```json
{
  "type": "session_recap",
  "version": "0.1",
  "authoritative": false,
  "trigger": "layer2 | pre_compaction | handoff | manual",
  "created_at": "<ISO 8601>",
  "source_turn_range": [<start>, <end>],
  "objective": "<当前会话目标>",
  "confirmed_facts": ["<已确认事实>"],
  "actions_taken": [{"type": "<code_change|config|analysis>", "target": "<文件或模块>", "result": "<结果>"}],
  "files_touched": ["<路径>"],
  "open_issues": ["<未解决问题>"],
  "next_steps": ["<下一步行动>"],
  "uncertainty": ["<假设或不确定项>"],
  "failed_attempts": [{"attempt": "<尝试>", "result": "<结果>", "remaining_problem": "<遗留问题>"}]
}
```

写入位置：`memory/recap.json`（覆盖，只保留最新一份）；同时调用 `writers.insert_session_recap()` 写入 SQLite。

### debug 模式下降权

排查 hook、tool_events、session 状态等问题时，recap 不可作为参考依据：

- 必须查 `raw_events` 表或 `memory/sidecar-hooks.log`
- recap 中如有"工具调用正常"等表述，视为无效，不得引用
- DEV LOG 中如存在 `source=hook-offline`，recap 的 tool 相关字段均不可信

### agent handoff 协议

CTRL 向子 agent 传递任务时，只传结构化 recap，不传完整对话历史：

```yaml
objective: <当前目标>
confirmed_facts: [<已确认事实>]
files_touched: [<相关文件>]
open_issues: [<未解决问题>]
next_steps: [<下一步>]
risk_flags: [<风险与不确定性>]
```

---

## Proactive Skill Creation（技能提议系统）

检测到可复用工作流时，在回复末尾附加提议（不打断正文）。必须用户确认后才创建文件。

**触发条件**（满足任一）：
1. 复杂任务完成（≥3步 + 逻辑可复用 + skills/ 中无覆盖该工作流的 skill）
2. 用户说"以后都这样处理" / "记住这个流程" / "做成一个技能"
3. 同类 workflow 在近 7 天内出现 ≥ 2 次

**提议格式**：
```
---
💡 [技能发现] 检测到可复用工作流：<工作流名称>
建议路径：skills/<role>-<workflow-name>/SKILL.md
用途：<一句话描述>
是否创建？回复"是"自动生成，回复"否"忽略此提议。
---
```

**创建约束**：
- 不自动创建，必须用户确认
- 不 patch 已有 skill，只创建新文件
- 新 skill 下次 session 才生效
- 不得包含敏感信息（密码/API key/个人信息）
- 不得覆盖 AGENTS.md 安全规则

---

## 会话模型模式（轻量）

`memory/session-state.json` 可含 `model_mode`（由 `tools/model_mode.py` 或 CTRL 写入），仅作**会话内观测/提示**，不驱动仓库内任何 LLM 代理或本地兜底。

- `auto`（默认）：无特殊约束
- `primary`：提示「主模型优先、不依赖自动降级叙事」；**不改变** OpenClaw / Codex 实际 HTTP 上游

切换示例：

```bash
python3 tools/model_mode.py set primary
python3 tools/model_mode.py set auto
python3 tools/model_mode.py get
```

历史上若存在 `model_mode=fallback`，`model_mode.py get` 会将其**归一为 `primary`** 并写回文件。换模型、换 provider 请在 **OpenClaw 客户端 / `~/.openclaw/openclaw.json`** 配置。

---

## DEV LOG 渲染前置校验

DEV LOG 的字段模板、强制输出场景、`dev_mode_effective` 判定、激活回合规则，均以 `DEV_LOG.md` 为唯一权威来源。本文件只保留执行侧约束，避免双份规则漂移。

需要输出 DEV LOG 时，CTRL 仅做以下校验：

1. `format_source = DEV_LOG.md`（未读取 `DEV_LOG.md` 不得渲染）
2. `value_source = runtime/tools/session-state.json/tool returns/current turn context`
3. 不得输出 `session_id:` / `round:` / `dev_mode:` 这类内置裸字段块，必须按 `DEV_LOG.md` 模板渲染
4. `📂 Session.ctx` / `compactions` / `queue` 必须来自本轮 `session_status()`；ctx 不可用时才回退到 `[ctx-preflight]` hook；其余字段不可用时一律写对应 `unavailable`，禁止沿用上一轮值
5. `🤖 模型.auth` / `🤖 模型.fallbacks` / `🤖 模型.effort` 必须取自本轮 `session_status()` banner（🔑 / 🔄 / Think 字段）；不可读各自写 `unavailable` / `none` / `unavailable`
6. `🧮 Tokens` 必须取自本轮 `session_status()` 的 🧮 Tokens / 🗄️ Cache 字段；session_status 不可用时整行写 `🧮 Tokens unavailable`，禁止估算
7. `⚙️ Execution.mode` / `runtime` / `think` / `elevated` 必须取自本轮 banner；不可读整行写 `⚙️ Execution unavailable`

若以上任一失败，先回退并重渲染，再发送回复。

## Session 状态管理

session_id 命名：`openclaw_{domain}_{YYYY-MM-DD}`（如 `openclaw_job_2026-04-14`）

`memory/session-state.json` 最小字段：

`session_id`, `round`, `dev_mode`, `routing_visibility`, `active_domain`, `current_topic`, `model_mode`, `last_retrieval_scope`, `last_retrieval_query_variants`, `pending_confirmation`, `read_only_web_authorized`, `authorized_scopes`, `compression_count`, `last_compression_at`, `updated_at`

写入时机：CTRL 草拟回复后、输出给用户前更新；不要在生成回复前读写导致循环依赖。

三层状态：
- Layer 1（短期）：recent_turns，工具事件数 > 30 或 trim_event > 10 时触发 Layer 2（仅 persistent session）
- Layer 2（中期）：summary + entities，LLM 摘要 + 关键实体
- Layer 3（长期）：key_conclusions，写入 MEMORY.md，跨 session 可检索

跨 session 检索：
- 专家级别：只在同类型 session 里检索（JOB 专家只搜 session_job_*）
- CTRL 级别：在所有 session 里检索

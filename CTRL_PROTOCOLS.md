# CTRL_PROTOCOLS.md — CTRL 运行协议

> 本文件管：**Skill 加载、压缩、检索、Skill 提议**。
> 专职代理定义 & 路由 → `MULTI_AGENTS.md`
> DEV LOG 格式 → `DEV_LOG.md`
> 全局安全约束 → `AGENTS.md`

---

## Skill 加载（OpenClaw 原生执行）

OpenClaw 运行时原生支持 Progressive Disclosure：会话启动时扫描 `skills/` 目录建立 index，命中触发条件时加载全文，执行完退出 context。longClaw 在此基础上扩展了 `requires` 依赖检查和强制触发规则。

### Skill Index（当前 15 个）

```
paper-deep-dive              | LEARN    | 论文深度解读
jd-analysis                  | JOB      | 分析岗位 JD，匹配度评级
agent-review                 | ENGINEER | workspace 配置审查
research-build               | ENGINEER | 需求→实现闭环
research-execution-protocol  | ENGINEER | 复杂排障/修 bug
fact-check-latest            | SEARCH   | 核查最新信息
public-evidence-fetch        | SEARCH   | 公开网页证据摘录
skill-safety-audit           | META     | 外部 skill 接入审计
session-compression-flow     | META     | 会话压缩归档
multi-agent-bootstrap        | META     | 多代理架构初始化
paperbanana                  | LEARN    | 学术论文配图自动生成（需本地安装）
deep-research                | SEARCH   | 并发多源深度调研（spawn SearchAgent×2-3）
code-agent                   | ENGINEER | Coding Agent 完整工作流（spawn repo-explorer→执行→验证）
memory-companion             | BRO/SIS  | 记忆增强陪伴（自动注入近期记忆，BRO/SIS路由时触发）
proactive-heartbeat          | META     | 主动心跳巡检（cron触发+SessionStart呈现）
```

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

在输出任何 DEV LOG 前，CTRL 必须先完成以下校验：

1. `format_source = DEV_LOG.md`
2. `value_source = runtime/tools/session-state.json/tool returns/current turn context`
3. 不得用 `session-state.json` 推导、替代、覆盖 `DEV_LOG.md` 的字段顺序、字段名称、展示格式
4. 若本轮尚未读取 `DEV_LOG.md`，不得输出 DEV LOG
5. 若候选输出命中 `session_id:`、`round:`、`dev_mode:` 这类内置裸字段块，而非 `DEV_LOG.md` 定义的模板字段，则视为格式错误，必须回退并重渲染

### Dev Mode 激活回合绑定（强制）

为避免与 `AGENTS.md` 的 session-state 写入时机冲突，DEV LOG 的展示判定必须使用：

`dev_mode_effective = (session-state.json.dev_mode == true) OR (current_turn_activation_intent == true)`

其中 `current_turn_activation_intent` 仅在本轮用户明确说出以下指令时成立：
- `开启 dev mode`
- `打开开发者模式`

激活回合（用户本轮刚说开启 dev mode）必须按以下顺序执行，不得等下一轮：
1. 立即将 `DEV_LOG.md` 视为唯一 `format_source`
2. 本轮回复必须直接输出一个真实的 `[DEV LOG]` 块
3. DEV LOG 字段值优先取 runtime / tool returns / current turn context；尚未持久化到 `session-state.json` 的字段按 `DEV_LOG.md` 规则写 `ephemeral` 或 `unavailable`
4. CTRL 草拟完回复后、发给用户前，再写入 `memory/session-state.json.dev_mode = true`

若第 1-4 步任一未满足，则不得口头确认"已开启 dev mode"；正确状态是 `blocked: dev_mode_activation_failed`

### Dev Mode 展示硬规则（强制）

若 `dev_mode_effective == true`，则本轮回复**必须**包含一个真实的 `[DEV LOG]` 块，不得省略，不得仅保留内部状态，不得因为“正文简洁”或“避免打扰”而跳过。

补充约束：
- `routing_visibility=devlog_only` 的含义是“路由与调试信息收纳进 DEV LOG”，**不是**“可以不显示 DEV LOG”。
- 当 `dev_mode_effective=true` 时，`[DEV LOG]` 是回复协议的一部分，而不是可选附录。
- 若本轮未能生成合格 DEV LOG，则整条回复视为未满足协议，必须先补齐 DEV LOG 再发送。
- 只有用户明确说出“关闭 dev mode / 关闭开发者模式”后，才允许停止在回复中显示 DEV LOG。

快速检查口令：

- 模板从哪里来？→ `DEV_LOG.md`
- 值从哪里来？→ runtime / tools / session-state
- 开启 dev mode 的当轮能不能等下轮再套模板？→ 不能
- 当前输出像不像 `DEV_LOG.md` 示例？→ 若否，禁止发送
- `dev_mode_effective=true` 时能不能不显示 DEV LOG？→ 不能

## Session 状态管理

session_id 命名：`openclaw_{domain}_{YYYY-MM-DD}`（如 `openclaw_job_2026-04-14`）

三层状态：
- Layer 1（短期）：recent_turns，工具事件数 > 30 或 trim_event > 10 时触发 Layer 2（仅 persistent session）
- Layer 2（中期）：summary + entities，LLM 摘要 + 关键实体
- Layer 3（长期）：key_conclusions，写入 MEMORY.md，跨 session 可检索

跨 session 检索：
- 专家级别：只在同类型 session 里检索（JOB 专家只搜 session_job_*）
- CTRL 级别：在所有 session 里检索

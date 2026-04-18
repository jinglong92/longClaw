# CTRL_PROTOCOLS.md — CTRL 运行协议

> 本文件管：**Skill 加载、压缩、检索、Skill 提议**。
> 专职代理定义 & 路由 → `MULTI_AGENTS.md`
> DEV LOG 格式 → `DEV_LOG.md`
> 全局安全约束 → `AGENTS.md`

---

## Skill 加载（OpenClaw 原生执行）

OpenClaw 运行时原生支持 Progressive Disclosure：会话启动时扫描 `skills/` 目录建立 index，命中触发条件时加载全文，执行完退出 context。longClaw 在此基础上扩展了 `requires` 依赖检查和强制触发规则。

### Skill Index（当前 11 个）

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

### Layer 1：Trim（工具输出实时截断）（借鉴 Claude Code Tool Result Budgeting）

**触发**：任意一条工具输出 > 500 字符，当轮立即执行，无需等待轮数累积。

**执行**：
- 保留工具输出前 500 字符
- 追加截断尾注：`[截断：原始输出 N 字符，已保留前 500 字符。如需完整内容请说"展开上一条工具输出"。]`
- 静默执行，不写入 session-state.json，不计入 compression_count

**设计理由**：换电诊断工具返回通常为结构化 JSON，500 字符可覆盖关键字段（故障码/时间戳/车辆ID）。实时截断比等到 round > 20 更轻量，防止单条超长输出污染后续检索上下文。

### Layer 2：Summarize（轻量摘要）（token 压力驱动，静默）

**触发**（满足任一，且原生 compaction 未触发）：
- 对话轮数 > 20
- （注：单次工具输出 > 500 字符已由 Layer 1（Trim）处理，不再作为 Layer 2 触发条件）

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
DEV LOG 显示：检索级别 / query 变体 / 召回数 / 是否触发跨域

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

## 兜底模型（Force Fallback + Session Model Mode）

用户可在会话中随时指定本轮走兜底模型（本地 Ollama），也可把当前 session 切到 `auto / primary / fallback` 三档模型模式。

### 会话模型模式（写入 `memory/session-state.json.model_mode`）

- `auto`：默认模式，优先 primary，命中 fallback 条件时自动降级
- `primary`：强制走主模型，失败直接报错，不自动降级
- `fallback`：强制走兜底模型，跳过 primary

### 模式切换口令（硬触发）

- `切到兜底` / `后续都走兜底` → `python3 tools/model_mode.py set fallback`
- `切回主模型` / `后续都走主模型` → `python3 tools/model_mode.py set primary`
- `恢复自动` / `恢复自动切换` → `python3 tools/model_mode.py set auto`
- `本轮用兜底模型` / `用兜底模型` / `走兜底` / `用本地模型` / `用 ollama` / `走 ollama` / `本地跑` / `force fallback` / `强制兜底` → 仅本轮 `force_fallback = true`

### 执行方式

#### A. 会话模式切换

CTRL 统一通过 helper 更新 `memory/session-state.json`：

```bash
python3 tools/model_mode.py set fallback
```

之后调用 `tools/llm_fallback.py` 时，即使 payload 不带 `force_fallback`，脚本也会先读 session-state 并按 `model_mode` 执行。

#### A′. 主会话「整段」走兜底（含 1+2 这类简单题）

前提：`~/.openclaw/openclaw.json` 已注册 `models.providers.ollama`（例如 `ollama/gemma4:e2b`）。

仅改 `session-state.json` **不会**让 OpenClaw UI 里仍选中的 `openai-codex/gpt-5.4` 自动变成 Ollama。要让**所有主会话回答**（含算术）都走本地模型，在切 `fallback` 时**同时改 agent 绑定模型**：

```bash
python3 tools/model_mode.py set fallback --sync-openclaw
openclaw gateway restart
```

- 首次执行会备份当前 `agents.defaults.model.primary` 与各 `agents.list[].model` 到 `~/.openclaw/model_mode_agent_restore.json`，再把上述字段统一改为 `ollama/gemma4:e2b`（可用环境变量 `OPENCLAW_FALLBACK_MODEL` 覆盖）。
- 回到云上主模型：`python3 tools/model_mode.py set auto --sync-openclaw`（或 `set primary`）后同样建议 **`openclaw gateway restart`**，以便恢复备份中的模型 ID。

这样 DEV LOG 里 **`mode=fallback` 时 `actual` 应能写 `ollama/gemma4:e2b`**（前提是客户端已重载配置）。

#### A″. 持续兜底（跨会话）直到你手动切回 — 与 Codex 预算

你要的行为是：**前序对话里一旦切到兜底，后续新开会话、下一轮聊天都继续用兜底**，直到你明确切回主模型 —— 这样 **Codex 额度用尽时仍可用本地 Ollama 跑通**。

| 机制 | 是否跨会话持久 | 说明 |
|------|------------------|------|
| 只写 `memory/session-state.json` 的 `model_mode` | **不一定** | CTRL 每轮可能改写该文件；新上下文也可能被初始化，**不能单独当作「全局开关」**。 |
| **`set fallback --sync-openclaw`** | **是** | 把 **`~/.openclaw/openclaw.json`** 里 agent 绑定改到 **`ollama/gemma4:e2b`**，存在磁盘上，**新开 chat、重启客户端后仍生效**，直到执行 **`set auto --sync-openclaw`**（或 **`set primary --sync-openclaw`**）并 **`openclaw gateway restart`** 从备份恢复。 |
| **`llm_fallback_proxy` + `base_url`** | **是**（代理侧） | 流量经代理时按 `session_state_path` 读 `model_mode`；同样建议与 `--sync-openclaw` 二选一或组合，避免「state 写 fallback、主会话仍绑 Codex」的漂移。 |

**自检**：`python3 tools/model_mode.py get` 会输出 `openclaw_defaults_primary` 与 **`persistent_fallback_active`**（仅当 `model_mode=fallback` 且 OpenClaw 主模型已是 `ollama/*` 时为 `true`）。若出现 **`drift_warning`**，说明会话口头兜底了但 **OpenClaw 仍指向 Codex**，需补跑 `--sync-openclaw`。

**Codex 预算**：当 agent 实际绑定 **`ollama/...`** 时，主请求**不走** openai-codex，自然不消耗 Codex 额度（仍须本机 **`ollama serve`** 与对应模型已拉取）。

#### C. 主会话（OpenClaw Chat）与 `model_mode` 闭环

**事实边界**：只改 `memory/session-state.json` 的 `model_mode`，**不会**改变 OpenClaw / Codex **内置主会话**实际调用的 HTTP 上游；主会话不经过 `tools/llm_fallback.py`，除非你显式调用该脚本。

**闭环做法**（让「主回答」也被 `model_mode` 接管）：

1. 在本机常驻运行 `python3 tools/llm_fallback_proxy.py`（配置见 `runtime/model-router.json`）。
2. 在 OpenClaw 侧把**主模型 provider** 的 `base_url` 指到代理（例如 `http://127.0.0.1:18080/v1`），`model` 仍写你逻辑上的主模型名（如 `gpt-5.4`）；**不要把 OpenClaw 里的 `model` 改成 Gemma 名**。
3. `model-router.json` 中保持 `session_state_path`（默认 `memory/session-state.json`，路径相对于 `workspace_root`；未配置 `workspace_root` 时以仓库根为根，即 `tools/` 的上一级目录）。

代理对每个 `POST /v1/chat/completions` 会读取当前 `model_mode`：

| `model_mode` | 行为 |
|--------------|------|
| `fallback` | **跳过 primary**，请求体中的 `model` 改写为兜底模型后直连 Ollama（主会话即走 Gemma）。 |
| `primary` | **仅 primary**，失败/429 等**不**自动降级 Ollama。 |
| `auto` | 先 primary，命中配置的 HTTP/子串/连接类失败后再走 Ollama（与原先一致）。 |

`/health` 会返回当前解析到的 `session_model_mode`，便于核对代理是否读到了同一份 `session-state.json`。

#### B. 本轮强制兜底

调用 `tools/llm_fallback.py`，stdin 传入带 `force_fallback: true` 的 JSON：

```bash
python3 tools/llm_fallback.py < request.json
```

其中 `request.json` 至少包含：

```json
{"system":"<system>","prompt":"<用户问题>","force_fallback":true}
```

### DEV LOG 标注（必须）

```
🛠️ 工具 llm_fallback(force) → [兜底模型] 用户指定走兜底模型：ollama:gemma4:e2b | status=ok(degraded)
```

或：

```
🛠️ 工具 llm_fallback(session_mode=fallback) → [兜底模型] 会话当前为 fallback 模式：ollama:gemma4:e2b | status=ok(degraded)
```

结果输出后，若实际走了兜底模型，回复开头必须注明：**[本轮使用兜底模型 ollama:gemma4:e2b]**。
若 `model_mode = primary`，DEV LOG 必须写清：**当前会话禁用自动降级**。

---

## Session 状态管理

session_id 命名：`openclaw_{domain}_{YYYY-MM-DD}`（如 `openclaw_job_2026-04-14`）

三层状态：
- Layer 1（短期）：recent_turns，超 20 轮触发 Layer 2（Summarize）压缩
- Layer 2（中期）：summary + entities，LLM 摘要 + 关键实体
- Layer 3（长期）：key_conclusions，写入 MEMORY.md，跨 session 可检索

跨 session 检索：
- 专家级别：只在同类型 session 里检索（JOB 专家只搜 session_job_*）
- CTRL 级别：在所有 session 里检索

# longClaw Workspace

语言 / Language: **简体中文** | [English](README.en.md)

> 基于 [OpenClaw](https://github.com/openclaw/openclaw) 深度改造的个人 AI 操作系统——
> 把单个 AI 助手升级为**可扩展的多专家协作运行时**，
> 带工业级记忆检索、会话管理和完整的开发者可观测性。

**🌐 快速概览页面**：[longClaw 介绍站点](https://htmlpreview.github.io/?https://gist.githubusercontent.com/jinglong92/7ce7fefa4803914cd7e07e43dc120c12/raw/longclaw-site.html) — 可视化展示系统架构与核心能力，建议先看这里。

---

## 你可以用它做什么

**🧩 搭建可扩展的多代理系统**
定义任意数量的专职代理（JOB / WORK / LEARN / ENGINEER / ...），通过 CTRL 控制平面统一路由和仲裁。每个代理只处理自己域内的任务，CTRL 负责最终裁决和输出——不会出现多个代理同时给出矛盾答案的情况。

**🧠 多层工业级记忆存储与检索**
内置三层记忆体系：每日日志（短期）、分域长期记忆（MEMORY.md 按 [DOMAIN] 分块）、结构化 JSONL 条目索引（持久化）。检索时先按路由域收敛范围，再做 FTS + Embedding Rerank（Ollama 本地推理），精准召回相关记忆，不被跨域噪声污染。

**🔄 智能会话管理与上下文压缩**
内置两层压缩策略：token 压力驱动的自动压缩（保护首尾关键消息、清理孤立工具对），以及话题边界触发的归档（结论写入长期记忆）。长对话不再因上下文溢出而丢失关键信息。

**🔍 可控的 Developer Mode + 证据驱动执行**

在对话中说 **"开启 dev mode"** 后，系统会把 Dev Mode 视为**会话级硬状态**，并优先从 `memory/session-state.json` 读取会话字段。Developer Mode 的目标不是“多打一段日志”，而是把执行闭环变成**可核验产物优先**：

- 没有真实执行证据，不得声称“已执行/已完成/已生效”
- 没有 verbatim readback，不得声称“已读回校验”
- public-web 只读证据抓取默认按 session 预授权，不与本地任务混淆
- web evidence gate 仅拦截外网证据抓取，不得误拦本地文件修改/读回/验证

```
[DEV LOG]
🔀 路由     JOB | 触发: "offer、面试" | 模式: 单专职
🧠 Memory   [SYSTEM]+[JOB] | ~380 tokens | 节省 72%
📂 Session  第 5 轮 | recent_turns=5/8 | 未触发压缩
🔍 检索     scope=JOB | level=同域归档 | 召回 3 条 | top=[0.91, 0.78, 0.62]
⚖️ 置信度   0.88 [依据: 数据+经验] | 冲突: 无
🤝 A2A      JOB → PARENT 时间冲突协调 | confidence=0.85 | needs_ctrl=false
🏷️ 实体     检测到新实体: Shopee=进行中（2026-04-10）→ 已更新 [JOB]
```

可观测的内容包括：**路由决策 · 会话状态 · 记忆注入量 · 检索范围 · 专家置信度 · A2A 多代理通信 · 冲突裁决过程 · 实体更新记录**

**🧱 Workspace Baseline 已收口**

当前 workspace 已把”授权、证据、读回、session 状态、外网检索门禁”固化成一套统一基线：

- `AGENTS.md`：Deny > Ask > Allow 三层授权 / Immutable Rules / execution latch / readback validation
- `.claude/settings.json`：PostCompact / FileChanged / PreToolUse / SessionStart hooks（harness 层强制执行）
- `memory/session-state.json`：Dev Mode、当前域、待确认动作、压缩次数

**⚡ Workflow Skill 按需加载**
14 个高频任务固化为独立 SKILL.md，会话启动时只建索引，命中触发条件时立即加载全文执行，执行完即退出。每个 skill 声明 `requires` 依赖字段，命中前先检查工具可用性，不满足直接返回 `blocked`。

**🤖 Subagent 并发架构**
四类专用子代理（model: inherit，继承主 session 的 Codex），各自有独立 context 和最小工具权限：
- `search-agent`：并发搜索，只有 WebFetch/WebSearch/Read/Grep 权限
- `memory-agent`：BRO/SIS 路由时后台检索近期记忆，只读权限；回复中明确标注 `[本轮]`/`[记忆]`/`[判断]` 三种来源
- `heartbeat-agent`：cron 定时巡检，只读 + 写 heartbeat-state.json + 自动检查索引新鲜度
- `repo-explorer`：code-agent 触发时自主探索 codebase，返回结构化文件地图，只读

**📊 本地训练底座（Local-first）**
真实交互可沉淀为训练资产：Trace 收集 → Judge 评分 → Dataset 构建 → MLX / LLaMA-Factory 本地训练，全流程在 Mac mini M4 上运行，无需上传数据到云端。

---

| | |
|---|---|
| **基于** | [OpenClaw](https://github.com/openclaw/openclaw)（Peter Steinberger，MIT 开源，353k ⭐） |
| **部分借鉴** | [Hermes Agent](https://github.com/NousResearch/hermes-agent)（Nous Research，MIT 开源，40k ⭐） |
| **底层 LLM** | Codex（OpenClaw 运行时） |
| **运行环境** | Mac mini M4（24/7 本地），WhatsApp / Telegram / Discord 交互 |
| **核心扩展** | 多专家仲裁、分域记忆、向量化检索、Subagent 并发、Harness hooks、训练底座 |

---

## Quick Start

**前提**：已安装 [OpenClaw](https://github.com/openclaw/openclaw)，workspace 目录已创建。

```bash
# 1. Clone 本仓库
git clone https://github.com/jinglong92/longClaw.git
cd longClaw

# 2. 把通用配置复制到你的 OpenClaw workspace
cp AGENTS.md SOUL.md MULTI_AGENTS.md /path/to/your-workspace/
cp -r skills/ /path/to/your-workspace/

# 3. 从模板创建你自己的私有配置（这 3 个文件不会被推送到 GitHub）
cp USER.md.example /path/to/your-workspace/USER.md
cp MEMORY.md.example /path/to/your-workspace/MEMORY.md
# 然后编辑 USER.md，填入你的名字、职业、偏好、当前上下文

# 4. 安装 memory 检索工具（可选，增强检索能力）
cp -r tools/ /path/to/your-workspace/
cd /path/to/your-workspace
python3 tools/memory_entry.py    # 构建索引
python3 tools/memory_search.py --query "测试" --verbose  # 验证

# 5. 在 OpenClaw 对话中说"开启 dev mode"，验证 Dev Mode 与路由/证据规则

# 6. 可选：同步当前基线脚本
bash refactor_workspace_baseline.sh
```

**需要自己创建的私有文件**（不在 repo 里，不会推送）：

| 文件 | 来源 | 要改什么 |
|------|------|---------|
| `USER.md` | 从 `USER.md.example` 复制 | 你的名字、职业、偏好、当前上下文、专属术语定义 |
| `MEMORY.md` | 从 `MEMORY.md.example` 复制 | 从空白开始，随对话积累长期记忆 |
| `memory/` | 自动生成 | 每日对话日志，由 CTRL 自动写入 |

**可以直接复用（不需要改）**：
`AGENTS.md` · `SOUL.md` · `MULTI_AGENTS.md` · `skills/` · `tools/`

---

## 目录

1. [三系统定位对比](#1-三系统定位对比)
2. [核心设计](#2-核心设计)
3. [当前系统架构](#3-当前系统架构)
4. [Memory 检索系统](#4-memory-检索系统)
5. [Workflow Skills](#5-workflow-skills)
6. [演示](#6-演示)
7. [文件索引](#7-文件索引)
8. [当前边界](#8-当前边界)
9. [设计借鉴说明](#9-设计借鉴说明)

---

## 1. 三系统定位对比

longClaw 与官方 OpenClaw、Hermes Agent 同属"个人 AI 操作系统"赛道，但定位和架构有本质差异。

### 1.1 一句话定位

| 系统 | 定位 | 核心范式 |
|------|------|---------|
| **官方 OpenClaw** | "The AI that actually does things" | 单 Agent + 本地执行 + 自我进化 |
| **Hermes Agent** | Self-improving AI agent | 单 Agent + 多工具 + 技能自动学习 |
| **longClaw（本仓库）** | 个人 AI 操作系统，多专家仲裁 + 可优化 | Multi-Agent + CTRL 仲裁 + 训练底座 |

### 1.2 架构对比

```
官方 OpenClaw：
  用户 → OpenClaw Agent（本地 24/7）
           ├── 自动生成 SKILL.md（自我进化）
           ├── 50+ 集成（Gmail/GitHub/智能家居）
           └── ClawHub 技能市场

Hermes Agent：
  用户 → AIAgent.run_conversation()
           ├── 47 个工具 / 20 toolset
           ├── SQLite + FTS5 记忆检索
           └── Progressive Disclosure skill 加载

longClaw（本仓库）：
  用户 → CTRL 控制平面（唯一对外出口）
           ├── 10 个专职代理（JOB/WORK/LEARN/ENGINEER/...）
           ├── 置信度协议 + P0-P4 冲突裁决 + Risk Audit
           ├── 分域记忆注入（~80% token 节省）
           ├── route-aware 检索（FTS + Hybrid Embedding）
           └── openclaw_substrate（Trace→Judge→Dataset→训练）
```

### 1.3 核心差异矩阵

| 能力维度         | 官方 OpenClaw         | Hermes Agent     | longClaw                         |
| ------------ | ------------------- | ---------------- | -------------------------------- |
| **执行层**      | ✅ 本地代码执行、文件读写、浏览器控制 | ✅ 47 工具          | ✅ 继承 OpenClaw 完整执行层              |
| **专家仲裁**     | ❌ 单 Agent           | ❌ 单 Agent        | ✅ 10 专职代理 + CTRL 仲裁              |
| **风险审计**     | ❌                   | ❌                | ✅ P0-P4 优先级 + Risk Audit         |
| **分域记忆**     | ❌ 全量注入              | ⚠️ FTS-only 全局检索 | ✅ 按路由域精准注入                       |
| **向量检索**     | ❌                   | ⚠️ FTS-only      | ✅ route-aware + Hybrid Embedding |
| **用户画像层**    | ❌                   | ❌                | ✅ USER.md 独立画像                   |
| **技能自动生成**   | ✅ Agent 自写 SKILL.md | ✅ 自动精炼           | ⚠️ 提议系统（用户确认后写入）                 |
| **本地训练底座**   | ❌                   | ❌                | ✅ Trace→Judge→Dataset→MLX        |
| **50+ 集成生态** | ✅ ClawHub           | ✅ Skills Hub     | ✅ 继承 OpenClaw                    |
| **开源**       | ✅ MIT               | ✅ MIT            | ✅ MIT                            |

> longClaw 的执行层（代码执行/文件读写/浏览器控制/50+ 集成）由 OpenClaw 软件本体提供，
> 运行在 Mac mini M4 上。workspace 配置层（本仓库）在此基础上增加了仲裁、记忆、检索、训练四层能力。

---

## 2. 核心设计

### 2.1 CTRL 控制平面

传统多代理系统的问题：多个 Agent 都能回答，但没人负责最后裁决；并行多但冲突难以解释；路由决策不可见。

longClaw 的设计：

- `CTRL` 是唯一对外交付入口，专职代理只做域内推理
- 默认单专职，跨域问题按需启用双专职并行（≤2）
- 每次回复携带 `Routing:` 行，路由决策完全可见
- 高影响决策触发 Risk Audit（P0 强制阻断 → P4 信息合并）

$$\text{Final Answer} = \text{CTRL}(\text{route},\ \text{specialist outputs},\ \text{risk audit},\ \text{memory slice})$$

**与官方 OpenClaw / Hermes 的差异**：两者均为单 Agent 范式，没有专家仲裁层。longClaw 的多专家仲裁是三系统中独有的。

### 2.2 分域记忆注入

`MEMORY.md` 按 `[SYSTEM] / [JOB] / [LEARN] / [ENGINEER] / ... / [META]` 分块，CTRL 按路由只注入必要片段：

$$\text{Injected Memory} = \text{[SYSTEM]} \cup \text{[Relevant Domain]}$$

相比全量注入，每次节省约 **80% token**，同时避免历史噪声污染当前请求。

**与官方 OpenClaw / Hermes 的差异**：官方 OpenClaw 全量注入 MEMORY.md；Hermes 的 FTS 检索是全局范围。longClaw 在注入前先按路由域过滤，是三系统中唯一做到分域注入的。

### 2.3 Workflow Skill（借鉴 Hermes，有所调整）

把高频复杂任务沉淀为 workflow skill，遵循 **Progressive Disclosure**¹ 原则：

- 会话启动时只建 skill index（name + description）
- 命中触发条件时才加载完整 `SKILL.md`
- 执行完成后退出 context，不长期占用 token 预算

当前 10 个 skill（详见 [§ Workflow Skills](#6-workflow-skills)）：

| Skill | 触发场景 | 核心输出 |
|-------|---------|---------|
| `jd-analysis` | 收到 JD 文本/截图 | 能力模型 + 匹配度 + 投递行动 |
| `paper-deep-dive` | 发送论文标题/摘要 | 方法论 + 对比 + 可复述摘要 |
| `agent-review` | 审查 workspace 配置 | 规则冲突 + token 效率 + 漏洞清单 |
| `fact-check-latest` | 询问最新资讯/价格 | `[确定]`/`[推断]`/`[缺失]` 分级 |
| `research-execution-protocol` | 复杂实现/排障/验证闭环 | 证据驱动执行、最小改动、验证闭环输出 |
| `research-build` | 从需求到实现的工程闭环 | 验收标准→最小改动→验证→回滚点 |
| `skill-safety-audit` | 外部 skill/脚本接入审计 | 风险分级、兼容性判断、接入建议 |
| `session-compression-flow` | 长会话压缩与跨会话衔接 | 压缩触发→摘要落盘→索引重建→新会话连续性 |
| `multi-agent-bootstrap` | 多代理架构搭建/迁移 | 快速同步初学者友好的多代理配置与可见路由 |
| `public-evidence-fetch` | 公开网页/论文证据抓取 | exact query + URL + verbatim snippet + 段落位置 |

> ¹ Progressive Disclosure 设计借鉴自 **[Hermes Agent](https://github.com/NousResearch/hermes-agent)**。
> Hermes 有完整的 skill_manage 工具实现自动 create/patch；longClaw 将其移植为 workspace 协议层约定。

**与官方 OpenClaw 的差异**：官方 OpenClaw 的 Agent 可以自动写 SKILL.md（真正的自我进化）；longClaw 目前是提议系统，用户确认后才写入。

### 2.4 route-aware Memory 检索

OpenClaw 原生 `memory_search` 是 FTS-only，词面不重叠就返回空结果。longClaw 在此基础上增加了两层：

**第一层：scope filter（先决定搜哪里）**

```
Level 1: 当前 session / recent turns
Level 2: 同域 + 7天内   → 结果 ≥ 2 则停止
Level 3: 同域 + 全量    → 结果 ≥ 2 则停止
Level 4: 跨域全量       → 兜底，结果标注[跨域]
```

**第二层：hybrid rerank（再决定怎么搜）**

$$S(q,d) = S_{\text{fts}} + 0.4 \cdot N_{\text{entity}} + 0.05 \cdot \text{imp}(d) + 0.05 \cdot \mathbf{1}_{\text{daily}}(d)$$

可选 Hybrid 模式：FTS candidate → Ollama nomic-embed-text（768 维）→ RRF fusion

**与 Hermes 的差异**：Hermes 的 FTS 是全库统一检索；longClaw 先按路由域收敛范围，再做 FTS + embedding rerank，解决了"更聪明地召回不该召回的东西"的问题。

### 2.5 本地训练底座（openclaw_substrate）

longClaw 独有，官方 OpenClaw 和 Hermes 均无此能力：

$$\text{Interaction} \rightarrow \text{Trace} \rightarrow \text{Judge} \rightarrow \text{Dataset} \rightarrow \text{Replay / Optimize}$$

- `trace_plane`：记录 canonical trace（请求/响应/路由/重试）
- `judge_plane`：规则评价 + 奖励信号（RuleBasedJudge + LlmJudge）
- `dataset_builder`：构建 SFT/GRPO 可训练数据集
- `shadow_eval`：baseline vs candidate 回放对比
- `backends/`：本地 MLX-LM + LLaMA-Factory 导出路径

---

## 3. 当前系统架构

### 3.1 主架构图

![longClaw 多代理控制系统架构图](docs/architecture-dashboard-zh-v5.png)

![longClaw Agent v3 路线架构图](docs/architecture-dashboard-zh-v3-agent.jpg)

### 3.2 当前六层结构

```mermaid
flowchart TD
    U["User"] --> C["CTRL Control Plane"]

    C --> P["Persona & Safety\nAGENTS.md / SOUL.md"]
    C --> M["Memory Plane\nUSER.md / MEMORY.md / memory/YYYY-MM-DD.md"]
    C --> R["Routing Plane\nMULTI_AGENTS.md"]
    C --> W["Workflow Plane\nskills/*/SKILL.md"]
    C --> RET["Retrieval Plane\ntools/memory_search.py\nFTS + Hybrid Embedding"]
    C --> T["Training Plane\nopenclaw_substrate/*"]

    R --> S1["LIFE / JOB / WORK / ENGINEER / PARENT"]
    R --> S2["LEARN / MONEY / BRO / SIS / SEARCH"]

    W --> K1["jd-analysis"]
    W --> K2["paper-deep-dive"]
    W --> K3["agent-review"]
    W --> K4["fact-check-latest"]
    W --> K5["research-execution-protocol"]

    RET --> RE1["Route-Aware Scope Filter"]
    RET --> RE2["FTS + BM25-like Scoring"]
    RET --> RE3["Ollama nomic-embed-text（可选）"]
```

### 3.3 请求流动时序

```mermaid
sequenceDiagram
    participant U as User
    participant C as CTRL
    participant M as Memory
    participant RET as Retrieval
    participant R as Router
    participant K as Skill Loader
    participant S as Specialist
    participant A as Audit

    U->>C: 请求
    C->>M: 读取分域记忆切片
    C->>RET: route-aware 检索（同域优先）
    RET-->>C: Top-K 相关记忆条目
    C->>R: 决定单专职 / 双专职 / SEARCH 先行
    R-->>C: route result
    C->>K: 如命中 workflow，则按需加载 skill
    K-->>C: skill or none
    C->>S: 分派任务
    S-->>C: 结构化结果 + 置信度
    C->>A: 高影响任务触发 Risk Audit
    A-->>C: 风险与裁决约束
    C-->>U: 最终统一输出 + Routing
```

---

## 4. Memory 检索系统

> 2026-04-10 新增，独立于 `openclaw_substrate`，放在 `tools/` 目录，无外部依赖（FTS 部分）。

### 检索架构

```
用户 query
    │
    ▼
Query Rewrite（3 个变体）
  ① 原始 query
  ② + domain hints（路由到 JOB 自动加 "job career offer interview"）
  ③ + 实体提取版（公司名 / 技术词 / 项目名）
    │
    ▼
Route-Aware Scope Filter
  Level 2: 同域 + 7天内  →  结果 ≥ 2 则停止
  Level 3: 同域 + 全量   →  结果 ≥ 2 则停止
  Level 4: 跨域全量      →  兜底，标注[跨域]
    │
    ▼
FTS Scoring（BM25-like，纯 Python，无外部依赖）
  实体精确命中 +0.4 · N_entity
  daily 条目（事实性更强）+0.05
  全局按分数重排（不受 level 顺序限制）
    │
    ├── FTS-only → Top-K
    │
    └── Hybrid（--hybrid，需 Ollama）
          nomic-embed-text（768 维，M4 本地推理，无需 GPU）
          → RRF fusion（FTS rank + embedding rank）
          → Top-K
```

### 快速上手

```bash
# 构建索引（首次或 MEMORY.md 更新后）
python3 tools/memory_entry.py
python3 tools/memory_entry.py --stats

# FTS 检索（无需 Ollama，立即可用）
python3 tools/memory_search.py --query "Shopee 面试" --domain JOB
python3 tools/memory_search.py --query "openclaw 调优" --domain ENGINEER --verbose

# Hybrid 检索（需要 Ollama）
brew install ollama && ollama pull nomic-embed-text
python3 tools/memory_search.py --query "换电站运力" --domain ENGINEER --hybrid
```

---

## 5. Workflow Skills

14 个高频任务已固化为 workflow skill，按需加载，不常驻 prompt。命中触发条件即自动执行，无需用户二次提醒。每个 skill 有 `requires` 依赖声明，缺少所需工具时直接返回 `blocked`，不空转。

### jd-analysis
触发：收到 JD 文本 / 截图 / 链接
输出：岗位解码（硬技能 / 软技能 / 隐含要求）→ 匹配度评级（A/B+/B/C）→ 简历叙事建议 → 本周行动清单

### paper-deep-dive
触发：发送论文标题 / 链接 / 摘要 / 方法片段
输出（8 个模块）：Essence → Methodology（公式 + 伪代码）→ SOTA 对比 → Reviewer#2 批判 → 工业落地评估 → Insights → Decision Card → 可复述摘要

### agent-review
触发："帮我 review workspace" / "检查配置有没有问题"
输出：规则一致性（AGENTS.md vs MULTI_AGENTS.md 冲突）→ Token 效率分析 → 逻辑漏洞清单（P0/P1/P2）

### fact-check-latest
触发：询问最新价格 / 资讯 / 技术动态
输出：`[F]` 确定信息（≥2 个独立来源）/ `[I]` 推断信息（1 个来源）→ 时效说明 + 来源列表

### research-execution-protocol
触发：复杂实现、排障、配置修复、实验验证、多轮失败后闭环推进
输出：`[FACT]/[HYP]/[TEST]/[RESULT]/[NEXT]` 结构化执行链；强调先证据后判断、先验证后宣称完成、失败后换路

### research-build
触发："直接帮我实现" / 用户提供明确目标和代码位置，希望生成改动计划或直接修改
输出：验收标准 → 最小改动计划 → 立即验证 → 明确回滚点

### skill-safety-audit
触发：用户给出 GitHub 仓库 / SKILL.md / shell script 让你评估；准备引入新的自动化/hook/daemon
输出：风险分级（P0-P2）、兼容性判断、接入建议；冲突优先级最高

### session-compression-flow
触发：对话轮次 >20（CTRL 自动检测）/ 用户明确要求压缩 / 话题切换信号
输出：压缩触发 → 摘要落盘（memory/YYYY-MM-DD.md）→ key_conclusions 写入 MEMORY.md → 新会话连续性

### multi-agent-bootstrap
触发：用户要求创建/迁移多代理架构、添加角色定义、强制路由可见
输出：快速同步初学者友好的多代理配置 + 可见路由 + 变更摘要

### public-evidence-fetch
触发："给我原文片段" / "不要总结，给证据" / "exact query + URL + snippet"
输出：exact query + URL + verbatim snippet + 段落位置 + 简短解释

### deep-research
触发："帮我深度调研" / "全面了解一下" / "多角度分析" / 需要多来源的复杂调研
输出：问题拆解 → 并发 spawn search-agent×2-3 → RRF 融合 → 带来源的综合报告

### memory-companion
触发：CTRL 路由到 BRO 或 SIS 时自动触发（无需用户说）
输出：后台 spawn memory-agent 检索近期记忆 → 注入情绪状态/上次话题 → BRO/SIS 带记忆回复

### proactive-heartbeat
触发：cron 每天 08:30 / 18:00 自动巡检；用户说"检查一下我的待办"
输出：heartbeat-agent 静默巡检 → 写入 heartbeat-state.json → 用户下次开口时呈现 P0/P1 事项

### paperbanana
触发："帮我画论文配图" / "生成方法架构图" / 提供方法段落+图注
输出：Retriever→Planner→Stylist→Visualizer→Critic 五代理流水线生成发表级配图（需本地安装）

---

## 6. 演示

### 演示一：多专家仲裁

```
开启 dev mode。
从 ENGINEER 和 JOB 两个视角同时分析：
这个技术项目应该如何定位和表达？
要求各自给出置信度，CTRL 最后仲裁。
```

展示：路由可见 + 双专职克制触发 + CTRL 真实仲裁 + 置信度差异

### 演示二：Workflow Skill

```
按 jd-analysis 工作流处理这个岗位。
输出：能力模型、匹配度、主要短板、本周行动。
```

展示：角色负责领域判断，skill 负责具体流程，输出结构稳定可复现

### 演示三：最新事实核查

```
按 fact-check-latest 工作流，核查最近 30 天 Agent + OR 岗位趋势。
要求区分 [确定] / [推断] / [缺失]。
```

展示：SEARCH 角色 + 不对不确定信息装懂 + 信息完整性显式表达

### 演示四：Memory 检索对比

```bash
# FTS-only vs Hybrid，展示 route-aware scope 的效果
python3 tools/memory_search.py --query "Shopee 面试" --domain JOB --verbose
python3 tools/memory_search.py --query "上次面试进展" --domain JOB --hybrid --verbose
```

展示：同域优先 + 实体命中加权排序 + hybrid 语义补盲

---

## 7. 文件索引

### 核心协议

| 文件 | 作用 |
|------|------|
| [AGENTS.md](AGENTS.md) | 全局行为约束 + Deny/Ask/Allow 三层授权 + Immutable Rules（最高优先级）|
| [SOUL.md](SOUL.md) | 助手人格契约 |
| [MULTI_AGENTS.md](MULTI_AGENTS.md) | 专职代理定义 + 路由规则 + A2A 协议 |
| [CTRL_PROTOCOLS.md](CTRL_PROTOCOLS.md) | CTRL 运行协议：Skill 加载 / 压缩 / 检索 / Skill 提议 |
| [DEV_LOG.md](DEV_LOG.md) | DEV LOG 9 字段格式规范 + 强制输出规则 |
| [HEARTBEAT.md](HEARTBEAT.md) | 心跳静默策略 + Proactive Heartbeat Agent 说明 |
| `USER.md` | 用户画像与偏好（私有，从 USER.md.example 创建，不在 repo 里）|
| `MEMORY.md` | 长期记忆（分域块，私有，从 MEMORY.md.example 创建，不在 repo 里）|
| [USER.md.example](USER.md.example) | USER.md 公开模板 |
| [MEMORY.md.example](MEMORY.md.example) | MEMORY.md 公开模板 |

### Harness 配置（.claude/）

| 文件 | 作用 |
|------|------|
| [.claude/settings.json](.claude/settings.json) | UserPromptSubmit（/new 重启）/ PostCompact / FileChanged / PreToolUse / SessionStart hooks |
| [.claude/agents/search-agent.md](.claude/agents/search-agent.md) | 并发搜索子代理（inherit model，WebFetch+Read+Grep）|
| [.claude/agents/memory-agent.md](.claude/agents/memory-agent.md) | 记忆检索子代理（inherit model，只读）|
| [.claude/agents/heartbeat-agent.md](.claude/agents/heartbeat-agent.md) | 心跳巡检子代理（inherit model，只读+写 heartbeat-state.json+自动索引重建）|
| [.claude/agents/repo-explorer.md](.claude/agents/repo-explorer.md) | Codebase 探索子代理（inherit model，只读，返回结构化文件地图）|

### Workflow Skills

| 文件 | 触发场景 |
|------|---------|
| [skills/job/jd-analysis/SKILL.md](skills/job/jd-analysis/SKILL.md) | JD 分析 |
| [skills/learn/paper-deep-dive/SKILL.md](skills/learn/paper-deep-dive/SKILL.md) | 论文深度解读 |
| [skills/engineer/agent-review/SKILL.md](skills/engineer/agent-review/SKILL.md) | Workspace 审查 |
| [skills/search/fact-check-latest/SKILL.md](skills/search/fact-check-latest/SKILL.md) | 最新事实核查 |
| [skills/engineer/research-execution-protocol/SKILL.md](skills/engineer/research-execution-protocol/SKILL.md) | 研究型工程执行协议 |
| [skills/engineer/research-build/SKILL.md](skills/engineer/research-build/SKILL.md) | 研究工程落地构建 workflow |
| [skills/meta/skill-safety-audit/SKILL.md](skills/meta/skill-safety-audit/SKILL.md) | 外部技能接入安全审计 |
| [skills/meta/session-compression-flow/SKILL.md](skills/meta/session-compression-flow/SKILL.md) | 会话压缩与跨会话衔接流程 |
| [skills/multi-agent-bootstrap/SKILL.md](skills/multi-agent-bootstrap/SKILL.md) | 多代理架构搭建/迁移 |
| [skills/search/public-evidence-fetch/SKILL.md](skills/search/public-evidence-fetch/SKILL.md) | 公开网页/论文证据抓取 |
| [skills/search/deep-research/SKILL.md](skills/search/deep-research/SKILL.md) | 并发多源深度调研（spawn search-agent×2-3）|
| [skills/companion/memory-companion/SKILL.md](skills/companion/memory-companion/SKILL.md) | 记忆增强陪伴（BRO/SIS 自动触发）|
| [skills/meta/proactive-heartbeat/SKILL.md](skills/meta/proactive-heartbeat/SKILL.md) | 主动心跳巡检（cron + SessionStart 呈现）|
| [skills/learn/paperbanana/SKILL.md](skills/learn/paperbanana/SKILL.md) | 学术论文配图自动生成（需本地安装）|

### Memory 检索工具

| 文件 | 作用 |
|------|------|
| [tools/memory_entry.py](tools/memory_entry.py) | MEMORY.md + daily memory → JSONL 条目 |
| [tools/memory_search.py](tools/memory_search.py) | route-aware FTS + hybrid embedding 检索 |

### 本地训练底座

| 文件 | 作用 |
|------|------|
| [openclaw_substrate/gateway.py](openclaw_substrate/gateway.py) | OpenAI 兼容 API 网关 |
| [openclaw_substrate/trace_plane.py](openclaw_substrate/trace_plane.py) | Trace 记录与状态组装 |
| [openclaw_substrate/judge_plane.py](openclaw_substrate/judge_plane.py) | 规则评价 + 奖励信号 |
| [openclaw_substrate/dataset_builder.py](openclaw_substrate/dataset_builder.py) | 训练数据集构建 |
| [openclaw_substrate/shadow_eval.py](openclaw_substrate/shadow_eval.py) | Baseline vs candidate 回放对比 |

### 学习文档

| 文件 | 内容 |
|------|------|
| [docs/longclaw-design.md](docs/longclaw-design.md) | 系统设计与 Claude Code 对比（架构/记忆/压缩/协同/Harness，含设计决策矩阵）|
| [docs/longclaw-practice.md](docs/longclaw-practice.md) | 实践经验与踩坑（5类常见问题解法、演进历程、已知问题）|
| [docs/memory-compression-guide.md](docs/memory-compression-guide.md) | 记忆与压缩机制详解 + Mermaid 原理图（PPT 专用）|
| [docs/claude-code-internals.md](docs/claude-code-internals.md) | Claude Code 内部架构逆向分析（sourcemap，10个核心设计模式）|
| [docs/coding-agent-learning-plan.md](docs/coding-agent-learning-plan.md) | Coding Agent 学习路径（SWE-agent/Aider/SWE-bench，5个里程碑）|

### 历史设计资料

- [multi-agent/ARCHITECTURE.md](multi-agent/ARCHITECTURE.md)
- [multi-agent/PROFILE_CONTRACT.md](multi-agent/PROFILE_CONTRACT.md)
- [multi-agent/UNIFIED_SYNC_2026-03-25.md](multi-agent/UNIFIED_SYNC_2026-03-25.md)

---

## 8. 当前边界

| 边界 | 说明 |
|------|------|
| workspace 改造层 | longClaw 是 OpenClaw workspace 改造，原生能力（hooks/权限/compaction/skill加载）直接可用；longClaw 新增仲裁、分域记忆、检索、subagent、harness hooks、训练底座 |
| Subagent 模型 | subagent 只支持 Claude 模型（inherit/sonnet/opus/haiku），不支持 Codex；当前四个 agent 均设为 inherit 继承主 session |
| Session 连续性 | 微信 bot 每条消息触发新 session（ephemeral），DEV LOG 的 round 是本次运行内轮次；跨 session 统计由 heartbeat-agent 负责 |
| memory-agent 来源标注 | BRO/SIS 回复中必须区分 [本轮]/[记忆]/[判断] 三种来源；memory-agent 超时时禁止把当前会话信息包装成记忆检索结果 |
| FileChanged hook 时效 | 只感知进程运行中的文件变更；启动前的变更需重启 OpenClaw 或 /new 后生效 |
| 技能自动生成 | 目前是提议系统（用户确认后才写入），非官方 OpenClaw 式自动写入 |
| memory 检索质量 | 取决于 MEMORY.md 的事实条目密度；heartbeat-agent 每天自动检查索引新鲜度并按需重建 |
| hybrid 增益 | 语料以配置/规则文本为主时 FTS 与 embedding 差距不大；事实型日志积累后优势显现 |
| openclaw_substrate | 训练底座已定义优化闭环，短期不启用（主用 Codex via OpenClaw） |
| 并发上限 | 专职并行 ≤2；subagent 并发 ≤3（deep-research 上限）|
| Proactive Heartbeat | 需在 Mac mini 上手动运行一次 setup_heartbeat_cron.sh 安装 cron job |

---

## 9. 设计借鉴说明

### 官方 OpenClaw

> **OpenClaw**（Peter Steinberger，MIT 开源，353k ⭐）：https://github.com/openclaw/openclaw

longClaw 是在官方 OpenClaw 软件基础上改造的 workspace。执行层（代码执行、文件读写、浏览器控制、50+ 集成、Heartbeat 机制）完全继承官方 OpenClaw，运行在 Mac mini M4 上。

本仓库是 workspace 配置层的改造，包括：

- 扩展了 MULTI_AGENTS.md（10 个专职代理、A2A 协议、置信度裁决）
- 重构了 MEMORY.md（分域块注入）
- 新增 tools/ 目录（独立 memory 检索工具）
- 新增 openclaw_substrate/（本地训练底座）

### Hermes Agent

> **Hermes Agent**（Nous Research，MIT 开源，40k ⭐）
> GitHub：https://github.com/NousResearch/hermes-agent
> 文档：https://hermes-agent.nousresearch.com/docs/

| 借鉴点 | Hermes 原始设计 | longClaw 的实现与调整 |
|--------|---------------|---------------------|
| **Skill 格式（SKILL.md）** | 结构化 frontmatter，粒度为具体 workflow（arxiv-search、github-pr-workflow 等） | 沿用格式和粒度原则，为 4 个高频任务建 SKILL.md；角色定义保留在 MULTI_AGENTS.md |
| **Progressive Disclosure** | 启动时只加载 skill name+description，命中时才读完整内容，有 skill_manage 工具支撑 | OpenClaw 运行时原生支持；longClaw 在此基础上扩展了 requires 依赖检查和强制触发规则 |
| **Context Compression** | 50% token threshold 触发，四阶段算法（清理冗长输出→划定边界→生成摘要→清理孤立工具对） | 分两层：Layer A 为压缩偏好声明（与 OpenClaw 原生 compaction 协同），Layer B 为话题归档 |
| **FTS + embedding 检索** | SQLite FTS5 + session 血缘追踪，mode=fts-only | 增加 route-aware scope filter + Ollama 本地 embedding rerank + RRF fusion |
| **Proactive Troubleshooting** | 外部查询失败时主动尝试备用路径，不直接问用户 | 沿用理念，修正 fallback 路径（Google Cache 已下线 → Wayback Machine） |

**longClaw 独有，Hermes 没有的**：

| 能力 | 说明 |
|------|------|
| Multi-Agent 仲裁 + Risk Audit | 10 个专职代理 + CTRL 仲裁 + P0-P4 优先级裁决 |
| USER.md 用户画像层 | 独立的用户上下文文件，个性化建议的基础 |
| openclaw_substrate 训练底座 | Trace → Judge → Dataset → MLX 训练闭环 |
| route-aware scope filter | 检索前先按路由域收敛范围，而非全库检索 |

---

> 这套系统最有价值的地方，不是"会分角色聊天"，而是把控制、记忆、流程和优化闭环拆清楚——让每一层都可以独立演进、独立观测、独立优化。

---

## Contributing

欢迎贡献 Workflow Skill、改进检索工具或完善训练底座。

最低门槛的贡献方式：在 `skills/<domain>/<skill-name>/` 下新建一个 `SKILL.md`，
描述一个具体的可复用工作流（参考现有的 `skills/job/jd-analysis/` 格式）。

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## Skills 扩展原则

新增 skill 必须满足：
- 不替代 CTRL（skill 是 workflow，不是角色）
- 不改变全局人格
- 不常驻污染上下文（执行完即退出）
- 优先局部增强、可验证、可回滚

新增方式：在 `skills/<domain>/<skill-name>/` 下新建 `SKILL.md`，参考现有格式（frontmatter + 触发条件 + 流程步骤 + 输出格式）。


---

## 架构分层说明

longClaw 是运行在 Mac mini M4 上的 **OpenClaw workspace 改造层**，不是独立运行时。

### OpenClaw 原生提供（直接可用，无需在 workspace 里重新实现）

| 能力 | 说明 |
|------|------|
| Hooks 系统 | PreToolUse / PostToolUse / SessionStart / Stop 等事件，harness 层自动执行 |
| 权限模型 | Deny > Ask > Allow 三层，settings.json 配置，harness 强制执行 |
| 工具调用生命周期 | 工具发现、调用、结果注入，由 OpenClaw 运行时管理 |
| Context compaction | session 接近上下文窗口时自动触发，保护工具调用边界 |
| SKILL.md 加载 | Progressive Disclosure，会话启动时扫描 skills/，命中时加载全文 |
| CLAUDE.md 加载 | 项目根目录 + 父目录递归加载，compaction 后自动重读 |
| Session 生命周期 | 会话创建、恢复、结束，由 OpenClaw 管理 |

### longClaw workspace 层新增（本仓库的改造内容）

| 能力 | 说明 |
|------|------|
| CTRL 多专家仲裁 | 10 个专职代理 + P0-P4 冲突裁决，定义在 MULTI_AGENTS.md |
| 分域记忆注入 | MEMORY.md 按 [DOMAIN] 分块，CTRL 按路由只注入必要片段 |
| route-aware 检索 | tools/memory_search.py，4 级作用域 + FTS + Hybrid Embedding |
| Skill 依赖声明 | requires 字段，命中前检查工具可用性 |
| Layer B 话题归档 | 话题结束时提炼结论写入 MEMORY.md，跨 session 可检索 |
| DEV LOG 格式 | 9 字段可观测日志，含 🛠️ 工具 PostToolUse 注入 |
| openclaw_substrate | 本地训练底座，Trace→Judge→Dataset→MLX（设计完成，待激活） |

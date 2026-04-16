# longClaw 技术深度解析

> 版本：2026-04-14 | 对应简历项目：longClaw 个人 AI 助理操作系统（2026.03 — 至今）
> 本文档整合了记忆系统、压缩机制、Subagent 架构、Harness 工程、Coding Agent 五个方向的完整原理
> 可直接用于面试技术深挖准备

---

## 零、系统全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                         longClaw 系统全景                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    OpenClaw 运行时（底层）                    │   │
│  │  hooks / 权限模型 / 工具调用 / compaction / skill加载        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ↑ 基础设施层                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   longClaw workspace 改造层                   │  │
│  │                                                              │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │  CTRL 控制层 │  │  记忆系统     │  │  Harness 工程     │   │  │
│  │  │ 10专职+仲裁  │  │ 三层+四级检索 │  │ hooks+权限+压缩   │   │  │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │                                                              │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │ Subagent层  │  │  Skill 系统   │  │  训练底座         │   │  │
│  │  │ 并发+最小权限│  │ 14个工作流   │  │ Trace→Judge→Data │   │  │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**核心设计原则**（对应简历三个 bullet）：
1. **记忆系统**：简单存储 + 智能检索，按域精准注入，节省 80% token
2. **多模型协同**：CTRL 仲裁 + Subagent 并发，最小权限隔离
3. **执行完整性**：Harness 层强制，幻觉声明率接近零

---

## 一、记忆系统：三层架构 + 四级检索

### 1.1 为什么不用向量数据库

面试高频问题。核心论据来自 Claude Code 内部设计（sourcemap 逆向分析）：

> "简单存储 + 智能检索 > 复杂存储 + 复杂检索"

| 方案 | 优点 | 缺点 | longClaw 选择 |
|------|------|------|--------------|
| 向量数据库 | 语义检索强 | 需要额外基础设施，黑盒，难调试 | ❌ |
| 关键词匹配 | 简单 | 词面不重叠就找不到 | 部分用（FTS） |
| 文件 + FTS + LLM检索 | 透明可编辑，可观察=可信任 | 检索能力受限 | ✅ |

**可观察性 = 信任**：用户可以直接打开 `memory/YYYY-MM-DD.md` 看到 agent 记住了什么，这是产品设计的核心决策。

### 1.2 三层记忆架构

```
┌──────────────────────────────────────────────────────────┐
│  Layer 1：上下文窗口（Codex 原生）                          │
│  生命周期：当前 session，关闭即消失                          │
│  内容：最近对话 / 工具调用结果 / 当前轮决策                   │
│  访问：直接在 context 里，无需检索工具                       │
│  触发：→ 超过 20 轮 → Layer 2（Summarize）压缩                         │
│       → 话题结束信号 → Layer 4 归档                        │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  Layer 2：每日日志（memory/YYYY-MM-DD.md）                  │
│  生命周期：天到周，手动清理                                   │
│  内容：当天对话流水 / 决策记录 / 实体更新                     │
│  访问：memory_search.py 检索（Level 2/3）                  │
│  触发：→ 提炼 key_conclusions → 写入 MEMORY.md             │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  Layer 3：长期记忆（MEMORY.md，按域分块）                    │
│  生命周期：月到年，主动维护                                   │
│  内容：稳定偏好 / 重要结论 / 长期关注事项                     │
│  访问：session 启动时按域注入 + memory_search.py 检索        │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  Layer 3b：JSONL 索引（tools/artifacts/memory_entries.jsonl）│
│  内容：每条记忆的结构化元数据（域/实体/重要性/日期）             │
│  访问：memory_search.py 的底层数据源                         │
└──────────────────────────────────────────────────────────┘
```

### 1.3 域块设计与分域注入（token 节省 80% 的来源）

MEMORY.md 按专职代理的域分块，CTRL 按路由只注入必要的块：

```
(SYSTEM)    ← 所有代理都读（全局偏好）
[JOB]       ← 只在 JOB 路由时注入
[WORK]      ← 只在 WORK 路由时注入
[LEARN]     ← 只在 LEARN 路由时注入
[ENGINEER]  ← 只在 ENGINEER 路由时注入
[MONEY]     ← 只在 MONEY 路由时注入
[BRO/SIS]   ← BRO 和 SIS 共用
[META]      ← CTRL 跨域时注入
```

**注入规则**：

| 路由 | 注入内容 | 节省比例 |
|------|---------|---------|
| JOB | (SYSTEM) + [JOB] | ~80% |
| LEARN | (SYSTEM) + [LEARN] | ~80% |
| SEARCH | (SYSTEM) 只读 | ~90% |
| CTRL/跨域 | (SYSTEM) + [META] + 相关域 | ~60% |

**对比全量注入**：假设 MEMORY.md 共 10 个域块，每块 500 token，全量注入 5000 token，JOB 路由只注入 2 块约 1000 token，节省 80%。

### 1.4 四级 Route-Aware 检索

```
用户 query
    │
    ▼
Step 1：Query Rewrite（生成 2-3 个变体）
  变体1：原始 query
  变体2：+ domain hints（JOB 路由自动加 "job career offer interview"）
  变体3：实体提取版（公司名/技术词/项目名）
    │
    ▼
Step 2：Route-Aware Scope Filter（4 级递进）
  Level 1：当前 context（Codex 上下文窗口，无需工具调用）
           ↓ 不足时
  Level 2：同域 7 天内 → 结果 ≥ 2 且 top1 ≥ 0.3 则停止
           ↓ 不足时
  Level 3：同域全量   → 结果 ≥ 2 且 top1 ≥ 0.3 则停止
           ↓ 不足时
  Level 4：跨域兜底   → 结果标注 [跨域]
    │
    ▼
Step 3：FTS Scoring（BM25-like）
  基础分：token 词频重叠（TF-like）
  实体命中：+0.4 × 精确命中实体数    ← 最强信号
  重要性：  +0.05 × importance_score
  daily条目：+0.05（事实性更强）
  同域加分： +0.3
  跨域惩罚： -0.2
    │
    ├── FTS-only → Top-K
    │
    └── Hybrid（--hybrid，需 Ollama）
          nomic-embed-text（768维，M4本地推理，无GPU）
          → RRF fusion（FTS rank + embedding rank）
          → Top-K
```

**扩展条件设计**（为什么用绝对分数 0.3 而不是差值）：

差值判断（top1-top2 < 0.05）在低分区间极其敏感——两个分数都是 0.1 时差值也是 0，会频繁触发跨域扩展引入噪声。绝对分数（top1 < 0.3）更稳定。

### 1.5 重要性评分算法

```python
def estimate_importance(text: str) -> float:
    score = 0.5  # 基础分

    # 高重要性关键词 → +0.1 each（上限 1.0）
    high = ["决策", "结论", "P0", "重要", "关键",
            "offer", "面试", "上线", "已落地", "确认"]

    # 低重要性关键词 → -0.2 each（下限 0.1）
    low = ["待更新", "（待更新）", "TBD"]

    # 老化检测：importance < 0.4 且 >90天 → 标注 [stale]
```

### 1.6 实体提取（检索的核心加权信号）

```python
ENTITY_PATTERNS = [
    r"(?:美团|字节|阿里|腾讯|Shopee|longClaw)",  # 公司名
    r"(?:GRPO|PPO|SFT|LoRA|RAG|GNN|GAT|LLM|Codex)",  # 技术词
    r"[A-Z][a-z]+[A-Z]\w*",   # camelCase（如 longClaw）
    r"\d{4}-\d{2}-\d{2}",     # 日期
]
# 命中一个实体 → 检索分 +0.4
# 命中两个实体 → 检索分 +0.8
```

---

## 二、压缩机制：三层协作

### 2.1 全景图

```
对话进行中
    │
    ├── 每轮：CTRL 检查 round > 20？
    │     是 → Layer 2（Summarize）轻量摘要（静默）
    │
    ├── 话题结束信号：Layer 4 归档（主动写入 MEMORY.md，告知用户）
    │
    └── context 接近上限（200K tokens）：
          OpenClaw 原生 compaction（自动触发）
              └── PostCompact hook 重注入关键协议文件
```

### 2.2 OpenClaw 原生 Compaction（底层，不可控）

**触发**：context window 接近上限（200K tokens）

**保留 vs 丢失**：

| 内容 | 压缩后状态 | 原因 |
|------|-----------|------|
| 项目根目录 CLAUDE.md | ✅ 自动重注入 | OpenClaw 硬编码 |
| MEMORY.md（前200行/25KB） | ✅ 自动重注入 | OpenClaw 硬编码 |
| 已调用的 SKILL.md | ✅ 重注入（≤5K/个，总≤25K） | 最近调用优先 |
| CTRL_PROTOCOLS.md / DEV_LOG.md | ❌ 丢失 | → PostCompact hook 补救 |
| 对话历史 | ❌ 压缩为结构化摘要 | 保留意图/概念/错误/待办 |

**压缩效率**：58轮对话（~9600 tokens）→ 摘要（~1140 tokens），压缩率 88%

**PostCompact hook**（longClaw 的补救机制）：
```json
"PostCompact": [{
  "matcher": "auto",
  "hooks": [{"type": "command",
    "command": "cat CTRL_PROTOCOLS.md DEV_LOG.md >> \"$CLAUDE_ENV_FILE\""}]
}]
```

### 2.3 Layer 2：Summarize（轻量摘要）（longClaw 扩展）

**定位**：在原生 compaction 触发之前，提前做业务层摘要，减少噪声积累。

**触发**（满足任一，且原生 compaction 本轮未触发）：
- round > 20
- 单次工具输出 > 500 字符且与当前话题低相关

**摘要格式**：
```
[压缩摘要 2026-04-14 15:30]
目标：调研 Agent+OR 融合的最新进展
进展：已完成 arXiv 搜索（3篇）、GitHub 搜索（2个项目）
决策：重点关注 EoH 和 SIRL 两个方向
下一步：整理面试叙事
关键实体：EoH=2026-03（arxiv），SIRL=2025-11（arxiv）
```

**保护结构**：system prompt + 前 3 条 + 后 8 条不摘要，只摘要中间部分。

### 2.4 Layer 4：Archive（话题归档）（longClaw 扩展）

**定位**：不是 context 压缩，而是**跨 session 的知识沉淀**。

**触发**（满足任一）：
- 用户说"新话题" / "搞定了" / "好了就这样"
- CTRL 判断当前话题已有明确结论
- 用户连续 2 轮未追问上一话题（静默超时）

**执行**：
```
Step 1：提炼 key_conclusions（≤5条，每条一句话）
Step 2：提取关键实体（公司名/面试状态/学习内容等）
Step 3：写入 MEMORY.md 对应域
  [JOB]
  Shopee面试状态：二面通过，等HR（2026-04-14）
Step 4：告知用户"已将[话题]的结论保存到长期记忆"
```

### 2.5 三层对比

| | OpenClaw 原生（Layer 3） | Layer 2（Summarize） | Layer 4（Archive） |
|---|---|---|---|
| 触发 | context 接近上限 | round > 20 | 话题边界 |
| 可控性 | 不可控 | 可配置阈值 | 可配置触发词 |
| 写入位置 | 替换对话历史 | 替换冗长输出 | MEMORY.md |
| 对用户可见 | 静默 | 静默 | 告知用户 |
| 影响范围 | 当前 session | 当前 session | 所有未来 session |

**与 Claude Code 四层压缩的对应关系**：

```
Claude Code Layer 1（Tool Result Budgeting）← longClaw 待实现
Claude Code Layer 2（Snip Compacting）      ← longClaw Layer 2（Summarize）对应
Claude Code Layer 3（Microcompacting）      ← longClaw Layer 2（Summarize）部分覆盖
Claude Code Layer 4（Auto-compacting）      ← longClaw Layer 3（Compact，原生）对应
```

---

## 三、多模型协同：CTRL 仲裁 + Subagent 并发

### 3.1 整体架构

```
用户请求
    ↓
CTRL 控制平面（唯一对外出口）
    ├── 路由决策（语义关键词表 + 置信度）
    ├── 记忆检索（memory_search.py，4级）
    ├── Skill 检查（14个 skill，requires 依赖验证）
    ↓
路由分支：
    ├── 单专职（默认）：User→CTRL→[JOB]→CTRL→User
    ├── 双专职并行（跨域）：User→CTRL→([JOB]||[PARENT])→CTRL→User
    └── Subagent 编排（复杂任务）：spawn search/memory/heartbeat agent
    ↓
CTRL 仲裁输出
    ├── 置信度协议（≥0.8直接采纳，0.6-0.8标注不确定性，<0.6追问）
    ├── P0-P4 优先级裁决
    └── Risk Audit（策略/价值判断类问题）
```

### 3.2 置信度仲裁协议

```
每专家输出必须附：
[置信度: X.XX][依据: 数据/推断/经验]

CTRL 仲裁规则：
  ≥ 0.8  → 直接采纳
  0.6-0.8 → 采纳但标注不确定性："建议验证后执行"
  < 0.6  → 追问或标注"建议验证后执行"

冲突展示格式：
⚠️ [专家A] 和 [专家B] 在【X问题】上存在分歧
  → 专家A：<结论> [置信度: 0.85]
  → 专家B：<结论> [置信度: 0.72]
  → CTRL 倾向：<建议>
```

### 3.3 Subagent 并发架构

**角色 vs Subagent 的本质区别**：

```
角色（Specialist）：坐在桌前思考的顾问
  → 用户开口才响应
  → 串行执行
  → 继承主 session 工具权限
  → 跟随对话生命周期

Subagent：派出去干活的工人
  → CTRL 主动 spawn
  → 并发执行，独立 context window
  → 最小工具权限（只有完成任务所需）
  → 任务完成即退出
```

**三个 Subagent 的设计**：

```
search-agent（AI 搜索）
  model: inherit（继承主 session 的 Codex）
  tools: WebFetch / WebSearch / Read / Grep（只读+网络）
  职责：执行单一搜索任务，返回结构化证据
  触发：deep-research skill spawn×2-3

memory-agent（AI 陪伴）
  model: inherit
  tools: Read / Grep / Glob（只读）
  职责：BRO/SIS 路由时后台检索近期记忆
  触发：CTRL 路由到 BRO/SIS 时自动 spawn

heartbeat-agent（主动发现）
  model: inherit
  tools: Read / Glob / Grep / Write（只读+写state文件）
  职责：cron 定时巡检，P0/P1 事项写入 heartbeat-state.json
  触发：cron 08:30 / 18:00
```

### 3.4 并发搜索的 RRF 融合

```python
# Reciprocal Rank Fusion（倒数排名融合）
# 跨多个 agent 都排名靠前的文档，最终分数最高

for doc in all_results:
    rrf_score = 0
    for agent_rank_list in [agent_A_results, agent_B_results, agent_C_results]:
        if doc in agent_rank_list:
            rank = agent_rank_list.index(doc)
            rrf_score += 1 / (k + rank + 1)  # k=60，防止高排名过度主导

# 效果：三个 agent 都找到的文档分数最高，单 agent 找到的次之
```

**为什么不让每个 agent 直接输出总结**：
- 总结的总结 → 信息损耗叠加
- 结构化输出（URL + verbatim snippet + score）→ CTRL 可以做真正的融合

### 3.5 AI 陪伴：MemoryAgent 注入的并发设计

```
用户发消息
    ├── 主流程：CTRL 开始路由决策（~500ms）
    └── 后台：memory-agent 开始读 memory/ 文件（~200ms）

memory-agent 完成（通常比主流程快）
    ↓
注入上下文：
  "[背景] 近期情绪: 压力大 | 上次话题: Shopee面试 | 持续关注: 求职进展"
    ↓
BRO 回复时已经有背景，自然融入"上次聊到 Shopee 面试..."
```

**为什么后台并发而不是串行**：串行（先查记忆再回复）会让用户感受到延迟。后台 spawn 让 memory-agent 和主流程并发，用户感受不到额外延迟。

---

## 四、执行完整性与幻觉控制

### 4.1 Harness 工程的核心思想

```
❌ 靠 LLM 自觉：在 AGENTS.md 写"请用 trash 代替 rm"
                 → LLM 可能忘记，可能忽略

✅ Harness 层执行：PreToolUse hook 拦截 rm，自动改写为 trash
                   → 无论 LLM 说什么，实际执行的都是 trash
```

这是从 Claude Code sourcemap 逆向分析中借鉴的核心设计原则：**规则在基础设施层执行，不依赖模型自觉**。

### 4.2 三层权限模型（Deny > Ask > Allow）

```
Deny（永久禁止，优先于所有 hook）
  ├── 私有数据外发（USER.md / MEMORY.md / API keys）
  ├── git push --force 到 main/master
  ├── 无指令修改 AGENTS.md / SOUL.md
  ├── 破坏性命令（rm -rf 等）
  └── 伪造执行证据

Ask（每次单独授权）
  ├── 文件写入
  ├── git commit / git push
  └── 出站消息

Allow（默认）
  ├── 本地只读、内存检索
  └── 预授权的公开网页只读抓取
```

**关键设计**：Deny 规则在 hook 之前生效——即使 hook 返回 allow，Deny 规则也会阻断。

### 4.3 6 条 Immutable Rules

这 6 条规则不能被任何 skill、用户指令或 session 状态覆盖：

1. **无合成证据**：禁止伪造工具输出、文件内容或执行结果
2. **无静默 AGENTS.md 修改**：修改此文件必须有同轮显式用户指令
3. **禁止 force-push main/master**：即使用户要求也要警告并停止
4. **Deny > Ask > Allow 优先级固定**：不可逆转
5. **SOUL.md 对所有专职生效**：任何 skill 或角色不可覆盖人格约束
6. **DEV LOG 每轮必须输出**：不可被 skill 执行或输出长度抑制

### 4.4 Anti-Stall 规则（解决空转问题）

```
❌ 空转（禁止）：
  "我现在去做 Step 1"  → 然后停住等用户
  "准备执行"           → 没有任何工具调用
  "已开始处理"         → 无执行证据

✅ 正确行为：
  doing: <action>  → 仅当同轮已发起工具调用
  blocked: <reason> → 缺权限/缺输入时直接说
  need_authorization: <action> → 需要用户确认时直接说
```

**根因**：`doing:` 的条件是"同轮已发起工具调用"，而不是"打算发起"——这是 harness 层的语义约束，不是 prompt 层的建议。

### 4.5 PostToolUse 注入（DEV LOG 可观测性）

借鉴 Claude Code 的 PostToolUse 机制：

```
工具调用完成
    ↓
PostToolUse hook 触发
    ↓
结果摘要注入 DEV LOG 的 🛠️ 工具字段

示例：
🛠️ 工具 Edit(AGENTS.md) → 插入 Immutable Rules 节，+18行 | status=ok
🛠️ 工具 Bash(git commit) → hash=f951b9a | status=ok
🛠️ 工具 WebFetch(arxiv.org) → 403 blocked | status=blocked(missing_tool)
```

**与靠 LLM 自述的区别**：
- LLM 自述：可能不准确，可能遗漏，可能夸大
- PostToolUse 注入：来自 runtime-produced 字段，不可伪造

---

## 五、Coding Agent：repo-explorer + code-agent

### 5.1 当前 ENGINEER 角色的瓶颈

```
当前（角色模式）：
  用户："帮我修这个 bug"
      ↓
  ENGINEER 专职
      → 分析问题（但不知道代码在哪里）
      → 给出修改建议
      → 用户自己去改

目标（Coding Agent 模式）：
  用户："帮我修这个 bug"
      ↓
  code-agent skill
      → repo-explorer 自主探索 codebase（spawn subagent）
      → 制定修改计划（用户确认）
      → 自主执行修改
      → 运行测试验证
      → 失败自动换路（最多 2 次）
      → 交付可验证的 diff
```

### 5.2 repo-explorer：Codebase 理解 Subagent

```
输入：问题描述 / 修改目标
    ↓
Step 1：结构扫描
  find . -type f -name "*.py" | head -60
  识别项目类型 / 主要目录 / 入口文件

Step 2：关键词定位
  grep -rn "<关键词>" --include="*.py" -l

Step 3：深度读取（最多10个文件）
  读取完整内容（小文件）或关键段落（大文件，≤30行/文件）

Step 4：依赖追踪
  追踪 import/require 关系（最多 2 跳）

Step 5：输出结构化文件地图
  1. <文件路径> [核心]
     - 作用：一句话
     - 关键代码：<片段>
     - 依赖：<import关系>
     - 被依赖：<反向依赖>
  修改建议入口：<文件:行号>
  风险点：<副作用>
```

**为什么用 subagent 而不是让 ENGINEER 直接探索**：
- 探索过程产生大量中间结果（文件列表、grep 输出），用 subagent 隔离后不污染主 context
- 结构化输出让 ENGINEER 直接"消费"，不需要再次理解

**借鉴 SWE-agent 的 ACI 设计**：
- 每次读文件不超过 100 行，用 grep 定位后再精确读取
- 输出格式结构化，不是原始 shell 输出

### 5.3 code-agent skill 工作流

```
Step 1：spawn repo-explorer → 获取文件地图
Step 2：制定修改计划 → 等用户确认
        （关键：不自行扩大范围，计划外的文件不动）
Step 3：执行修改 → 每文件改完立即 readback 验证
Step 4：运行测试 → 最多重试 2 次
Step 5：交付报告（改了什么 / 验证结果 / 如何回滚）
```

**换路策略**（借鉴 research-execution-protocol）：
```
第 1 次失败 → 检查是否测试本身的问题
第 2 次失败 → 缩小修改范围，只保留最核心改动
第 3 次失败 → 停止，报告 blocked: 需要人工介入
```

**与其他 skills 的关系**：
```
code-agent（编排层）
    ├── 探索阶段 → repo-explorer（subagent）
    ├── 排障阶段 → research-execution-protocol（优先级更高）
    └── 审查阶段 → agent-review（workspace 配置审查）
```

### 5.4 下一步迭代路径

| 里程碑 | 目标 | 验证方式 |
|--------|------|---------|
| M1（已完成）| repo-explorer + code-agent 基础版 | 能自主探索 longClaw 自身 codebase 并修改 |
| M2（2周）| repo-map 工具（tree-sitter）| 生成 500 token 内的代码地图 |
| M3（4周）| git worktree 隔离 | code-agent 任务在独立分支，失败可安全丢弃 |
| M4（6周）| openclaw_substrate 评估接入 | 能跑 SWE-bench-lite，有 resolved rate 数据 |

---

## 六、训练底座：Trace → Judge → Dataset

### 6.1 设计目标

```
真实对话交互
    ↓
Trace 收集（openclaw_substrate/trace_plane.py）
  记录：请求/响应/路由/工具调用/重试
    ↓
Judge 评分（openclaw_substrate/judge_plane.py）
  规则评价 + LLM Judge
  输出奖励信号
    ↓
Dataset 构建（openclaw_substrate/dataset_builder.py）
  SFT 数据集 / GRPO 偏好对
    ↓
本地训练（backends/）
  MLX-LM（Mac mini M4，Apple Silicon，无需 GPU）
  LLaMA-Factory（导出 YAML，可迁移到 A100/H100）
    ↓
Shadow Eval（openclaw_substrate/shadow_eval.py）
  baseline vs candidate 回放对比
```

### 6.2 与美团 SFT+GRPO 实践的关联

这个训练底座的设计直接借鉴了美团换电诊断 Agent 的训练经验：

| 美团实践 | longClaw 训练底座 |
|---------|-----------------|
| LLaMA-Factory + LoRA SFT | LLaMA-Factory backend 导出 YAML |
| 三层 Dense Reward（格式/工具路径/证据引用） | judge_plane.py 规则评价 + 奖励信号 |
| VeRL GRPO 训练 | dataset_builder.py 构建偏好对 |
| 工具路径匹配率 60%+ | shadow_eval.py 回放对比 |

---

## 七、系统设计决策总结（面试用）

### 7.1 五个关键决策及其权衡

**决策 1：文件记忆 vs 向量数据库**
- 选择：Markdown 文件 + FTS + Hybrid Embedding
- 理由：透明度 = 信任；可直接编辑；无需额外基础设施
- 代价：检索语义理解能力受限（FTS 词面不重叠就找不到）
- 缓解：Hybrid 模式（Ollama nomic-embed-text + RRF fusion）

**决策 2：按域注入 vs 全量注入**
- 选择：按路由域精准注入
- 理由：节省 80% token，避免历史噪声污染当前请求
- 代价：跨域信息可能遗漏
- 缓解：Level 4 跨域兜底检索

**决策 3：Harness 层规则 vs Prompt 层建议**
- 选择：Harness 层（hook + Immutable Rules）
- 理由：LLM 会忘记 prompt 里的规则，harness 层不会
- 代价：灵活性降低，某些边界情况需要手动处理
- 缓解：Deny/Ask/Allow 三层，只有 Deny 是绝对的

**决策 4：Subagent 并发 vs 串行角色**
- 选择：对搜索/记忆/巡检任务用 Subagent
- 理由：并发节省时间；最小权限隔离更安全；独立 context 不污染主对话
- 代价：模型只支持 Claude（inherit），不支持 Codex
- 缓解：model: inherit，继承主 session 的 Codex

**决策 5：压缩三层协作 vs 单一策略**
- 选择：原生 compaction + Layer 2（Summarize，token压力）+ Layer 4（Archive，话题边界）
- 理由：不同触发条件解决不同问题，层层递进
- 代价：配置复杂，三层之间的优先级需要明确
- 缓解：原生 compaction 优先，Layer 2 跳过，Layer 4 独立触发

### 7.2 与 Claude Code 内部设计的对应

| Claude Code 设计 | longClaw 实现 | 差距/下一步 |
|-----------------|--------------|-----------|
| 4-Layer Compression | Layer 1（Trim）+ Layer 2（Summarize）+ Layer 3（Compact）+ Layer 4（Archive） | 已补 Layer 1（Trim，工具输出实时截断） |
| LLM 侧查询记忆检索 | FTS + Hybrid Embedding | 升级方向：用 Codex 做语义检索 |
| Fork Agent 缓存共享 | 无 | A2A 并行可引入，节省 90% token |
| Speculative Execution | 无 | code-agent 工具并发可引入 |
| Hook Config Snapshots | settings.json 静态配置 | 已部分实现 |

---

## 八、关键数字速查（面试时的量化锚点）

| 指标 | 数值 | 来源 |
|------|------|------|
| 分域注入 token 节省 | ~80% | MEMORY.md 10域块，每次只注入1-2个 |
| 原生 compaction 压缩率 | ~88% | 9600 tokens → 1140 tokens |
| 检索扩展阈值 | top1 < 0.3 | 绝对分数，避免差值过敏感 |
| 实体命中加分 | +0.4 × N | N=命中实体数 |
| Layer 2 触发阈值 | round > 20 | session-state.json 追踪 |
| Subagent 并发上限 | 3（deep-research） | OpenClaw 并行限制 |
| code-agent 重试上限 | 2次 | 第3次停止报告 blocked |
| SWE-bench-lite 目标 | resolved rate > baseline | M4 里程碑 |
| Skill 总数 | 14个 | CTRL_PROTOCOLS.md skill index |
| 专职代理数 | 10个 | MULTI_AGENTS.md |

---

## 九、参考资料

### 核心文档（本 repo）

```
docs/memory-compression-guide.md      ← 记忆与压缩机制详解（556行）
docs/subagent-harness-learning-guide.md ← Subagent & Harness 改造（499行）
docs/claude-code-internals.md         ← Claude Code 内部架构解析（408行）
docs/coding-agent-learning-plan.md    ← Coding Agent 学习计划（402行）
```

### 外部参考

- **Claude Code 架构书**：https://github.com/alejandrobalderas/claude-code-from-source
- **SWE-agent 论文**：https://arxiv.org/abs/2405.15793
- **Aider repo-map**：https://aider.chat/docs/repomap.html
- **Agentless 论文**：https://arxiv.org/abs/2407.01489
- **SWE-bench**：https://arxiv.org/abs/2310.06770

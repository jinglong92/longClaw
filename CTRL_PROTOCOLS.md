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

## Context Compression（双层）

OpenClaw 原生 compaction 优先。若原生已在本轮触发，Layer A 跳过，只执行 Layer B。

### Layer A：轻量摘要（token 压力驱动，静默）

**触发**（满足任一，且原生 compaction 未触发）：
- 对话轮数 > 20
- 单次工具输出 > 500 字符且与当前话题低相关

**执行**：
- 生成压缩摘要块替换冗长输出，保留关键结论
- 保护：system prompt + 前 3 条 + 后 8 条不摘要
- 摘要格式：`目标 / 进展 / 决策 / 下一步 / 关键实体（字段名：值（日期））`
- 写入 session-state.json：`compression_count += 1`，`last_compression_at = <ISO>`
- DEV LOG 显示：压缩原因 / 累计次数 / 级别
- 失败时退化为最小裁剪，不得声称"已完成压缩"

### Layer B：话题归档（话题边界驱动，主动）

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
建议路径：skills/<role>/<workflow-name>/SKILL.md
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

## Session 状态管理

session_id 命名：`openclaw_{domain}_{YYYY-MM-DD}`（如 `openclaw_job_2026-04-14`）

三层状态：
- Layer 1（短期）：recent_turns，超 20 轮触发 Layer A 压缩
- Layer 2（中期）：summary + entities，LLM 摘要 + 关键实体
- Layer 3（长期）：key_conclusions，写入 MEMORY.md，跨 session 可检索

跨 session 检索：
- 专家级别：只在同类型 session 里检索（JOB 专家只搜 session_job_*）
- CTRL 级别：在所有 session 里检索

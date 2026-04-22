---
name: deep-research
description: 并发多源深度调研——把复杂问题拆解为多个并发 SearchAgent，各自独立搜索后由 CTRL 汇总，输出带来源的综合报告。适合需要多角度、多来源的复杂调研任务。
version: 1.0.0
author: jinglong92
license: MIT
requires: ["web_fetch"]
---

# Deep Research

把复杂调研问题拆解为并发 SearchAgent，多路搜索后汇总。

## 触发条件

**硬触发关键词（出现任一即命中，无需语义判断）**：
- "深度调研" / "deep research" / "深研"
- "多个来源" / "多来源" / "多角度"
- "全面了解" / "系统调研" / "综合调研"
- "帮我搜几个" / "多搜几个地方"
- 用户发 `/deep` 命令

**软触发（CTRL 判断）**：
- 问题涉及 2 个以上维度（技术 + 行业 + 招聘 等）
- 用户对 fact-check-latest 的结果不满意，要求扩展

## 不触发条件
- 简单事实查询（用 fact-check-latest）
- 只需要一个原文片段（用 public-evidence-fetch）
- 问题只有一个明确维度

---

## 执行流程

### Step 1：问题拆解
将用户问题拆解为 2-3 个独立搜索任务，每个任务：
- 有明确的搜索目标
- 可以独立执行（不依赖其他任务结果）
- 覆盖不同维度（如：学术/行业/实践）

输出拆解结果给用户确认（1句话/任务），不等确认直接进入 Step 2。

### Step 2：并发 spawn SearchAgent
为每个搜索任务 spawn 一个 `search-agent`：

```
Agent(search-agent): 任务A — <具体搜索指令>
Agent(search-agent): 任务B — <具体搜索指令>
Agent(search-agent): 任务C — <具体搜索指令>（如有）
```

每个 agent 独立执行，最多并发 3 个。

### Step 3：结果汇总（RRF 融合）
收集所有 SearchAgent 返回的结构化证据，按以下方式融合：

1. **去重**：相同 URL 或高度重复内容只保留一条
2. **相关性排序**：按各 agent 返回的相关性分数排序
3. **冲突标注**：不同来源有矛盾时，显式标注 `⚠️ 来源冲突`
4. **缺失标注**：某个维度无结果时，标注 `[该维度无有效来源]`

### Step 4：输出综合报告

```
## 深度调研报告：<主题>
调研时间：<YYYY-MM-DD HH:MM>
覆盖维度：<A> / <B> / <C>

### <维度A>
[F] <确定信息>（来源：<URL>）
[I] <推断信息>（来源：<URL>，置信度：X%）

### <维度B>
...

### 综合结论
<2-3句话的核心结论>

### 来源列表
1. <URL> — <简要说明>
2. ...

时效说明：<检索时间，信息有效期估计>
```

## DEV LOG 约定
```
🧩 Skill deep-research | step=<N/4> | agents=<spawned_count>
🛠️ 工具 Agent(search-agent×<N>) → 召回<M>条有效来源 | status=ok
```

## 边界
- 最多并发 3 个 SearchAgent（OpenClaw 并行上限）
- 单个 agent 超时（>60s）时跳过该维度，标注 `[超时，跳过]`
- 所有 agent 都失败时，降级为单路 fact-check-latest

---

## Project Writeback Contract

**触发条件**：MEMORY.md 存在 `[PROJECT]` 块，且当前调研与项目 `goal` 相关。

**Step 5（在综合报告输出后执行）**：

将调研结果写回 project memory，格式如下：

```yaml
project_writeback:
  project_id: <从 [PROJECT] 块读取>
  research_topic: <本次调研主题>
  summary: <2-3句话的核心结论>
  key_findings:
    - <发现1>
    - <发现2>
    - <发现3>（最多5条）
  uncertainties:
    - <尚不确定的点>（如有）
  next_actions:
    - <基于调研结论，建议的下一步>
  sources:
    - <URL1>
    - <URL2>
  written_at: <YYYY-MM-DD HH:MM>
```

**写回目标**（双路径）：

1. **MEMORY.md [PROJECT] 块**：更新 `current_focus` 为调研结论摘要，`next_action` 为建议的下一步。
2. **memory/YYYY-MM-DD.md**：追加一条 `[research_writeback]` 条目，包含完整 `project_writeback` 内容。

**写回规则**：
- 写回内容是高密度摘要，不是原文全量
- 若用户明确说"不用写回"，跳过此步骤
- 写回后在报告末尾追加一行：`✅ 已写回 project memory（project: <project_id>）`
- 若无 [PROJECT] 块，跳过此步骤，不提示

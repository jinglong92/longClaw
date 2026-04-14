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
- 用户说"帮我深度调研" / "全面了解一下" / "多角度分析"
- 问题涉及多个维度（如：技术进展 + 行业动态 + 招聘趋势）
- 用户明确要求"多个来源" / "不要只搜一个地方"
- 单次 fact-check-latest 或 public-evidence-fetch 明显不够用

## 不触发条件
- 简单事实查询（用 fact-check-latest）
- 只需要一个原文片段（用 public-evidence-fetch）

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

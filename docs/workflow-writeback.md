# Workflow Writeback — 调研和代码任务的结果写回机制

Workflow writeback 是让每次 research / coding 任务的结果自动持久化到 project memory 的机制。

---

## 为什么需要 writeback

没有 writeback 时：
- 调研结果只存在于当前 session context
- 下次开新 session，需要重新解释背景
- AI 不知道上次做到哪里、验证结果是什么

有了 writeback：
- 每次任务完成后，关键结论自动写入 project memory
- 下次 session，CTRL 读取 [PROJECT] 块，直接恢复上下文
- 不需要重新解释背景

---

## 两种 writeback

### 1. Research Writeback（`search-deep-research` skill）

**触发条件**：deep-research 任务完成 + MEMORY.md 有 [PROJECT] 块

**写回内容**：

```yaml
project_writeback:
  project_id: <project_id>
  research_topic: <调研主题>
  summary: <2-3句话的核心结论>
  key_findings:
    - <发现1>
    - <发现2>
  uncertainties:
    - <尚不确定的点>
  next_actions:
    - <建议的下一步>
  sources:
    - <URL1>
  written_at: <时间>
```

**写回目标**：
1. MEMORY.md [PROJECT] 块：更新 `current_focus` + `next_action`
2. `memory/YYYY-MM-DD.md`：追加 `[research_writeback]` 条目
3. SQLite `project_events`：记录事件

### 2. Code Writeback（`engineer-code-agent` skill）

**触发条件**：code-agent 任务完成（Step 5）+ MEMORY.md 有 [PROJECT] 块

**写回内容**：

```yaml
project_writeback:
  project_id: <project_id>
  task_goal: <任务目标>
  files_touched:
    - <文件路径>: <改动描述>
  validation_result: passed | partial | failed
  validation_detail: <测试命令 + 结果>
  open_risks:
    - <遗留风险>
  next_actions:
    - <建议的下一步>
  written_at: <时间>
```

**写回目标**：同上（三路径）

---

## 写回规则

| 规则 | 说明 |
|------|------|
| 摘要优先 | 写回内容是高密度摘要，不是原文全量 |
| 如实反映 | `validation_result` 必须如实，不得在失败时写 passed |
| 可选退出 | 用户说"不用写回"时跳过 |
| 无项目时静默 | 无 [PROJECT] 块时跳过，不提示 |
| 写回确认 | 写回后在输出末尾追加 `✅ 已写回 project memory（project: <id>）` |

---

## 验证链路

运行 demo 验证完整链路：

```bash
# Research writeback demo
python3 docs/demo_research.py --round 1
python3 docs/demo_research.py --round 2

# Coding writeback demo
python3 docs/demo_coding.py --round 1
python3 docs/demo_coding.py --round 2

# 查看 project 状态
scripts/longclaw-status
```

---

## 存储位置汇总

| 存储 | 路径 | 内容 |
|------|------|------|
| MEMORY.md | `MEMORY.md` | [PROJECT] 块，current_focus + next_action |
| 日记 | `memory/YYYY-MM-DD.md` | [research_writeback] / [code_writeback] 条目 |
| JSON store | `memory/projects.json` | Project 对象全量 |
| SQLite | `memory/state.db` | project_events 表，事件日志 |

---

## 与 CTRL 的关系

CTRL 在每轮组装上下文时：

1. 读取 MEMORY.md [PROJECT] 块（如有）
2. 将 `goal` / `current_focus` / `next_action` 注入执行上下文
3. research / coding skill 完成后触发 writeback
4. writeback 更新 [PROJECT] 块，下次 session 可恢复

这形成了一个闭环：**任务 → 执行 → 写回 → 下次恢复**。

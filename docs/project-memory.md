# Project Memory — 设计与使用指南

longClaw 的 project memory 是让 AI 记住"你在推进什么项目"的核心机制。

---

## 它是什么

Project memory 是一个轻量的持久化层，存储当前项目的：

- **目标**（goal）：这个项目要达成什么
- **当前焦点**（current_focus）：现在在做什么
- **下一步**（next_action）：接下来该干什么
- **状态**（status）：active / paused / completed / archived

每次 research 或 coding 任务完成后，结果自动写回这个 project context，下次 session 可以直接恢复。

---

## 存储层

Project memory 有两个存储路径，互为补充：

### 1. MEMORY.md [PROJECT] 块（人类可读）

```
[PROJECT]
id: longclaw-productization
name: longClaw 产品化
goal: turn longClaw into a project-based AI workspace for technical users
current_focus: project-aware memory writeback
next_action: connect deep-research writeback to project store
status: active
constraints:
- keep architecture minimal
- no new CLI entry except init/doctor/status
[/PROJECT]
```

**特点**：
- 人类可直接编辑
- CTRL 每轮优先读取，注入执行上下文
- 同一时间只保留一个活跃 [PROJECT] 块

### 2. memory/projects.json（机器写入）

JSON 文件，由 `core/project/project_store.py` 管理。Skill writeback 自动更新。

```json
{
  "longclaw-productization": {
    "project_id": "longclaw-productization",
    "name": "longClaw 产品化",
    "goal": "...",
    "current_focus": "...",
    "next_action": "...",
    "status": "active",
    "updated_at": "2026-04-22T07:00:00Z"
  }
}
```

### 3. memory/state.db（SQLite，跨 session 事件日志）

存储 `projects` 表和 `project_events` 表，记录每次 writeback 事件。

```sql
-- 每次 research/coding 完成后自动写入
INSERT INTO project_events (project_id, event_type, summary, payload_json) ...
```

---

## 如何使用

### 创建项目

编辑 `MEMORY.md`，在末尾加 [PROJECT] 块（参考 MEMORY.md.example 的模板）。

或者通过 Python：

```python
from core.project.project_schema import Project
from core.project.project_store import ProjectStore

store = ProjectStore()
p = Project(
    project_id="my-project",
    name="我的项目",
    goal="...",
    current_focus="...",
    next_action="...",
)
store.save(p)
```

### 查看项目状态

```bash
scripts/longclaw-status
```

输出：

```
┌─ PROJECT ─────────────────────────────────────────────
│  🟢 [active]  longClaw 产品化  (longclaw-productization)
│  Goal:    turn longClaw into a project-based AI workspace
│  Focus:   project-aware memory writeback
│  Next:    connect deep-research writeback to project store
└───────────────────────────────────────────────────────
```

### 触发 writeback

在 longClaw 对话中触发 `search-deep-research` 或 `engineer-code-agent` skill，任务完成后自动写回（前提：MEMORY.md 有 [PROJECT] 块）。

---

## 生命周期

```
创建项目
  → 设置 goal + current_focus + next_action
  → status: active

推进中（每次 research/coding 后）
  → 自动更新 current_focus + next_action
  → project_events 记录每次事件

项目完成
  → 把 status 改为 completed
  → 把 [PROJECT] 块内容迁移到 MEMORY.md [META] 做归档

归档
  → status: archived
  → 从 [PROJECT] 块移除
```

---

## 设计原则

- **最小化**：只存 current_focus + next_action + status，不做复杂 task 对象
- **双路径**：人类可编辑（MEMORY.md）+ 机器写入（JSON/SQLite），互为补充
- **不强制**：无 [PROJECT] 块时，系统按普通 session 处理，不报错

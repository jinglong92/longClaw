---
name: memory-companion
description: 记忆增强陪伴——BRO/SIS 回复前自动 spawn MemoryAgent 检索近期记忆，让陪伴有"记得你"的感觉。无需用户触发，CTRL 路由到 BRO/SIS 时自动激活。
version: 1.0.0
author: jinglong92
license: MIT
requires: ["file_read"]
---

# Memory Companion

BRO/SIS 路由时自动注入近期记忆上下文，让陪伴不再是无状态的。

## 触发条件（自动，无需用户说）
- CTRL 路由到 `BRO` 专职时，自动触发
- CTRL 路由到 `SIS` 专职时，自动触发
- 用户表现出情绪信号（吐槽/压力/兴奋/低落）时，无论路由到哪个专职都触发

## 执行流程

### Step 1：spawn MemoryAgent（后台，不打断主流程）
```
Agent(memory-agent): 检索近 3 天记忆，提取情绪状态和关注点
```

MemoryAgent 在后台执行，主流程继续路由到 BRO/SIS。

### Step 2：注入上下文
MemoryAgent 返回结果后，CTRL 将 `[MemoryAgent 注入]` 块插入 BRO/SIS 的上下文前缀：

```
[背景] 近期情绪: <状态> | 上次话题: <话题> | 持续关注: <事项>
```

BRO/SIS 基于这个背景回复，而不是从零开始。

### Step 3：BRO/SIS 回复
BRO/SIS 用注入的记忆上下文生成回复，自然融入"我记得你上次说..."的表达。

### Step 4：话题归档（Layer B 触发时）
陪伴对话结束时，将本次情绪状态和话题写入 `MEMORY.md [BRO/SIS]` 块：
```
情绪状态：<状态>（<YYYY-MM-DD>）
话题：<话题名>（<YYYY-MM-DD>）
```

## MemoryAgent 返回为空时的处理
- 正常路由到 BRO/SIS，不注入任何背景
- 不向用户说明"没有记忆"（保持自然）

## DEV LOG 约定
```
🧩 Skill memory-companion | trigger=BRO/SIS路由 | step=completed
🛠️ 工具 Agent(memory-agent) → 近期情绪=<状态> 上次话题=<话题> | status=ok
```

## 边界
- MemoryAgent 只读，不写入
- 注入内容不暴露原始日志给用户
- 超时（>10s）时静默跳过，BRO/SIS 正常回复
- 不用于 JOB/WORK/ENGINEER 等任务型专职（只限陪伴场景）

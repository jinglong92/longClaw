---
name: session-compression-flow
description: Trigger and execute session compression plus post-compression handoff for next-session continuity. Use when user asks to compress long conversations, enforce compression thresholds, or standardize how compressed summaries are written into daily memory and MEMORY.md for later recall.
requires: ["file_write"]
---

# Session Compression Flow

将“触发压缩 + 压缩落盘 + 新会话衔接”固化为标准流程。

## 执行入口

当满足任一条件时执行：
- 用户明确要求”压缩/总结当前会话”
- CTRL 在更新 session-state.json 时检测到 `round > 20`（每轮写入后主动检查，不等用户提醒）
- 工具输出冗长且低相关，影响上下文质量

**CTRL 自动检查规则**：每轮写入 session-state.json 后，若 `round > 20` 且 `compression_count` 未在本轮递增，则自动触发本 skill（Layer A 压缩）。不需要用户说”压缩”。

## 流程

1. 识别压缩触发原因
- 标注触发类型：`round-threshold` / `long-tool-output` / `manual-request`

2. 生成压缩摘要块
- 使用固定格式：
  - 目标
  - 进展
  - 决策
  - 下一步
  - 关键实体（字段名：值（日期））

3. 压缩落盘（双写）
- 写入 `memory/YYYY-MM-DD.md`（作为当日流水）
- 将关键“决策/实体”写入 `MEMORY.md` 对应域（长期记忆）

4. 检索索引更新
- 执行：`python3 tools/memory_entry.py --rebuild`
- 确保压缩后信息在检索层可见

5. 新会话衔接
- 新会话先按路由域注入 `MEMORY.md` 对应域
- 必要时调用检索拿最近压缩摘要（优先同域）

## 输出约定

每次执行后在回复中给出：
- 压缩是否执行（是/否）
- 触发原因
- 落盘位置（daily + MEMORY 域）
- 索引是否重建成功

## DEV LOG 约定

在 DEV LOG 中追加：
- 压缩原因
- 压缩次数累计
- 压缩级别（Layer A / Layer B）
- 是否完成“落盘 + 重建索引”

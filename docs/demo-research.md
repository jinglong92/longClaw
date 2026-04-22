# Demo: Project-Aware Research

这个 demo 展示 longClaw 的核心差异：**调研结果跨 session 可追溯，第二轮能承接第一轮**。

## 场景

你在研究 vLLM 的 continuous batching 实现。第一轮调研完，下次开新 session 还能直接接上。

---

## 运行方式

```bash
# 确保在 longClaw 目录
cd /path/to/longClaw

# 第一轮：模拟 deep-research 并写回 project memory
python3 docs/demo_research.py --round 1

# 第二轮：模拟新 session 恢复项目上下文，继续追问
python3 docs/demo_research.py --round 2
```

---

## 演示脚本

见 `docs/demo_research.py`。

---

## 关键链路

```
Round 1:
  用户提问 → deep-research skill 触发
  → 并发 SearchAgent×3（模拟）
  → 汇总结果
  → project_writeback 写回 MEMORY.md [PROJECT] + memory/YYYY-MM-DD.md
  → ✅ 已写回 project memory

Round 2（新 session）:
  CTRL 读取 MEMORY.md [PROJECT] 块
  → 恢复 current_focus + next_action
  → 用户追问时，直接引用上次 key_findings
  → 不需要重新解释背景
```

---

## 验证标准

- Round 1 完成后，`scripts/longclaw-status` 显示更新后的 `current_focus` 和 `next_action`
- Round 2 开始时，CTRL 能说出"上次调研发现了 X，你想继续哪个方向？"
- `memory/YYYY-MM-DD.md` 包含 `[research_writeback]` 条目

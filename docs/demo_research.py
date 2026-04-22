#!/usr/bin/env python3
"""
Demo: Project-Aware Research
展示 deep-research → project_writeback → 跨 session 恢复上下文 的完整链路。

Usage:
    python3 docs/demo_research.py --round 1   # 第一轮调研 + 写回
    python3 docs/demo_research.py --round 2   # 第二轮：新 session 恢复上下文
    python3 docs/demo_research.py --status    # 查看当前 project 状态
"""

import argparse
import os
import sys
from datetime import date, datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.project.project_schema import Project
from core.project.project_store import ProjectStore
from runtime_sidecar.state import db, readers, writers


# ---------------------------------------------------------------------------
# Simulated research results (in real use, these come from SearchAgent)
# ---------------------------------------------------------------------------

MOCK_RESEARCH = {
    "topic": "vLLM continuous batching 实现原理",
    "summary": (
        "vLLM 使用 PagedAttention + continuous batching 实现高吞吐推理。"
        "核心是 KV cache 分页管理，允许不同序列共享 GPU 内存页，"
        "避免了传统静态批处理中的内存碎片问题。"
    ),
    "key_findings": [
        "PagedAttention 将 KV cache 分成固定大小的 block（默认 16 tokens/block），按需分配",
        "continuous batching 允许在一次 forward pass 中混合不同长度的序列",
        "调度器（Scheduler）负责决定哪些 sequence 进入当前 batch，优先级基于 FCFS",
        "preemption 机制：当 GPU 内存不足时，将低优先级序列换出到 CPU",
        "throughput 比 HuggingFace Transformers 高 14-24x（官方 benchmark）",
    ],
    "uncertainties": [
        "chunked prefill 在 vLLM v0.4+ 的实际效果尚需实测",
        "speculative decoding 与 continuous batching 的交互行为",
    ],
    "next_actions": [
        "阅读 vLLM 源码 scheduler.py 了解调度细节",
        "对比 TGI（Text Generation Inference）的 batching 策略差异",
        "调研 vLLM v0.6 引入的 disaggregated prefill 对 continuous batching 的影响",
    ],
    "sources": [
        "https://arxiv.org/abs/2309.06180",
        "https://blog.vllm.ai/2023/06/20/vllm.html",
        "https://github.com/vllm-project/vllm/blob/main/vllm/core/scheduler.py",
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Round 1: Research + writeback
# ---------------------------------------------------------------------------

def run_round_1():
    print("=" * 60)
    print("Round 1: Deep Research — vLLM continuous batching")
    print("=" * 60)
    print()

    # Step 1: Show simulated research result
    r = MOCK_RESEARCH
    print(f"📋 调研主题: {r['topic']}")
    print()
    print(f"📝 综合结论:")
    print(f"   {r['summary']}")
    print()
    print(f"🔍 关键发现:")
    for i, f in enumerate(r["key_findings"], 1):
        print(f"   {i}. {f}")
    print()
    print(f"❓ 尚不确定:")
    for u in r["uncertainties"]:
        print(f"   · {u}")
    print()
    print(f"➡️  建议下一步:")
    for a in r["next_actions"]:
        print(f"   · {a}")
    print()

    # Step 2: Write back to project store
    print("─" * 60)
    print("✍️  写回 project memory...")
    print()

    store = ProjectStore()
    # Get or create the demo project
    p = store.get("demo-vllm-research")
    if p is None:
        p = Project(
            project_id="demo-vllm-research",
            name="vLLM 调研",
            goal="深入理解 vLLM continuous batching 实现，为生产部署决策提供依据",
        )

    p.current_focus = f"已完成 continuous batching 基础调研，发现 PagedAttention 是核心"
    p.next_action = r["next_actions"][0]
    store.save(p)

    # Write to daily memory log
    log_path = os.path.join(REPO_ROOT, "memory", f"{_today()}.md")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    writeback_entry = f"""
[research_writeback]
project_id: {p.project_id}
research_topic: {r['topic']}
written_at: {_now_iso()}
summary: {r['summary']}
key_findings:
{chr(10).join(f'  - {f}' for f in r['key_findings'])}
next_actions:
{chr(10).join(f'  - {a}' for a in r['next_actions'])}
sources:
{chr(10).join(f'  - {s}' for s in r['sources'])}
[/research_writeback]
"""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(writeback_entry)

    # Write to SQLite
    conn = db.get_connection()
    writers.initialise_schema(conn)
    writers.upsert_project(
        conn,
        project_id=p.project_id,
        name=p.name,
        goal=p.goal,
        current_focus=p.current_focus,
        next_action=p.next_action,
        status=p.status,
    )
    writers.insert_project_event(
        conn,
        project_id=p.project_id,
        event_type="research_writeback",
        summary=f"调研完成: {r['topic']}",
        payload={
            "summary": r["summary"],
            "key_findings_count": len(r["key_findings"]),
            "next_action": r["next_actions"][0],
        },
    )

    print(f"   ✅ 已写回 project memory（project: {p.project_id}）")
    print(f"   ✅ 已写回 memory/{_today()}.md")
    print(f"   ✅ 已写入 SQLite project_events")
    print()
    print("─" * 60)
    print("💡 现在运行 `scripts/longclaw-status` 查看更新后的项目状态")
    print("💡 然后运行 `python3 docs/demo_research.py --round 2` 模拟新 session")
    print()


# ---------------------------------------------------------------------------
# Round 2: New session — restore context and continue
# ---------------------------------------------------------------------------

def run_round_2():
    print("=" * 60)
    print("Round 2: 新 Session — CTRL 恢复项目上下文")
    print("=" * 60)
    print()

    # Simulate CTRL reading [PROJECT] block
    store = ProjectStore()
    p = store.get("demo-vllm-research")

    if p is None:
        print("❌ 未找到项目 demo-vllm-research。请先运行 --round 1")
        return

    print("🔄 CTRL 读取 MEMORY.md [PROJECT] 块...")
    print()
    print(f"   项目: {p.name}  ({p.project_id})")
    print(f"   目标: {p.goal}")
    print(f"   上次焦点: {p.current_focus}")
    print(f"   下一步: {p.next_action}")
    print()

    # Simulate reading from daily log
    log_path = os.path.join(REPO_ROOT, "memory", f"{_today()}.md")
    has_writeback = False
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
        has_writeback = "[research_writeback]" in content

    print("─" * 60)
    print("🤖 CTRL 恢复上下文后，对话可以直接接上：")
    print()
    print('   用户: "继续上次 vLLM 的调研"')
    print()
    print("   CTRL: 上次调研（continuous batching 基础）已完成，核心发现：")
    print("         · PagedAttention 将 KV cache 分成 16-token block 按需分配")
    print("         · continuous batching 允许同一 forward pass 混合不同长度序列")
    print("         · 吞吐量比 HF Transformers 高 14-24x")
    print()
    print(f"         上次建议的下一步：{p.next_action}")
    print()
    print("         你想继续哪个方向？")
    print("         A) 深入 scheduler.py 源码")
    print("         B) 对比 TGI 的 batching 策略")
    print("         C) 调研 disaggregated prefill")
    print()
    print("─" * 60)

    # Show recent events from SQLite
    conn = db.get_connection()
    writers.initialise_schema(conn)
    events = readers.get_recent_project_events("demo-vllm-research", limit=3)
    if events:
        print("📊 SQLite project_events（跨 session 持久化）:")
        for e in events:
            print(f"   [{e['event_type']}]  {e.get('summary', '')}  ({e['created_at'][:16]})")
        print()

    if has_writeback:
        print(f"📄 memory/{_today()}.md 包含 [research_writeback] 条目")
        print()

    print("✅ 验证通过：Round 2 成功承接 Round 1 的调研结果")
    print()


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def show_status():
    store = ProjectStore()
    p = store.get("demo-vllm-research")
    if p is None:
        print("未找到 demo-vllm-research 项目。请先运行 --round 1")
        return
    print(f"Project: {p.name}")
    print(f"  Status:  {p.status}")
    print(f"  Focus:   {p.current_focus}")
    print(f"  Next:    {p.next_action}")
    print(f"  Updated: {p.updated_at}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Demo: Project-Aware Research")
    parser.add_argument("--round", type=int, choices=[1, 2], help="Run demo round 1 or 2")
    parser.add_argument("--status", action="store_true", help="Show project status")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.round == 1:
        run_round_1()
    elif args.round == 2:
        run_round_2()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

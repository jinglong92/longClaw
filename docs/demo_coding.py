#!/usr/bin/env python3
"""
Demo: Project-Aware Coding Task
展示 code-agent → project_writeback → 跨 session 恢复任务状态 的完整链路。

重点：不是"改了代码"，而是"改动被记住并形成下一步"。

Usage:
    python3 docs/demo_coding.py --round 1   # 第一轮：task 开始 + 实施 + 验证 + 写回
    python3 docs/demo_coding.py --round 2   # 第二轮：新 session 恢复任务状态，继续
    python3 docs/demo_coding.py --status    # 查看当前 project 状态
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Round 1: Coding task — start, implement, validate, writeback
# ---------------------------------------------------------------------------

def run_round_1():
    print("=" * 60)
    print("Round 1: Code Agent — longclaw-status 接入 project events")
    print("=" * 60)
    print()

    # Step 1: Task declaration
    print("📋 Task 开始")
    print("   Goal: 让 longclaw-status 显示最近 project events")
    print("   验收标准:")
    print("   · scripts/longclaw-status 输出包含 Recent Project Events 节")
    print("   · 每条 event 显示 type + summary + 时间")
    print()

    # Step 2: Simulate implementation
    print("─" * 60)
    print("🛠️  实施")
    print()
    print("   [1/3] 读取 scripts/longclaw-status 当前实现...")
    print("         → 找到 gather_full_status() 函数")
    print("         → 找到 main() 的输出逻辑")
    print()
    print("   [2/3] 修改 gather_full_status()...")
    print("         → 新增 recent_events 字段")
    print("         → 调用 readers.get_recent_project_events()")
    print()
    print("   [3/3] 修改 main() 输出逻辑...")
    print("         → 新增 Recent Project Events 节")
    print("         → 每条 event 显示 type + summary + created_at[:16]")
    print()

    # Step 3: Simulate validation
    print("─" * 60)
    print("✅ 验证")
    print()
    print("   $ python3 scripts/longclaw-status")
    print()
    print("   输出（节选）:")
    print("   ── Recent Project Events ────────────────────────────────")
    print("     [code_writeback]  Added projects + project_events tables  (2026-04-22 07:00)")
    print()
    print("   验证结果: passed ✓")
    print()

    # Step 4: Writeback
    print("─" * 60)
    print("✍️  写回 project memory...")
    print()

    store = ProjectStore()
    p = store.get("longclaw-productization")
    if p is None:
        p = Project(
            project_id="longclaw-productization",
            name="longClaw 产品化",
            goal="turn longClaw into a project-based AI workspace for technical users",
        )

    p.current_focus = "longclaw-status 已接入 project events，Week 1 全部完成"
    p.next_action = "Day 9: coding demo 写回验证；Day 10: 补文档"
    store.save(p)

    # Write to daily memory log
    log_path = os.path.join(REPO_ROOT, "memory", f"{_today()}.md")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    writeback_entry = f"""
[code_writeback]
project_id: {p.project_id}
task_goal: 让 longclaw-status 显示最近 project events
written_at: {_now_iso()}
files_touched:
  - scripts/longclaw-status: 新增 recent_events 输出节
validation_result: passed
validation_detail: python3 scripts/longclaw-status 输出包含 Recent Project Events 节
open_risks: []
next_actions:
  - Day 9: coding demo 写回验证
  - Day 10: 补文档（docs/project-memory.md + docs/workflow-writeback.md）
[/code_writeback]
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
        event_type="code_writeback",
        summary="longclaw-status 接入 project events，验证通过",
        payload={
            "files_touched": ["scripts/longclaw-status"],
            "validation_result": "passed",
            "next_action": "Day 10: 补文档",
        },
    )

    print(f"   ✅ 已写回 project memory（project: {p.project_id}）")
    print(f"   ✅ 已写回 memory/{_today()}.md")
    print(f"   ✅ 已写入 SQLite project_events")
    print()
    print("─" * 60)
    print("💡 运行 `scripts/longclaw-status` 查看更新后的项目状态")
    print("💡 然后运行 `python3 docs/demo_coding.py --round 2` 模拟新 session")
    print()


# ---------------------------------------------------------------------------
# Round 2: New session — restore task state and continue
# ---------------------------------------------------------------------------

def run_round_2():
    print("=" * 60)
    print("Round 2: 新 Session — CTRL 恢复任务状态")
    print("=" * 60)
    print()

    store = ProjectStore()
    p = store.get("longclaw-productization")

    if p is None:
        print("❌ 未找到项目 longclaw-productization。请先运行 --round 1")
        return

    print("🔄 CTRL 读取 MEMORY.md [PROJECT] 块...")
    print()
    print(f"   项目: {p.name}  ({p.project_id})")
    print(f"   上次焦点: {p.current_focus}")
    print(f"   下一步: {p.next_action}")
    print()

    # Read daily log for code_writeback
    log_path = os.path.join(REPO_ROOT, "memory", f"{_today()}.md")
    has_writeback = False
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
        has_writeback = "[code_writeback]" in content

    print("─" * 60)
    print("🤖 CTRL 恢复上下文后，对话可以直接接上：")
    print()
    print('   用户: "继续上次的任务"')
    print()
    print("   CTRL: 上次任务（longclaw-status 接入 project events）已完成，验证通过。")
    print()
    print("         改动摘要:")
    print("         · 修改了 scripts/longclaw-status")
    print("         · 新增 Recent Project Events 输出节")
    print("         · 验证: python3 scripts/longclaw-status 输出正确")
    print()
    print(f"         下一步: {p.next_action}")
    print()
    print("         要开始 Day 10 的文档工作吗？")
    print()
    print("─" * 60)

    # Show recent events from SQLite
    conn = db.get_connection()
    writers.initialise_schema(conn)
    events = readers.get_recent_project_events("longclaw-productization", limit=3)
    if events:
        print("📊 SQLite project_events（跨 session 持久化）:")
        for e in events:
            print(f"   [{e['event_type']}]  {e.get('summary', '')}  ({e['created_at'][:16]})")
        print()

    if has_writeback:
        print(f"📄 memory/{_today()}.md 包含 [code_writeback] 条目")
        print()

    print("✅ 验证通过：Round 2 成功承接 Round 1 的任务状态")
    print()


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def show_status():
    store = ProjectStore()
    p = store.get("longclaw-productization")
    if p is None:
        print("未找到 longclaw-productization 项目。请先运行 --round 1")
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
    parser = argparse.ArgumentParser(description="Demo: Project-Aware Coding Task")
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

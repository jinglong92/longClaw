#!/bin/bash
# heartbeat-agent 通畅性测试脚本
# 在 Mac mini 上运行：bash tools/test_heartbeat.sh

set -e
WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKSPACE"

echo "=== heartbeat-agent 通畅性测试 ==="
echo "Workspace: $WORKSPACE"
echo ""

# 1. 检查 memory/ 目录
echo "── Step 1：检查 memory/ 目录"
if [ -d "memory" ]; then
    echo " [OK] memory/ 存在"
    MD_COUNT=$(ls memory/*.md 2>/dev/null | wc -l | tr -d ' ')
    echo " [OK] memory/*.md 文件数：$MD_COUNT"
    TODAY="memory/$(date +%Y-%m-%d).md"
    if [ -f "$TODAY" ]; then
        echo " [OK] 今日日志存在：$TODAY"
    else
        echo " [WARN] 今日日志不存在：$TODAY"
    fi
else
    echo " [WARN] memory/ 目录不存在，首次运行正常"
    mkdir -p memory
fi
echo ""

# 2. 检查 MEMORY.md
echo "── Step 2：检查 MEMORY.md"
if [ -f "MEMORY.md" ]; then
    LINES=$(wc -l < MEMORY.md)
    echo " [OK] MEMORY.md 存在（$LINES 行）"
else
    echo " [WARN] MEMORY.md 不存在（私有文件，正常）"
fi
echo ""

# 3. 检查索引新鲜度（核心测试）
echo "── Step 3：索引新鲜度检查（--check-stale）"
python3 tools/memory_entry.py --check-stale
echo ""

# 4. 检查 heartbeat-state.json
echo "── Step 4：检查 heartbeat-state.json"
STATE="memory/heartbeat-state.json"
if [ -f "$STATE" ]; then
    echo " [OK] $STATE 存在"
    python3 -c "
import json
d = json.load(open('$STATE'))
print(f' last_check: {d.get(\"last_check\", \"N/A\")}')
print(f' has_pending: {d.get(\"has_pending\", False)}')
print(f' pending_items: {len(d.get(\"pending_items\", []))} 条')
stats = d.get('session_stats', {})
if stats:
    print(f' session_stats.active_days_7d: {stats.get(\"active_days_7d\", 0)}')
    print(f' session_stats.memory_entry_count: {stats.get(\"memory_entry_count\", {})}')
" 2>/dev/null || echo " [WARN] JSON 解析失败，文件可能为空"
else
    echo " [WARN] $STATE 不存在（heartbeat 尚未运行过）"
fi
echo ""

# 5. 检查 cron job
echo "── Step 5：检查 cron job"
if crontab -l 2>/dev/null | grep -q "longclaw_heartbeat"; then
    echo " [OK] heartbeat cron job 已安装："
    crontab -l | grep "longclaw_heartbeat"
else
    echo " [WARN] heartbeat cron job 未安装，运行 bash setup_heartbeat_cron.sh 安装"
fi
echo ""

# 6. 检查 memory_entries.jsonl
echo "── Step 6：检查索引文件"
JSONL="tools/artifacts/memory_entries.jsonl"
if [ -f "$JSONL" ]; then
    COUNT=$(wc -l < "$JSONL" | tr -d ' ')
    echo " [OK] $JSONL 存在（$COUNT 条）"
    python3 -c "
import json
from collections import Counter
entries = [json.loads(l) for l in open('$JSONL') if l.strip()]
domains = Counter(e['domain'] for e in entries)
for d, n in sorted(domains.items(), key=lambda x: -x[1]):
    print(f'   {d:<15} {n} 条')
" 2>/dev/null
else
    echo " [WARN] 索引不存在，运行 python3 tools/memory_entry.py 构建"
fi
echo ""

echo "=== 测试完成 ==="

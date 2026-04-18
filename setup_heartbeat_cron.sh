#!/bin/bash
# 安装 Proactive Heartbeat 定时巡检 cron job
# 在 Mac mini M4 上运行一次即可

WORKSPACE_DIR="$(cd "$(dirname "$0")" && pwd)"

# openclaw 是 node 脚本的 alias，cron 环境没有 shell alias，必须用完整命令
# 等价于：/opt/homebrew/opt/node/bin/node /opt/homebrew/lib/node_modules/openclaw/dist/entry.js
NODE_CMD="/opt/homebrew/opt/node/bin/node"
OPENCLAW_ENTRY="/opt/homebrew/lib/node_modules/openclaw/dist/entry.js"
OPENCLAW_CMD="$NODE_CMD $OPENCLAW_ENTRY"

# 检查 node 和 entry.js 是否存在
if [ ! -x "$NODE_CMD" ]; then
  echo "[ERROR] node not found at $NODE_CMD"
  exit 1
fi
if [ ! -f "$OPENCLAW_ENTRY" ]; then
  echo "[ERROR] openclaw entry.js not found at $OPENCLAW_ENTRY"
  exit 1
fi

# heartbeat 巡检命令
# 注意：`openclaw --print '…'` 在 2026.4.15+ 版本中不合法，
# 解析器会把引号内的字符串当成子命令名导致失败。
#
# 根据你的 openclaw 版本选择以下其中一种：
#
# 方案 A：openclaw agent（经 Gateway 跑一轮，需 Gateway 在线）
#   HEARTBEAT_CMD="cd '$WORKSPACE_DIR' && $OPENCLAW_CMD agent --agent main --message 'heartbeat巡检：spawn heartbeat-agent，执行巡检并写入 memory/heartbeat-state.json，静默完成' > /tmp/longclaw_heartbeat.log 2>&1"
#
# 方案 B：openclaw system event（入队系统事件，`openclaw system event --mode now` 已验证返回 ok）
#   HEARTBEAT_CMD="cd '$WORKSPACE_DIR' && $OPENCLAW_CMD system event --text 'heartbeat巡检：spawn heartbeat-agent，执行巡检并写入 memory/heartbeat-state.json，静默完成' --mode now > /tmp/longclaw_heartbeat.log 2>&1"
#
# cron 环境里变量嵌套展开不可靠，直接用硬编码路径构造命令
# 当前使用方案 B（system event）
_NODE="/opt/homebrew/opt/node/bin/node"
_ENTRY="/opt/homebrew/lib/node_modules/openclaw/dist/entry.js"
_WS="$WORKSPACE_DIR"
_LOG="/tmp/longclaw_heartbeat.log"

CRON_MORNING="30 8 * * * cd '$_WS' && $_NODE $_ENTRY system event --text 'longclaw heartbeat巡检' --mode now >> $_LOG 2>&1 # longclaw_heartbeat"
CRON_EVENING="0 18 * * * cd '$_WS' && $_NODE $_ENTRY system event --text 'longclaw heartbeat巡检' --mode now >> $_LOG 2>&1 # longclaw_heartbeat"

# 读取现有 crontab，去掉旧的 longclaw heartbeat 条目，加入新的
(crontab -l 2>/dev/null | grep -v "longclaw_heartbeat"; \
 echo "$CRON_MORNING"; \
 echo "$CRON_EVENING") | crontab -

echo "[OK] Heartbeat cron jobs installed:"
echo "  Morning: 08:30 daily"
echo "  Evening: 18:00 daily"
echo ""
echo "Verify with: crontab -l | grep longclaw"
echo "Log file: /tmp/longclaw_heartbeat.log"

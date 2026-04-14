#!/bin/bash
# 安装 Proactive Heartbeat 定时巡检 cron job
# 在 Mac mini M4 上运行一次即可

WORKSPACE_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW_CMD="openclaw"  # 根据实际安装路径调整

# 检查 openclaw 是否可用
if ! command -v "$OPENCLAW_CMD" &>/dev/null; then
  # 尝试常见路径
  for p in "$HOME/.local/bin/openclaw" "/usr/local/bin/openclaw" "$HOME/bin/openclaw"; do
    if [ -x "$p" ]; then OPENCLAW_CMD="$p"; break; fi
  done
fi

if ! command -v "$OPENCLAW_CMD" &>/dev/null; then
  echo "[ERROR] openclaw not found. Please set OPENCLAW_CMD in this script."
  exit 1
fi

# heartbeat 巡检命令
HEARTBEAT_CMD="cd '$WORKSPACE_DIR' && $OPENCLAW_CMD --print 'heartbeat巡检：spawn heartbeat-agent，执行巡检并写入 memory/heartbeat-state.json，静默完成' > /tmp/longclaw_heartbeat.log 2>&1"

# 安装两个 cron job：早 8:30 和 晚 18:00
CRON_MORNING="30 8 * * * $HEARTBEAT_CMD"
CRON_EVENING="0 18 * * * $HEARTBEAT_CMD"

# 读取现有 crontab，去掉旧的 longclaw heartbeat 条目，加入新的
(crontab -l 2>/dev/null | grep -v "longclaw_heartbeat"; \
 echo "# longclaw heartbeat - morning"; echo "$CRON_MORNING"; \
 echo "# longclaw heartbeat - evening"; echo "$CRON_EVENING") | crontab -

echo "[OK] Heartbeat cron jobs installed:"
echo "  Morning: 08:30 daily"
echo "  Evening: 18:00 daily"
echo ""
echo "Verify with: crontab -l | grep longclaw"
echo "Log file: /tmp/longclaw_heartbeat.log"

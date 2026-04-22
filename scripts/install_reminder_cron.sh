#!/bin/bash
set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NODE_CMD="/opt/homebrew/Cellar/node/25.8.2/bin/node"
OPENCLAW_ENTRY="/opt/homebrew/lib/node_modules/openclaw/dist/entry.js"
OPENCLAW_CMD="$NODE_CMD $OPENCLAW_ENTRY"
GATEWAY_CRON_NAME="longclaw-reminder-poller"
GATEWAY_CRON_STORE="$HOME/.openclaw/cron/jobs.json"
LOG_FILE="/tmp/longclaw_reminder.log"
PYTHON_CMD="/usr/bin/python3"
RUNNER="$WORKSPACE_DIR/scripts/run_due_reminders.py"

remove_gateway_job_by_name() {
  local name="$1"
  local ids
  ids="$(python3 - "$name" "$GATEWAY_CRON_STORE" <<'PY'
import json
from pathlib import Path
import sys
name = sys.argv[1]
store = Path(sys.argv[2])
if not store.exists():
    raise SystemExit(0)
data = json.loads(store.read_text())
jobs = data.get('jobs') if isinstance(data, dict) else data
jobs = jobs or []
for job in jobs:
    if job.get('name') == name and job.get('id'):
        print(job['id'])
PY
)"
  if [ -n "$ids" ]; then
    while IFS= read -r id; do
      [ -n "$id" ] && $OPENCLAW_CMD cron rm "$id" >/dev/null || true
    done <<< "$ids"
  fi
}

MSG="执行提醒轮询：先运行 /usr/bin/python3 scripts/run_due_reminders.py；然后读取 memory/due-reminders.json。若 count>0，则对其中每个 item 向 sessionKey=agent:main:openclaw-weixin:direct:o9cq802fwfrmlbme2kzxdhfewiyw@im.wechat 发送一条简短提醒消息，内容包含 title、content、due_at；发送后不要重复发送。若 count=0，则静默结束。"

remove_gateway_job_by_name "$GATEWAY_CRON_NAME"
$OPENCLAW_CMD cron add \
  --name "$GATEWAY_CRON_NAME" \
  --agent main \
  --session isolated \
  --light-context \
  --model "openai-codex/gpt-5.4" \
  --timeout-seconds 180 \
  --cron "*/5 * * * *" \
  --tz "Asia/Shanghai" \
  --message "$MSG" \
  >> "$LOG_FILE" 2>&1

echo "[OK] reminder cron installed: $GATEWAY_CRON_NAME (every 5 minutes)"

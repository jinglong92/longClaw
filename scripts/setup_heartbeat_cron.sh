#!/bin/bash
# 安装 Proactive Heartbeat 定时巡检 cron job
# 在 Mac mini M4 上运行一次即可

set -u

WORKSPACE_DIR="$(cd "$(dirname "$0")" && pwd)"

# openclaw 是 node 脚本的 alias，cron 环境没有 shell alias，必须用完整命令
# 等价于：/opt/homebrew/opt/node/bin/node /opt/homebrew/lib/node_modules/openclaw/dist/entry.js
NODE_CMD="/opt/homebrew/opt/node/bin/node"
OPENCLAW_ENTRY="/opt/homebrew/lib/node_modules/openclaw/dist/entry.js"
OPENCLAW_CMD="$NODE_CMD $OPENCLAW_ENTRY"
GATEWAY_CRON_AM_NAME="longclaw-heartbeat-am"
GATEWAY_CRON_PM_NAME="longclaw-heartbeat-pm"
GATEWAY_CRON_STORE="$HOME/.openclaw/cron/jobs.json"

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
# 已验证：2026.4.15 下 `system event --mode now` 只会产生 wake，不保证真正执行 heartbeat-agent。
# 为了让 cron 具备可验证的写回语义，这里直接走 `openclaw agent`，
# 显式要求主 agent 按 `.claude/agents/heartbeat-agent.md` 的流程静默巡检，
# 并且只写入 `memory/heartbeat-state.json`。
_NODE="/opt/homebrew/opt/node/bin/node"
_ENTRY="/opt/homebrew/lib/node_modules/openclaw/dist/entry.js"
_WS="$WORKSPACE_DIR"
_LOG="/tmp/longclaw_heartbeat.log"
_MODEL="openai-codex/gpt-5.3-codex"
_MSG="执行一次 heartbeat 巡检：读取 HEARTBEAT.md 与 .claude/agents/heartbeat-agent.md，按其中流程静默完成巡检；只写入 memory/heartbeat-state.json，不发送任何外部消息。完成后输出一句话，包含 last_check。"

# system crontab 仅作兜底；显式传入模型，避免 isolated/background 任务漂到已失效的本地 provider
CRON_MORNING="30 8 * * * cd '$_WS' && OPENCLAW_AGENT_MODEL='$_MODEL' $_NODE $_ENTRY agent --agent main --message '$_MSG' --timeout 180 --json >> $_LOG 2>&1 # longclaw_heartbeat"
CRON_EVENING="0 18 * * * cd '$_WS' && OPENCLAW_AGENT_MODEL='$_MODEL' $_NODE $_ENTRY agent --agent main --message '$_MSG' --timeout 180 --json >> $_LOG 2>&1 # longclaw_heartbeat"

install_system_cron() {
  # 读取现有 crontab，去掉旧的 longclaw heartbeat 条目，加入新的。
  # 避免使用 `... | crontab -`：该写法在当前机器上出现过挂起和不完整写入。
  TMP_CRON="$(mktemp)"
  trap 'rm -f "$TMP_CRON"' RETURN

  {
    crontab -l 2>/dev/null | grep -v "longclaw_heartbeat" || true
    echo "# longclaw heartbeat - morning"
    echo "$CRON_MORNING"
    echo "# longclaw heartbeat - evening"
    echo "$CRON_EVENING"
  } > "$TMP_CRON"

  python3 - "$TMP_CRON" <<'PY'
import subprocess
import sys

path = sys.argv[1]
try:
    proc = subprocess.run(["crontab", path], check=True, timeout=5, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
except subprocess.TimeoutExpired:
    print("[WARN] system crontab install timed out after 5s", file=sys.stderr)
    sys.exit(124)
except subprocess.CalledProcessError as exc:
    if exc.stdout:
        print(exc.stdout, end="")
    if exc.stderr:
        print(exc.stderr, end="", file=sys.stderr)
    sys.exit(exc.returncode)
PY
}

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
jobs = data.get("jobs") if isinstance(data, dict) else data
jobs = jobs or []
for job in jobs:
    if job.get("name") == name and job.get("id"):
        print(job["id"])
PY
)"
  if [ -n "$ids" ]; then
    while IFS= read -r id; do
      [ -n "$id" ] && $OPENCLAW_CMD cron rm "$id" >/dev/null
    done <<< "$ids"
  fi
}

install_gateway_cron() {
  remove_gateway_job_by_name "$GATEWAY_CRON_AM_NAME"
  remove_gateway_job_by_name "$GATEWAY_CRON_PM_NAME"

  $OPENCLAW_CMD cron add \
    --name "$GATEWAY_CRON_AM_NAME" \
    --agent main \
    --session isolated \
    --no-deliver \
    --light-context \
    --model "$_MODEL" \
    --timeout-seconds 180 \
    --cron "30 8 * * *" \
    --tz "Asia/Shanghai" \
    --message "$_MSG" \
    >/dev/null

  $OPENCLAW_CMD cron add \
    --name "$GATEWAY_CRON_PM_NAME" \
    --agent main \
    --session isolated \
    --no-deliver \
    --light-context \
    --model "$_MODEL" \
    --timeout-seconds 180 \
    --cron "0 18 * * *" \
    --tz "Asia/Shanghai" \
    --message "$_MSG" \
    >/dev/null
}

if install_system_cron; then
  echo "[OK] Heartbeat system crontab jobs installed:"
  echo "  Morning: 08:30 daily"
  echo "  Evening: 18:00 daily"
  echo ""
  echo "Verify with: crontab -l | grep longclaw"
  echo "Log file: /tmp/longclaw_heartbeat.log"
else
  echo "[WARN] system crontab install failed; falling back to OpenClaw Gateway cron"
  install_gateway_cron
  echo "[OK] Heartbeat Gateway cron jobs installed:"
  cat "$GATEWAY_CRON_STORE"
fi

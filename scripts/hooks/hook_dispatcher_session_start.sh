#!/usr/bin/env bash
# Full SessionStart bridge: protocol + heartbeat + sidecar ledger (for hosts that fire SessionStart).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p memory
echo "$(date '+%F %T') [hook] SessionStart bridge invoked" >> memory/sidecar-hooks.log

# 保留原有协议注入语义（含 DEV_LOG 模板约束说明）
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -f CTRL_PROTOCOLS.md ] && [ -f DEV_LOG.md ]; then
  printf '\n[SessionStart: injecting critical protocols]\n[IMPORTANT] DEV LOG must use the 9-field template defined in DEV_LOG.md — do NOT output the built-in session-state.json serialization format (routing:/session_id:/round: etc.)\n' >> "$CLAUDE_ENV_FILE"
  cat CTRL_PROTOCOLS.md DEV_LOG.md >> "$CLAUDE_ENV_FILE"
fi

# heartbeat 提示改为走稳定注入通道（优先写入 CLAUDE_ENV_FILE）
STATE="memory/heartbeat-state.json"
if [ -f "$STATE" ]; then
  HEARTBEAT_BLOCK=$(python3 - <<'PY'
import json
from pathlib import Path

p = Path("memory/heartbeat-state.json")
try:
    d = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

items = [
    i for i in d.get("pending_items", [])
    if i.get("priority") in ["P0", "P1"] and not i.get("shown")
]
if not (d.get("has_pending") and items):
    print("")
    raise SystemExit(0)

lines = [
    "\n[heartbeat reminder] 在本轮回复开头先简短呈现以下待处理事项（呈现后再正常回复用户）：",
]
for item in items[:3]:
    priority = item.get("priority", "P1")
    content = item.get("content", "").strip()
    action = item.get("action", "").strip()
    line = f"- [{priority}] {content}"
    if action:
        line += f" -> {action}"
    lines.append(line)
print("\n".join(lines))
PY
)
  if [ -n "$HEARTBEAT_BLOCK" ]; then
    if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
      printf '%s\n' "$HEARTBEAT_BLOCK" >> "$CLAUDE_ENV_FILE"
    else
      echo "$HEARTBEAT_BLOCK"
    fi
  fi
fi

# sidecar ledger 旁路记录
python3 - <<'PY' | python3 -m runtime_sidecar.hook_dispatcher SessionStart >/dev/null 2>> memory/sidecar-hooks.log || true
import json
import os

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

ctx = {
    "session_id": pick("CLAUDE_SESSION_ID", "SESSION_ID", "OPENCLAW_SESSION_ID"),
    "parent_session_id": pick("CLAUDE_PARENT_SESSION_ID", "PARENT_SESSION_ID", "OPENCLAW_PARENT_SESSION_ID"),
    "platform": pick("OPENCLAW_PLATFORM", "PLATFORM", "HOSTNAME"),
    "profile": pick("CLAUDE_PROFILE", "PROFILE"),
    "topic_key": pick("CLAUDE_TOPIC_KEY", "TOPIC_KEY"),
}
print(json.dumps(ctx, ensure_ascii=False))
PY

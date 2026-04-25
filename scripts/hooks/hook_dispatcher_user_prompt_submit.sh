#!/usr/bin/env bash
# UserPromptSubmit: /new, once-per-session protocol inject (marker), heartbeat, ledger via UserPromptSubmit plugin.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p memory
echo "$(date '+%F %T') [hook] UserPromptSubmit bridge invoked" >> memory/sidecar-hooks.log

MSG=$(echo "${CLAUDE_USER_PROMPT:-}" | tr -d '\n' | xargs)
if [ "$MSG" = "/new" ]; then
  rm -f memory/.user_prompt_submit.injected.* \
    memory/.user_prompt_last_claude_session_id \
    memory/.user_prompt_init_no_claude_session_id
  openclaw gateway restart
  exit 0
fi

pick_session_key() {
  if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
    printf '%s' "$CLAUDE_SESSION_ID"
  elif [ -n "${SESSION_ID:-}" ]; then
    printf '%s' "$SESSION_ID"
  elif [ -n "${OPENCLAW_SESSION_ID:-}" ]; then
    printf '%s' "$OPENCLAW_SESSION_ID"
  else
    printf '__unknown__'
  fi
}

SESSION_KEY="$(pick_session_key)"
# Sanitize for filename (avoid slashes etc.)
SAFE_KEY=$(printf '%s' "$SESSION_KEY" | tr -c 'A-Za-z0-9._-' '_')
MARKER="memory/.user_prompt_submit.injected.${SAFE_KEY}"

if [ ! -f "$MARKER" ]; then
  if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -f CTRL_PROTOCOLS.md ] && [ -f DEV_LOG.md ]; then
    printf '\n[UserPromptSubmit: injecting critical protocols]\n[IMPORTANT] DEV LOG must use the 9-field template defined in DEV_LOG.md — do NOT output the built-in session-state.json serialization format (routing:/session_id:/round: etc.)\n' >> "$CLAUDE_ENV_FILE"
    cat CTRL_PROTOCOLS.md DEV_LOG.md >> "$CLAUDE_ENV_FILE"
  else
    echo "[UserPromptSubmit] 请在本轮遵循 CTRL_PROTOCOLS.md 与 DEV_LOG.md。"
  fi
  touch "$MARKER"
fi

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

INPUT="$(cat || true)"
export INPUT CLAUDE_USER_PROMPT
printf '%s' "$INPUT" | python3 -c "
import json, os, sys

raw_txt = sys.stdin.read()
try:
    raw = json.loads(raw_txt) if raw_txt.strip() else {}
except Exception:
    raw = {}

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

prompt = (
    raw.get('prompt')
    or raw.get('user_prompt')
    or raw.get('message')
    or raw.get('text')
    or ((raw.get('input') or {}).get('text'))
    or os.environ.get('CLAUDE_USER_PROMPT')
    or ''
)

sid = pick('CLAUDE_SESSION_ID', 'SESSION_ID', 'OPENCLAW_SESSION_ID')
if not sid:
    sid = 'sidecar-host-unknown'

ctx = {
    'session_id': sid,
    'parent_session_id': pick('CLAUDE_PARENT_SESSION_ID', 'PARENT_SESSION_ID', 'OPENCLAW_PARENT_SESSION_ID'),
    'platform': pick('OPENCLAW_PLATFORM', 'PLATFORM', 'HOSTNAME'),
    'profile': pick('CLAUDE_PROFILE', 'PROFILE'),
    'topic_key': pick('CLAUDE_TOPIC_KEY', 'TOPIC_KEY'),
    'prompt_preview': prompt[:500] if isinstance(prompt, str) else '',
}
print(json.dumps(ctx, ensure_ascii=False))
" | python3 -m runtime_sidecar.hook_dispatcher UserPromptSubmit >/dev/null 2>> memory/sidecar-hooks.log || true

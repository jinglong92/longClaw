#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p memory
echo "$(date '+%F %T') [hook] PreToolUse bridge invoked" >> memory/sidecar-hooks.log

INPUT="$(cat || true)"

CMD="$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', '') or '')
except Exception:
    print('')
")"

# sidecar ledger 旁路记录（stdin 必须是 INPUT JSON，不能用 heredoc 占满 stdin）
printf '%s' "$INPUT" | python3 -c "
import json, os, sys

try:
    raw = json.load(sys.stdin)
except Exception:
    raw = {}

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

cmd = (raw.get('tool_input') or {}).get('command', '') or ''
ctx = {
    'session_id': pick('CLAUDE_SESSION_ID', 'SESSION_ID', 'OPENCLAW_SESSION_ID'),
    'tool_name': 'bash',
    'args': cmd,
}
print(json.dumps(ctx, ensure_ascii=False))
" | python3 -m runtime_sidecar.hook_dispatcher PreToolUse >/dev/null 2>> memory/sidecar-hooks.log || true

# 保留 rm -> trash 保护语义（OpenClaw 期望的 hookSpecificOutput JSON）
if echo "$CMD" | grep -qE '^rm '; then
  SAFE="$(echo "$CMD" | sed 's/^rm /trash /')"
  python3 -c 'import json,sys; safe=sys.argv[1]; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":{"tool_input":{"command":safe}}}}, ensure_ascii=False))' "$SAFE"
fi

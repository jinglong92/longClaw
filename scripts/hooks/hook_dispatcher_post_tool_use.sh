#!/usr/bin/env bash
# PostToolUse bridge — Layer 1 Trim
#
# Reads the tool result JSON from stdin, checks output length, and:
# 1. Passes structured context to the sidecar ledger (post_tool_use plugin)
# 2. If output > 500 chars: emits hookSpecificOutput to truncate the result
#    that Claude sees, appending the standard truncation footnote.
#
# OpenClaw PostToolUse hookSpecificOutput format:
#   { "hookSpecificOutput": { "hookEventName": "PostToolUse",
#                             "updatedOutput": "<truncated string>" } }
#
# If output is within threshold, exits silently (no hookSpecificOutput).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p memory
echo "$(date '+%F %T') [hook] PostToolUse bridge invoked" >> memory/sidecar-hooks.log

# Read stdin once into variable — must happen before any heredoc or pipe
INPUT="$(cat || true)"

# ── sidecar ledger (fire-and-forget, same pattern as pre_tool_use bridge) ───
printf '%s' "$INPUT" | python3 -c "
import json, os, sys

try:
    raw = json.loads(sys.stdin.read())
except Exception:
    raw = {}

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

tool_name  = raw.get('tool_name') or raw.get('tool', 'unknown')
output     = raw.get('output') or raw.get('tool_result') or ''
if not isinstance(output, str):
    output = json.dumps(output, ensure_ascii=False)
output_len = len(output)

sid = pick('CLAUDE_SESSION_ID', 'SESSION_ID', 'OPENCLAW_SESSION_ID')
if not sid:
    try:
        import pathlib
        sid = json.loads(pathlib.Path('memory/session-state.json').read_text()).get('session_id')
    except Exception:
        sid = None
ctx = {
    'session_id':    sid or 'sidecar-host-unknown',
    'tool_name':     tool_name,
    'output_length': output_len,
    'output':        '',
}
print(json.dumps(ctx, ensure_ascii=False))
" | python3 -m runtime_sidecar.hook_dispatcher PostToolUse >/dev/null 2>> memory/sidecar-hooks.log || true

# ── Layer 1 Trim ─────────────────────────────────────────────────────────────
TRIM_THRESHOLD=500

printf '%s' "$INPUT" | python3 -c "
import json, sys

THRESHOLD = $TRIM_THRESHOLD

try:
    raw = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

output = raw.get('output') or raw.get('tool_result') or ''
if not isinstance(output, str):
    output = json.dumps(output, ensure_ascii=False)

if len(output) > THRESHOLD:
    truncated = output[:THRESHOLD]
    footnote  = (
        '\n[截断：原始输出 ' + str(len(output)) + ' 字符，已保留前 ' + str(THRESHOLD) + ' 字符。'
        '如需完整内容请说\u201c展开上一条工具输出\u201d。]'
    )
    result = {
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'updatedOutput': truncated + footnote,
        }
    }
    print(json.dumps(result, ensure_ascii=False))
"

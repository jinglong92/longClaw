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

TRIM_THRESHOLD=500

INPUT="$(cat || true)"

# Parse output and metadata from the hook payload
python3 - "$TRIM_THRESHOLD" <<'PY'
import json, os, sys

threshold = int(sys.argv[1])

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

tool_name   = raw.get("tool_name") or raw.get("tool", "unknown")
output      = raw.get("output") or raw.get("tool_result") or ""
if not isinstance(output, str):
    output = json.dumps(output, ensure_ascii=False)
output_len  = len(output)
session_id  = pick("CLAUDE_SESSION_ID", "SESSION_ID", "OPENCLAW_SESSION_ID")

# ── sidecar ledger (fire-and-forget) ────────────────────────────────────────
ctx = {
    "session_id": session_id,
    "tool_name": tool_name,
    "output_length": output_len,
    "output": "",   # don't pass full output to ledger
}
import subprocess, json as _json
try:
    subprocess.run(
        ["python3", "-m", "runtime_sidecar.hook_dispatcher", "PostToolUse"],
        input=_json.dumps(ctx).encode(),
        capture_output=True,
        timeout=5,
    )
except Exception:
    pass

# ── Layer 1 Trim ─────────────────────────────────────────────────────────────
if output_len > threshold:
    truncated = output[:threshold]
    footnote = (
        f"\n[截断：原始输出 {output_len} 字符，已保留前 {threshold} 字符。"
        f"如需完整内容请说"展开上一条工具输出"。]"
    )
    updated = truncated + footnote
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedOutput": updated,
        }
    }
    print(json.dumps(result, ensure_ascii=False))
PY

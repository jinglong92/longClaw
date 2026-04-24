#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p memory
echo "$(date '+%F %T') [hook] PostCompact bridge invoked" >> memory/sidecar-hooks.log

# 协议重注入：覆写而非追加，防止多次 compaction 后内容膨胀
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -f CTRL_PROTOCOLS.md ] && [ -f DEV_LOG.md ]; then
  {
    printf '[PostCompact: re-injecting critical protocols]\n'
    cat CTRL_PROTOCOLS.md DEV_LOG.md
  } > "$CLAUDE_ENV_FILE"
fi

# sidecar ledger 旁路记录（传入结构化上下文）
python3 - <<'PY' | python3 -m runtime_sidecar.hook_dispatcher PostCompact >/dev/null 2>> memory/sidecar-hooks.log || true
import json
import os

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

# CLAUDE_TURN_COUNT is set by some OpenClaw versions; fall back to None
turn_count = os.environ.get("CLAUDE_TURN_COUNT")
try:
    turn_count = int(turn_count) if turn_count else None
except (TypeError, ValueError):
    turn_count = None

ctx = {
    "session_id": pick("CLAUDE_SESSION_ID", "SESSION_ID", "OPENCLAW_SESSION_ID"),
    "turn_count_before": turn_count,
    "current_turn_count": turn_count,
    "trigger_source": os.environ.get("COMPACT_TRIGGER_SOURCE", "native_compaction"),
    "summary_hint": os.environ.get("COMPACT_SUMMARY_HINT"),
    "current_context_tokens": pick("CLAUDE_CURRENT_CONTEXT_TOKENS", "CURRENT_CONTEXT_TOKENS", "OPENCLAW_CURRENT_CONTEXT_TOKENS"),
    "context_limit_tokens": pick("CLAUDE_CONTEXT_LIMIT_TOKENS", "CONTEXT_LIMIT_TOKENS", "OPENCLAW_CONTEXT_LIMIT_TOKENS"),
    "context_usage_source": pick("CLAUDE_CONTEXT_USAGE_SOURCE", "CONTEXT_USAGE_SOURCE", "OPENCLAW_CONTEXT_USAGE_SOURCE"),
}
print(json.dumps(ctx, ensure_ascii=False))
PY

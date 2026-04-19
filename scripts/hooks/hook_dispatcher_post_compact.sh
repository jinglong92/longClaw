#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p memory
echo "$(date '+%F %T') [hook] PostCompact bridge invoked" >> memory/sidecar-hooks.log

# 保留原有协议重注入语义
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -f CTRL_PROTOCOLS.md ] && [ -f DEV_LOG.md ]; then
  printf '\n[PostCompact: re-injecting critical protocols]\n' >> "$CLAUDE_ENV_FILE"
  cat CTRL_PROTOCOLS.md DEV_LOG.md >> "$CLAUDE_ENV_FILE"
fi

# sidecar ledger 旁路记录
python3 - <<'PY' | python3 -m runtime_sidecar.hook_dispatcher PostCompact >/dev/null 2>> memory/sidecar-hooks.log || true
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
}
print(json.dumps(ctx, ensure_ascii=False))
PY

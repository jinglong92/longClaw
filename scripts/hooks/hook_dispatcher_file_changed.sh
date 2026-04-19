#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p memory
echo "$(date '+%F %T') [hook] FileChanged bridge invoked" >> memory/sidecar-hooks.log

BASENAME="$(basename "${FILE_PATH:-unknown}")"
echo "[Config changed: ${BASENAME} updated at $(date '+%H:%M:%S')] Re-read the updated file before next response."

# sidecar ledger 旁路记录
python3 - <<'PY' | python3 -m runtime_sidecar.hook_dispatcher FileChanged >/dev/null 2>> memory/sidecar-hooks.log || true
import json
import os

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

file_path = os.environ.get("FILE_PATH")
ctx = {
    "session_id": pick("CLAUDE_SESSION_ID", "SESSION_ID", "OPENCLAW_SESSION_ID"),
    "files": [file_path] if file_path else [],
}
print(json.dumps(ctx, ensure_ascii=False))
PY

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

# Clean up legacy per-process markers from older logic.
# Keep only the stable marker file `memory/.session_round_reset`.
rm -f memory/.session_round_reset.proc-* 2>/dev/null || true

# 物理 session 重置：marker 文件不存在时重置 round=0
# /new 命令会清除 marker（见 user_prompt_submit.sh），开启新一轮重置
RESET_MARKER="memory/.session_round_reset"
if [ ! -f "$RESET_MARKER" ] && [ -f memory/session-state.json ]; then
  python3 - <<'PY' 2>/dev/null || true
import json, pathlib
p = pathlib.Path("memory/session-state.json")
try:
    d = json.loads(p.read_text())
    d["round"] = 0
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2))
except Exception:
    pass
PY
  touch "$RESET_MARKER"
fi

# Inject a best-effort runtime ctx token snapshot for DEV LOG rendering.
# This is a fallback path when per-turn hooks (e.g. UserPromptSubmit) are not fired.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  CTX_HINT=$(python3 - <<'PY' 2>/dev/null || true
import json, os
from pathlib import Path

def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

target_session_key = pick("CLAUDE_SESSION_KEY", "SESSION_KEY", "OPENCLAW_SESSION_KEY")
target_session_id = pick("CLAUDE_SESSION_ID", "SESSION_ID", "OPENCLAW_SESSION_ID")
cfg_path = Path(os.environ.get("OPENCLAW_CONFIG_PATH", Path.home() / ".openclaw" / "openclaw.json"))
cfg = read_json(cfg_path) or {}

stores = []
agents_cfg = cfg.get("agents", {}) if isinstance(cfg, dict) else {}
agents_list = agents_cfg.get("list", []) if isinstance(agents_cfg, dict) else []

default_agent = "main"
if isinstance(agents_list, list):
    for item in agents_list:
        if isinstance(item, dict) and item.get("id"):
            default_agent = item["id"]
            break

stores.append(Path.home() / ".openclaw" / "agents" / default_agent / "sessions" / "sessions.json")
if isinstance(agents_list, list):
    for item in agents_list:
        if not isinstance(item, dict):
            continue
        aid = item.get("id")
        if not aid:
            continue
        adir = item.get("agentDir")
        if isinstance(adir, str) and adir.strip():
            stores.append(Path(adir).expanduser().resolve().parent / "sessions" / "sessions.json")
        stores.append(Path.home() / ".openclaw" / "agents" / aid / "sessions" / "sessions.json")

seen = set()
unique_stores = []
for s in stores:
    key = str(s)
    if key in seen:
        continue
    seen.add(key)
    unique_stores.append(s)

best = None
best_key_match = None
best_id_match = None
for store in unique_stores:
    data = read_json(store)
    if not isinstance(data, dict):
        continue
    for session_key, row in data.items():
        if not isinstance(row, dict):
            continue
        updated_at = row.get("updatedAt")
        total = row.get("totalTokens")
        limit = row.get("contextTokens")
        if not isinstance(updated_at, (int, float)):
            continue
        if total is None or limit is None:
            continue
        rec = (int(updated_at), str(session_key), str(row.get("sessionId") or ""), int(total), int(limit))
        if best is None or rec[0] > best[0]:
            best = rec
        if target_session_key and str(session_key) == target_session_key:
            if best_key_match is None or rec[0] > best_key_match[0]:
                best_key_match = rec
        if target_session_id and str(row.get("sessionId") or "") == target_session_id:
            if best_id_match is None or rec[0] > best_id_match[0]:
                best_id_match = rec

final = best_id_match or best_key_match or best
if not final:
    print("")
    raise SystemExit(0)

_, session_key, session_id, total_tokens, context_tokens = final
trace = f"session_key={session_key}"
if session_id:
    trace += f" session_id={session_id}"
print(f"[runtime] ctx_tokens={total_tokens}/{context_tokens} source=sessions-store {trace}")
PY
)
  if [ -n "$CTX_HINT" ]; then
    printf '%s\n' "$CTX_HINT" >> "$CLAUDE_ENV_FILE"
  fi
fi

# sidecar ledger 旁路记录
# 关键：sidecar session_id 优先用 session-state.json 的逻辑 ID（CTRL 维护），
# 让所有 hook 写入/查询都 keyed by 同一个 ID，避免 sidecar-{uuid} 失配
python3 - <<'PY' | python3 -m runtime_sidecar.hook_dispatcher SessionStart >/dev/null 2>> memory/sidecar-hooks.log || true
import json, os, pathlib

def pick(*keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None

# Prefer logical session_id from session-state.json over runtime UUID
sid = pick("CLAUDE_SESSION_ID", "SESSION_ID", "OPENCLAW_SESSION_ID")
if not sid:
    try:
        sid = json.loads(pathlib.Path("memory/session-state.json").read_text()).get("session_id")
    except Exception:
        sid = None

ctx = {
    "session_id": sid,
    "parent_session_id": pick("CLAUDE_PARENT_SESSION_ID", "PARENT_SESSION_ID", "OPENCLAW_PARENT_SESSION_ID"),
    "platform": pick("OPENCLAW_PLATFORM", "PLATFORM", "HOSTNAME"),
    "profile": pick("CLAUDE_PROFILE", "PROFILE"),
    "topic_key": pick("CLAUDE_TOPIC_KEY", "TOPIC_KEY"),
}
print(json.dumps(ctx, ensure_ascii=False))
PY

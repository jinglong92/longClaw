#!/bin/bash
# refactor_workspace_baseline.sh
# longClaw workspace 一键基线重构
#
# 目标：
#   1) 重写 AGENTS.md 的授权模型（删除 broad ask-first 漂移）
#   2) 收紧 Web evidence gate 作用域（禁止误拦本地任务）
#   3) 固化 No synthetic execution evidence / Execution latch / Readback validation
#   4) 扩展 memory/session-state.json 为可用 schema
#   5) 重写 skills/search/public-evidence-fetch/SKILL.md
#
# 特点：
#   - 原位替换优先，不靠无限 append
#   - 自动备份
#   - 不 commit / 不 push
#
# 使用：
#   cd /Users/jinglong/.openclaw/workspace
#   bash refactor_workspace_baseline.sh

set -euo pipefail

echo "================================================"
echo "  longClaw workspace baseline refactor"
echo "================================================"
echo ""

if [ ! -f "AGENTS.md" ] || [ ! -f "MEMORY.md" ]; then
  echo "[ERROR] 请在 workspace 根目录运行（需存在 AGENTS.md / MEMORY.md）"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] 需要 python3"
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".workspace_refactor_backup_${TS}"
mkdir -p "${BACKUP_DIR}"
cp AGENTS.md "${BACKUP_DIR}/AGENTS.md.bak"
cp MEMORY.md "${BACKUP_DIR}/MEMORY.md.bak"
[ -f "memory/session-state.json" ] && cp "memory/session-state.json" "${BACKUP_DIR}/session-state.json.bak"
echo "[OK] 已备份到 ${BACKUP_DIR}"
echo ""

python3 <<'PYEOF'
import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(".")
AGENTS = ROOT / "AGENTS.md"
MEMORY = ROOT / "MEMORY.md"
SESSION = ROOT / "memory" / "session-state.json"
SKILL = ROOT / "skills" / "search" / "public-evidence-fetch" / "SKILL.md"

agents_text = AGENTS.read_text(encoding="utf-8")
memory_text = MEMORY.read_text(encoding="utf-8")

AUTH_MODEL = r"""
## Authorization model

Default authorization policy:

### Allowed by default
- local read-only file access
- workspace inspection
- local readback / verification
- memory retrieval
- session-state inspection
- public-web read-only retrieval for evidence collection

### Require explicit authorization
- local file mutation
- git commit
- git push
- outbound messages
- destructive commands
- anything that leaves the machine except public-web read-only evidence retrieval

### Forbidden ambiguity
Do not use broad rules like:
- "Anything you're uncertain about"
- "Always ask first if unsure"
as catch-all authorization triggers.

Authorization decisions must be based on concrete action type, not vague uncertainty.
""".strip()

WEB_GATE = r"""
## Web evidence capability gate

Before claiming public-web evidence retrieval capability, determine whether the current runtime can actually perform public-web fetch.

If public-web fetch capability is unavailable, return exactly once:

`blocked: no_public_web_fetch_tool`

and offer at most one fallback:
- direct URL / PDF from user
- local workspace / uploaded file search if relevant

Do not alternate repeatedly between:
- `need_authorization`
- `blocked`

for the same already-authorized read-only retrieval workflow within one session.
""".strip()

WEB_GATE_SCOPE = r"""
## Web evidence gate scope boundary

`Web evidence capability gate` applies only to tasks whose primary objective is public-web evidence retrieval.

It must NOT intercept or block:
- local file mutation
- local file readback
- workspace patching
- AGENTS.md / MEMORY.md / SKILL.md editing
- session-state inspection
- local repository search
- local artifact verification
- memory retrieval

For local-only tasks, `blocked: no_public_web_fetch_tool` is forbidden.

For local-only tasks, the only valid paths are:
- direct local readback
- need_authorization (if write is needed)
- local diff / readback evidence
- blocked only if the local read/write tool itself is unavailable
""".strip()

READ_ONLY_WEB_AUTH = r"""
## Read-only web retrieval default authorization

Public-web read-only retrieval for evidence collection is pre-authorized within the current session.

This includes:
- web search
- opening public pages
- extracting verbatim snippets
- returning source URLs and paragraph/section markers

This does NOT authorize:
- file mutation
- git commit
- git push
- outbound messages
- any write action

Do not repeat authorization requests for the same read-only retrieval scope within one session.

Repeated authorization is allowed only if:
- the source becomes private or auth-gated
- the requested scope changes materially
- the user explicitly revokes permission
""".strip()

NO_SYNTHETIC = r"""
## No synthetic execution evidence

The following fields may appear only if they come from a real executed tool/process in the same turn:
- exact command/tool
- stdout/stderr
- job handle
- target files touched

They must not be fabricated, inferred, templated, or described from intended actions.

Directory inspection, existence checks, or planning steps must not be described as:
- file mutation
- patch applied
- write completed
- execution started

If no real execution evidence exists, the correct status is:
- blocked
- need_authorization
- evidence_pending
""".strip()

EXECUTION_LATCH = r"""
## Execution latch rule

For any request involving file mutation, script execution, commit, or push:

### Forbidden before same-message evidence
Do not say:
- 我执行这个
- 我现在立刻执行
- completing later / 完成后给你
- executing:
- 已开始执行
- 已进入执行阶段
- 完成后我只回执证据

unless the same reply already includes execution evidence.

### Minimum evidence required for `executing:`
`executing:` is allowed only if the same reply includes all three:

1. exact command or tool invoked
2. first stdout/stderr line OR job handle
3. target files / branch / scope

If any of the three is missing, `executing:` is forbidden.

### Authorization separation
User authorization to modify files does NOT imply authorization to:
- git commit
- git push

These require separate explicit confirmation.

### Required execution order
1. modify files
2. return diff or file readback
3. ask whether to commit
4. if authorized, return commit hash
5. ask whether to push
6. if authorized, return push receipt
""".strip()

READBACK_RULE = r"""
## Readback validation rule

When the agent claims a file has been read, verified, or validated, it must return the readback evidence itself, not only a summary.

### Minimum readback evidence
A valid readback/validation reply must include all three:

1. target file path
2. exact matched excerpt (verbatim snippet from file content)
3. brief interpretation of what the excerpt proves

### Forbidden substitutes
The following do NOT count as readback evidence by themselves:
- heading names only
- bullet summary of matched sections
- "已读取到原文"
- "关键命中行包括"
- "diff 已验证"
- "规则已生效"

### Claim boundary
- `已写入文件` requires file-level evidence
- `已读回校验` requires verbatim readback evidence
- `已生效` requires observed behavioral evidence in addition to file readback

If only headings or summaries are available, the correct status is:
- evidence_pending
- readback_incomplete
""".strip()

SESSION_CONTRACT = r"""
## Session state contract

The workspace must maintain a structured session state file:

`memory/session-state.json`

### Purpose

This file is the source of truth for session-scoped metadata that cannot be reliably reconstructed from long-term memory alone.

It is used for:
- session identity
- turn/round tracking
- dev mode state
- routing presentation state
- active domain/topic
- latest retrieval scope
- pending confirmations

### Minimum fields

- `session_id`
- `round`
- `dev_mode`
- `routing_visibility`
- `active_domain`
- `current_topic`
- `last_retrieval_scope`
- `last_retrieval_query_variants`
- `pending_confirmation`
- `read_only_web_authorized`
- `authorized_scopes`
- `updated_at`

### Update rules

On every user turn, CTRL should update this file:
- increment `round`
- recompute and write `dev_mode`
- update `routing_visibility` when presentation preference changes
- update `active_domain` after route resolution
- update `current_topic` when topic is clearly identified or changes
- update `last_retrieval_scope` after retrieval
- update `last_retrieval_query_variants` when query rewrite is used
- set / clear `pending_confirmation` when confirmation-gated actions appear

### DEV LOG binding

If `memory/session-state.json` exists and is readable:
- DEV LOG should use it as the primary source for session fields

If it does not exist:
- DEV LOG may output `Session unavailable`
""".strip()

DEV_MODE = r"""
## Developer Mode

Developer Mode is a session-scoped hard state.

### Activation
- user says `开启 dev mode` / `打开开发者模式`
- state must be written to `memory/session-state.json`

### Deactivation
- user says `关闭 dev mode` / `关闭开发者模式`
- state must be written to `memory/session-state.json`

### Integrity rule
Do not say `已开启 dev mode` unless the same reply either:
- includes `[DEV LOG]`, or
- provides file/session evidence showing dev mode state was actually updated.

If activation evidence is missing, the correct status is:
- blocked: dev_mode_activation_failed
- evidence_pending
""".strip()

ROUTING_OVERRIDE = r"""
## Routing visibility override rule

Routing must appear in `[DEV LOG]` when dev mode is on.

Routing must NOT appear in the main body if the user's presentation preference says:
- 正文不要显示 routing
- routing 只放 DEV LOG
- 正文隐藏 routing

This override affects presentation only, not actual routing behavior.
""".strip()

MEMORY_PREF = r"""
### Execution and retrieval baseline

- Broad ask-first rules are disabled; authorization is action-type based, not uncertainty-based.
- Local read-only tasks are allowed by default.
- Public-web read-only evidence retrieval is session-pre-authorized unless explicitly revoked.
- Web evidence gate applies only to public-web evidence retrieval and must never block local-only tasks.
- Without real execution evidence, do not claim execution started or completed.
- Without verbatim readback evidence, do not claim verification complete.
- DEV LOG should prefer `memory/session-state.json` for session fields when available.
""".strip()

SKILL_TEXT = r"""---
name: public-evidence-fetch
description: 对公开网页/论文执行只读检索与证据摘录，返回 exact query、URL、逐字片段、段落位置与简短解释。
version: 2.0.0
author: jinglong92
license: MIT
---

# Public Evidence Fetch

## Trigger

当用户要求以下任一类型任务时触发：
- 外网搜一下并给我原文片段
- 谷歌搜这篇论文，然后截取对应段落
- 给我链接 + 逐字摘录 + 段落位置
- 不要总结，给证据
- 抓取公开网页证据
- 论文原文摘录
- 给我 exact query + URL + snippet + position

## Scope

仅适用于：
- 公共网页
- 公开论文页（如 arXiv / OpenReview / 官方文档 / GitHub README / 公共博客）
- 无需登录即可访问的页面

不适用于：
- 私有文档
- 登录后内容
- 需要写操作的任务

## Authorization

如果当前 session 已有：
- `read_only_web_authorized = true`
- 且 `authorized_scopes` 包含 `public_web_read_only_evidence_fetch`

则不得重复请求授权。

## Workflow

### Step 1: Query Rewrite
至少生成 2-3 个 query 变体：
1. 原始 query
2. 带 domain/source hint 的 query
3. 带目标概念/术语的 query

### Step 2: Capability Gate
先判断当前 runtime 是否真有 public-web fetch 能力。
若没有，直接：
`blocked: no_public_web_fetch_tool`
并只给一个 fallback。

### Step 3: Search
优先顺序：
1. 官方源 / 论文源（arXiv / OpenReview / 官方文档）
2. 搜索引擎结果
3. 公共镜像源

### Step 4: Page Open
打开候选页并定位用户指定目标概念。

### Step 5: Evidence Extraction
只提取用户指定目标相关的逐字片段，不用总结代替证据。

### Step 6: Return Format
必须返回：
- exact query
- source URL
- verbatim snippet
- paragraph/section marker
- one-sentence mapping

## Failure Contract

如果拿不到：
- exact query
- source URL
- verbatim snippet
- paragraph/section marker

则不得声称完成。
只能返回：
- `blocked: no_verifiable_evidence`
或
- `need_input: direct_url_or_pdf`

## Forbidden

不得：
- 在已授权会话内重复 ask authorization
- 没有原文片段时只给总结
- 没有 URL 时声称抓取成功
- 在失败后反复在 `need_authorization` 与 `blocked` 间切换
"""

def replace_section(text: str, heading_name: str, new_block: str) -> str:
    pattern = re.compile(
        rf"(?ms)^#{{2,4}}\s+{re.escape(heading_name)}\s*\n.*?(?=^#{{2,4}}\s+|\Z)"
    )
    if pattern.search(text):
        return pattern.sub(new_block + "\n\n", text, count=1)
    else:
        return text.rstrip() + "\n\n---\n\n" + new_block + "\n"

def remove_broad_rules(text: str) -> str:
    bad_patterns = [
        r'(?mi)^.*Don\'t ask permission\.\s*Just do it\..*$\n?',
        r'(?mi)^.*Anything you\'re uncertain about.*$\n?',
        r'(?mi)^.*Always ask first if unsure.*$\n?',
    ]
    for p in bad_patterns:
        text = re.sub(p, "", text)
    return text

agents_text = remove_broad_rules(agents_text)

for title, block in [
    ("Authorization model", AUTH_MODEL),
    ("Read-only web retrieval default authorization", READ_ONLY_WEB_AUTH),
    ("Web evidence capability gate", WEB_GATE),
    ("Web evidence gate scope boundary", WEB_GATE_SCOPE),
    ("No synthetic execution evidence", NO_SYNTHETIC),
    ("Execution latch rule", EXECUTION_LATCH),
    ("Readback validation rule", READBACK_RULE),
    ("Session state contract", SESSION_CONTRACT),
    ("Developer Mode（开发者运行日志）", DEV_MODE),
    ("Developer Mode", DEV_MODE),
    ("Routing visibility override rule", ROUTING_OVERRIDE),
]:
    agents_text = replace_section(agents_text, title, block)

AGENTS.write_text(agents_text, encoding="utf-8")

if "### Execution and retrieval baseline" not in memory_text:
    memory_text = memory_text.rstrip() + "\n\n" + MEMORY_PREF + "\n"
else:
    memory_text = re.sub(
        r"(?ms)^###\s+Execution and retrieval baseline\s*\n.*?(?=^###\s+|\Z)",
        MEMORY_PREF + "\n\n",
        memory_text,
    )
MEMORY.write_text(memory_text, encoding="utf-8")

SESSION.parent.mkdir(parents=True, exist_ok=True)
if SESSION.exists():
    try:
        session_data = json.loads(SESSION.read_text(encoding="utf-8"))
    except Exception:
        session_data = {}
else:
    session_data = {}

defaults = {
    "session_id": "main",
    "round": 0,
    "dev_mode": False,
    "routing_visibility": "dev_log_only",
    "active_domain": "CTRL",
    "current_topic": None,
    "last_retrieval_scope": None,
    "last_retrieval_query_variants": [],
    "pending_confirmation": None,
    "read_only_web_authorized": True,
    "authorized_scopes": ["public_web_read_only_evidence_fetch"],
    "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}

for k, v in defaults.items():
    if k not in session_data:
        session_data[k] = v

if "public_web_read_only_evidence_fetch" not in session_data.get("authorized_scopes", []):
    session_data.setdefault("authorized_scopes", []).append("public_web_read_only_evidence_fetch")

SESSION.write_text(json.dumps(session_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

SKILL.parent.mkdir(parents=True, exist_ok=True)
SKILL.write_text(SKILL_TEXT, encoding="utf-8")

print("[OK] AGENTS.md / MEMORY.md / session-state.json / SKILL.md 已重写")
PYEOF

echo "--- 变更文件 ---"
ls -1 AGENTS.md MEMORY.md memory/session-state.json skills/search/public-evidence-fetch/SKILL.md
echo ""

git add AGENTS.md skills/search/public-evidence-fetch/SKILL.md refactor_workspace_baseline.sh || true

echo "--- git diff --stat HEAD ---"
git diff --stat HEAD
echo "--- ignored local-only state ---"
printf "%s\n" "MEMORY.md (ignored)" "memory/session-state.json (ignored)"
echo ""

echo "================================================"
echo "基线重构完成（未 commit / 未 push）"
echo ""
echo "下一步："
echo "  1) 重启 longClaw / WeixinClawBot 进程"
echo "  2) 新开微信会话"
echo "  3) 再测：本地只读校验、本地改单行、外网证据抓取"
echo ""
echo "可选提交："
echo "  git commit -m 'refactor: rebuild workspace authorization and execution baseline'"
echo "================================================"

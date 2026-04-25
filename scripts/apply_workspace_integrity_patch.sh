#!/bin/bash
# apply_workspace_integrity_patch.sh
# 目标：只改 workspace 层，不碰预留优化闭环
# 作用：
#   1) 执行完整性硬化：无证据不报完成
#   2) 检索顺序收口：先 scope，再 recall
#   3) DEV LOG 去叙述化：无真字段则 unavailable
#   4) Heartbeat 静默化：去掉 placeholder/主动骚扰漂移
#   5) README 收口：把“已实现”与“工作区协议层”说清

set -euo pipefail

echo "================================================"
echo "  longClaw workspace integrity patch"
echo "================================================"
echo ""

if [ ! -f "AGENTS.md" ] || [ ! -f "MEMORY.md" ] || [ ! -f "README.md" ]; then
  echo "[ERROR] 请在 longClaw 仓库根目录运行"
  exit 1
fi

BRANCH="feature/workspace-integrity-hardening"
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
echo "[OK] 切换到分支: $BRANCH"
echo ""

append_if_absent() {
  local file="$1"
  local marker="$2"
  local content="$3"
  local label="$4"

  if grep -qF "$marker" "$file" 2>/dev/null; then
    echo "  [SKIP] $label: 已存在"
  else
    printf '\n%s\n' "$content" >> "$file"
    echo "  [OK] $label"
  fi
}

replace_once_py() {
  local file="$1"
  local old_text="$2"
  local new_text="$3"
  local label="$4"

  python3 - "$file" "$old_text" "$new_text" "$label" << 'PYEOF'
import sys
from pathlib import Path

file_path, old_text, new_text, label = sys.argv[1:]
p = Path(file_path)
text = p.read_text(encoding="utf-8")

if old_text not in text:
    print(f"  [WARN] {label}: 未找到目标文本，跳过")
    sys.exit(0)

text = text.replace(old_text, new_text, 1)
p.write_text(text, encoding="utf-8")
print(f"  [OK] {label}")
PYEOF
}

echo "--- 1) AGENTS.md：执行完整性硬化 ---"

append_if_absent "AGENTS.md" "## Execution integrity hard rules" '
---

## Execution integrity hard rules

### No evidence, no completion claim
The agent must not claim any task is completed, modified, enabled, committed, pushed, verified, or fixed unless at least one verifiable artifact exists.

Valid evidence includes:
- file readback excerpt
- diff output
- command stdout/stderr
- commit hash
- push receipt
- tool return payload

Without evidence, only these states are allowed:
- planned
- pending
- blocked
- executing
- evidence_pending

Forbidden phrases without evidence:
- 已修改
- 已完成
- 已开启
- 已推送
- 已验证
- 已修复

### Change report contract
Any claimed change must be reported in exactly three parts:

1. Change level
   - 会话级 / 配置级 / 代码级

2. Modified target
   - file path / command / branch / tool name

3. Evidence
   - diff excerpt / readback / stdout / hash / receipt

If part (3) is missing, the change must not be reported as completed.

### Anti-stall execution rule
Before producing any verifiable artifact, the agent must not send:
- 我现在去做
- 下一条给你结果
- 马上执行
- 已开始处理
- 正在修改（若没有工具或文件证据）

Allowed pre-evidence outputs:
- blocked: <reason>
- need_authorization: <specific action>
- need_input: <specific missing item>

### DEV LOG integrity rule
DEV LOG must only contain:
- runtime-produced fields
- tool-returned fields
- deterministic controller state

If a field is unavailable, print `unavailable`.
Do not infer or fabricate DEV LOG values from intention, narration, or expected workflow.
' "AGENTS 执行完整性硬规则"

append_if_absent "AGENTS.md" "## Retrieval scope rule" '
---

## Retrieval scope rule

For memory retrieval, always decide **where to search before how to search**.

Preferred retrieval order:
1. current session / recent turns
2. same-domain recent memory
3. same-domain long-term memory
4. cross-domain fallback (only when same-domain evidence is insufficient)

Never start with global cross-domain retrieval by default.

Before answering prior-work / dates / decisions questions:
- first narrow the scope by route/domain
- then run retrieval
- only widen to cross-domain if same-domain retrieval is empty or low-confidence

If fallback widening happens, mark it in DEV LOG.
' "AGENTS 检索范围规则"

append_if_absent "AGENTS.md" "## Routing visibility override rule" '
---

## Routing visibility override rule

Default: keep routing visible.

But if the user explicitly asks to hide routing from the main body:
- do not print routing in正文
- keep routing only inside `[DEV LOG]`
- this override applies to presentation only, not to internal routing behavior
' "AGENTS 路由显示覆盖规则"

echo ""

echo "--- 2) AGENTS.md：Heartbeat 收口 ---"
# 使用 heredoc 避免 bash 对反引号做命令替换；支持已打补丁的树（幂等）
python3 << 'PYPATCH'
from pathlib import Path

p = Path("AGENTS.md")
text = p.read_text(encoding="utf-8")

old_intro = """## 💓 Heartbeats - Be Proactive!

When you receive a heartbeat poll, **HEARTBEAT.md is the single source of truth**. If HEARTBEAT.md says silent mode, do not send any placeholder text (including `HEARTBEAT_OK`).

Default heartbeat prompt (legacy):
`Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.`

Execution precedence:
1. Follow HEARTBEAT.md first.
2. If HEARTBEAT.md conflicts with this file, HEARTBEAT.md wins for heartbeat behavior.

You are free to edit `HEARTBEAT.md` with a short checklist or reminders. Keep it small to limit token burn."""

new_intro = """## 💓 Heartbeats - Single source of truth

When you receive a heartbeat poll, **HEARTBEAT.md is the single source of truth**.

Execution precedence:
1. Follow HEARTBEAT.md first.
2. If HEARTBEAT.md conflicts with this file, HEARTBEAT.md wins for heartbeat behavior.

If HEARTBEAT.md specifies silent mode:
- do not send placeholder text
- do not send `HEARTBEAT_OK`
- do not send proactive status pings
- produce no outbound user-facing message unless a critical emergency exists

Default heartbeat behavior is now governed by HEARTBEAT.md, not by legacy placeholder replies."""

old_body = """**Things to check (rotate through these, 2-4 times per day):**

- **Emails** - Any urgent unread messages?
- **Calendar** - Upcoming events in next 24-48h?
- **Mentions** - Twitter/social notifications?
- **Weather** - Relevant if your human might go out?

**Track your checks** in `memory/heartbeat-state.json`:

```json
{
  "lastChecks": {
    "email": 1703275200,
    "calendar": 1703260800,
    "weather": null
  }
}
```

**When to reach out:**

- Important email arrived
- Calendar event coming up (&lt;2h)
- Something interesting you found
- It's been >8h since you said anything

**When to stay quiet (no outbound message):**

- Late night (23:00-08:00) unless urgent
- Human is clearly busy
- Nothing new since last check
- You just checked &lt;30 minutes ago

**Proactive work you can do without asking:**

- Read and organize memory files
- Check on projects (git status, etc.)
- Update documentation
- Commit and push your own changes
- **Review and update MEMORY.md** (see below)

### 🔄 Memory Maintenance (During Heartbeats)

Periodically (every few days), use a heartbeat to:

1. Read through recent `memory/YYYY-MM-DD.md` files
2. Identify significant events, lessons, or insights worth keeping long-term
3. Update `MEMORY.md` with distilled learnings
4. Remove outdated info from MEMORY.md that's no longer relevant

Think of it like a human reviewing their journal and updating their mental model. Daily files are raw notes; MEMORY.md is curated wisdom.

The goal: Be helpful without being annoying. Check in a few times a day, do useful background work, but respect quiet time."""

new_body = """**Things to check (heartbeat internal rotation):**

- **Emails** - Any urgent unread messages?
- **Calendar** - Upcoming events in next 24-48h?
- **Mentions** - Relevant notifications?
- **Weather** - Only if actually decision-relevant

Track internal checks in `memory/heartbeat-state.json`.

**Heartbeat output policy:** follow HEARTBEAT.md.
If HEARTBEAT.md is silent, all of the above remain internal-only and must not become outbound messages.

**Allowed internal work during heartbeat:**

- Read and organize memory files
- Check project state
- Update documentation
- Review MEMORY.md
- Prepare internal recommendations

### 🔄 Memory Maintenance (During Heartbeats)

Periodically, a heartbeat may:

1. Read recent `memory/YYYY-MM-DD.md` files
2. Distill significant events / lessons
3. Update `MEMORY.md`
4. Remove outdated long-term items

These are internal maintenance actions and do not imply outbound user messaging."""

if old_intro in text:
    text = text.replace(old_intro, new_intro, 1)
    print("  [OK] Heartbeat 顶层规则收口")
elif "## 💓 Heartbeats - Single source of truth" in text:
    print("  [SKIP] Heartbeat 顶层规则收口: 已是新版本")
else:
    print("  [WARN] Heartbeat 顶层规则收口: 未找到目标文本")

if old_body in text:
    text = text.replace(old_body, new_body, 1)
    print("  [OK] Heartbeat 主动触达旧逻辑收口")
elif "**Things to check (heartbeat internal rotation):**" in text:
    print("  [SKIP] Heartbeat 主动触达旧逻辑收口: 已是新版本")
else:
    print("  [WARN] Heartbeat 主动触达旧逻辑收口: 未找到目标文本")

p.write_text(text, encoding="utf-8")
PYPATCH

echo ""

echo "--- 3) HEARTBEAT.md：重写为静默策略 ---"

cat > HEARTBEAT.md << 'EOF'
# HEARTBEAT.md

## Silent Heartbeat Policy

Heartbeat polling is an internal maintenance action, not a user-facing interaction.

Default behavior: **silence**.

---

## Core Rule

When heartbeat polling is triggered:

- Do **not** send any proactive outbound message to WeChat, email, SMS, Slack, or any other user-facing channel.
- Do **not** send placeholder texts such as `HEARTBEAT_OK`, `心跳正常`, `all good`, `still alive`, or any equivalent status ping.
- Do **not** acknowledge to the user that heartbeat polling occurred.
- If there is **no critical emergency**, produce **no outbound user-facing message**.

---

## Allowed Internal Actions

Heartbeat may still perform internal work, including:
- checking inbox / calendar / notifications
- reading or updating memory files
- reviewing workspace files
- recording internal logs or state
- preparing a future recommendation internally

These actions must remain silent unless a critical emergency exists.

---

## What Counts as a Critical Emergency

A user-facing alert is allowed **only** if immediate human action is required to prevent one of the following:

1. Security incident
2. Irreversible destructive failure
3. Production outage requiring human intervention
4. High-risk financial / operational failure
5. Safety-critical issue

If the issue is recoverable, transient, low-confidence, retryable, or can be handled automatically, it is **not** a critical emergency.

---

## Non-Emergencies (Must Stay Silent)

The following are **not** reasons to send a message:

- heartbeat succeeded normally
- no new events were found
- temporary timeout or retryable API failure
- one source failed but alternatives still exist
- minor warning or uncertainty
- “just keeping the user informed”
- “it has been a while since the last message”
- “something interesting was found”
- routine background polling result

All of the above must produce **no outbound message**.

---

## Output Contract

### If no critical emergency
- perform internal checks if needed
- optionally update internal files/logs
- send **nothing**
- return **empty / no-op / no outbound user-facing message**

### If critical emergency exists
Send exactly **one concise alert**, containing:
- what happened
- why it is critical
- what immediate action is required

---

## Enforcement Rule

If there is any ambiguity, choose **silence**.
EOF
echo "  [OK] HEARTBEAT.md 已重写"
echo ""

echo "--- 4) MEMORY.md：补长期执行偏好 ---"

append_if_absent "MEMORY.md" "## [SYSTEM] 执行完整性偏好（补丁）" '
---

## [SYSTEM] 执行完整性偏好（补丁）

- Execution truth preference: no evidence, no completion claim.
- Change reports must always use three parts: change level, modified target, evidence.
- DEV LOG may only show runtime/tool/controller-grounded fields; unknown fields must be `unavailable`.
- If routing should be hidden from正文, keep it only in `[DEV LOG]`.
- Heartbeat default mode is silent internal maintenance, not proactive user messaging.
- Retrieval preference: first narrow by domain/scope, then retrieve; do not start with global cross-domain recall.
' "MEMORY 长期执行偏好"

echo ""

echo "--- 5) README.md：收口为 workspace-level 承诺 ---"

append_if_absent "README.md" "## 当前工作区约束（patch note）" '
---

## 当前工作区约束（patch note）

以下能力若未下沉到优化闭环/runtime，则视为 **workspace-level behavior contract**：
- DEV LOG 显示规则
- routing presentation override
- heartbeat silent mode
- retrieval scope narrowing
- completion-claim evidence gating

也就是说：
- 工作区协议层已经定义这些行为
- 但若运行层未实现对应校验器，CTRL 必须手动遵守
- 文档中的“可观测性/压缩/检索”应优先理解为：当前 workspace 行为约束 + 部分已实现能力
' "README 能力收口说明"

echo ""

echo "--- 6) git add ---"
git add AGENTS.md MEMORY.md HEARTBEAT.md README.md
echo "  [OK] 已暂存: AGENTS.md MEMORY.md HEARTBEAT.md README.md"
echo ""

echo "--- 改动汇总 ---"
git diff --stat HEAD
echo ""

echo "================================================"
echo "  Patch 完成"
echo ""
echo "建议你下一步人工 review："
echo "  git diff AGENTS.md"
echo "  git diff MEMORY.md"
echo "  git diff HEARTBEAT.md"
echo "  git diff README.md"
echo ""
echo "确认后："
echo "  git commit -m 'feat: harden workspace execution integrity and silent heartbeat'"
echo "  git push origin $BRANCH"
echo "================================================"

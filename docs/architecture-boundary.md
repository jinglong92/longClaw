# Architecture Boundary

This document clarifies the division of responsibilities between the
OpenClaw runtime, the longClaw workspace and the sidecar layer.

---

## 1. Three-layer model

```
workspace-first → sidecar-second → runtime-fork-last
```

| Layer | Owner | Can modify OpenClaw? |
|-------|-------|---------------------|
| L1: workspace | longClaw | No |
| L2: sidecar | longClaw | No |
| L3: thin patch | longClaw | Yes, strictly minimal |

---

## 2. OpenClaw Runtime (host)

The OpenClaw runtime executes agent turns, evaluates hooks and manages
session lifecycles. It **must not be modified** by longClaw except via
the thin-patch layer, which is out of scope for the current phase.

Responsibilities:
- Exposes hook entry points via `.claude/settings.json`
- Manages session state, agent scheduling and tool execution
- Owns the bootstrap file loading and compaction logic

---

## 3. longClaw Workspace

Defines agents, skills, workflows and settings for this deployment.

Responsibilities:
- Defines agent specifications (`AGENTS.md`, `SOUL.md`, `MULTI_AGENTS.md`)
- Provides protocol files (`CTRL_PROTOCOLS.md`, `DEV_LOG.md`)
- Supplies `.claude/settings.json` to wire hooks into the sidecar
- Houses memory files (`MEMORY.md`, `memory/`, `heartbeat-state.json`)

---

## 4. Runtime Sidecar

A Python package that extends longClaw without modifying the host runtime.
Runs inside hook processes; maintains its own state and logic.

Responsibilities:
- Hook dispatcher (`hook_dispatcher.py`) — consolidates shell scripts
- Event bus + plugin system — handles SessionStart, PostCompact,
  PostToolUse, UserPromptSubmit, FileChanged, PreToolUse events
- Session ledger (SQLite) — records session/tool/compact metadata
- `doctor` / `status` scripts — environment health and ledger stats

---

## 5. Context loading and compaction survival matrix

Understanding which files survive compaction is critical for knowing
where to put rules that must never be lost.

### Three context layers

**Layer A — OpenClaw native bootstrap files**
Automatically injected into the system prompt on every agent run.

| File | Auto-loaded | Notes |
|------|------------|-------|
| `AGENTS.md` | ✅ | Core bootstrap; also the only file with native post-compaction section refresh |
| `SOUL.md` | ✅ | Bootstrap file |
| `TOOLS.md` | ✅ | Bootstrap file |
| `IDENTITY.md` | ✅ | Bootstrap file |
| `USER.md` | ✅ | Bootstrap file |
| `MEMORY.md` | ✅ (main private session) | Conditional |
| `MULTI_AGENTS.md` | ❌ | Not a native bootstrap file |
| `CTRL_PROTOCOLS.md` | ❌ | Not a native bootstrap file |
| `DEV_LOG.md` | ❌ | Not a native bootstrap file |

**Layer B — Startup context**
Injected once on `/new` / `/reset`. Recent `memory/YYYY-MM-DD*.md`
files are loaded as "untrusted daily memory" for the first turn only.
Not injected on subsequent turns.

**Layer C — Hook-injected protocol layer**
Content appended to `CLAUDE_ENV_FILE` by bridge scripts. Includes
`CTRL_PROTOCOLS.md`, `DEV_LOG.md`, heartbeat reminders.

> `CLAUDE_ENV_FILE` content should be treated as temporary per-run
> context, not durable transcript. It does not survive compaction.
> Must be re-injected in `PostCompact`.

### Native post-compaction refresh — what is actually protected

OpenClaw's `post-compaction-context.ts` only explicitly re-injects
specific sections from `AGENTS.md`:

- Default: `Session Startup` and `Red Lines`
- Legacy fallback: `Every Session` and `Safety`

**Nothing else** is in the native post-compaction whitelist.
`SOUL.md`, `USER.md`, `MEMORY.md` re-enter context as bootstrap
sources on the next run, but are not part of this explicit refresh.

### Implications for longClaw

| Rule type | Where to put it |
|-----------|----------------|
| Must never be lost (safety, red lines, core CTRL invariants) | `AGENTS.md` — protected by native post-compaction refresh |
| Important but can be re-injected | `CTRL_PROTOCOLS.md` / `DEV_LOG.md` — rely on PostCompact hook |
| Routing and agent definitions | `MULTI_AGENTS.md` — **must be hook-injected**; currently missing from all hook scripts |
| Long-term memory | `MEMORY.md` — bootstrap source, re-enters on next run |

### Known gap: MULTI_AGENTS.md is not injected

`MULTI_AGENTS.md` is not a native bootstrap file and is not injected
by any current hook script. Three options to fix this:

1. Merge core routing rules into `AGENTS.md` (most stable)
2. Add `MULTI_AGENTS.md` to the `PostCompact` / `SessionStart` injection
3. Accept explicit `read` as the only way CTRL sees it

Option 1 is recommended for rules that must be always available.
Option 2 is acceptable for the full routing table.

---

## 6. Known doc/code discrepancy (low priority)

Official subagent documentation states only `AGENTS.md` and `TOOLS.md`
are injected for sub-agent sessions. However, `workspace.ts`
`MINIMAL_BOOTSTRAP_ALLOWLIST` currently includes `AGENTS.md`,
`SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`.

This discrepancy does not affect the main session. Flag for review if
subagent bootstrap behaviour needs to be documented precisely.

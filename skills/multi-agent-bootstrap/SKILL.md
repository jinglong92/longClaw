---
name: multi-agent-bootstrap
description: Bootstrap and migrate an OpenClaw workspace from single-agent to beginner-friendly multi-agent mode with visible routing. Use when user asks to create/adapt/sync multi-agent setup, add role definitions, enforce routing line output, or quickly replicate a proven multi-agent architecture.
---

# Multi-Agent Bootstrap

Create or update a workspace to a stable multi-agent baseline for beginners.

## Workflow

1. Read current files first: `AGENTS.md`, `USER.md`, `MULTI_AGENTS.md` (if exists), `MEMORY.md` (if main session).
2. If `MULTI_AGENTS.md` is missing, create it from `references/MULTI_AGENTS.template.md`.
3. Ensure role set includes at least: `LIFE/WORK/LEARN/ENGINEER`.
4. Ensure routing visibility rule is explicit in both `AGENTS.md` and `MULTI_AGENTS.md`:
   - `Routing: User -> CTRL -> [ROLE] -> CTRL -> User`
   - Parallel: `Routing: User -> CTRL -> ([ROLE_A] || [ROLE_B]) -> CTRL -> User`
5. Apply beginner safety defaults:
   - default single specialist routing
   - max parallel specialists = 2
   - CTRL is final merger only
6. If user asks “固化/记住”, persist in both:
   - `MULTI_AGENTS.md` (source of truth)
   - `MEMORY.md` (preference continuity)
7. Run `scripts/check_multi_agent.sh` to validate required fields/rules.
8. If validation passes, summarize changes and recommend 3 smoke tests from `references/smoke-tests.md`.

## Editing Rules

- Prefer surgical edits over full rewrites.
- Keep role labels business-facing; avoid generic tags like PLAN.
- Do not silently remove existing user-specific roles.
- On conflicts: safety/boundary rules in `AGENTS.md` win.

## Required Outputs

- A concise change summary.
- Explicit routing line in every user-facing reply.
- A short “what to test next” list.

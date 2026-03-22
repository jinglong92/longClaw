# longClaw Workspace

This repository stores the working memory, operating rules, and multi-agent experiments for a personal OpenClaw setup.

## What this repo contains

- Core behavior and safety docs for the assistant (`AGENTS.md`, `SOUL.md`, `USER.md`)
- Long-term and daily memory files (`MEMORY.md`, `memory/`)
- Multi-agent routing config and architecture notes (`MULTI_AGENTS.md`, `multi-agent/`)
- A runnable chat-first console prototype (`multi-agent/agent-console-mvp/`)

## Repo layout

```text
.
|-- AGENTS.md
|-- SOUL.md
|-- USER.md
|-- MEMORY.md
|-- HEARTBEAT.md
|-- MULTI_AGENTS.md
|-- multi-agent/
|   |-- README.md
|   |-- ARCHITECTURE.md
|   `-- agent-console-mvp/
|-- memory/
`-- TOOLS.md
```

## Quick start

1. Read `AGENTS.md` for workspace rules.
2. Read `SOUL.md` and `USER.md` for behavior and user preferences.
3. Read `MULTI_AGENTS.md` for routing and specialist roles.
4. Check `memory/` and `MEMORY.md` for continuity context.

## Run the Agent Console MVP

```bash
cd multi-agent/agent-console-mvp
npm install
npm run dev
```

Then open `http://localhost:3799`.

## Notes

- This is an evolving personal workspace, not a polished product distribution.
- Some files are operational state and may change frequently.

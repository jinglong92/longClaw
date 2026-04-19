# Architecture Boundary

This document clarifies the division of responsibilities between the
OpenClaw runtime, the longClaw workspace and the new sidecar layer introduced
in the first phase of the refactoring.  Understanding these boundaries
ensures that enhancements are implemented in the correct place and that
future migrations remain low risk.

## OpenClaw Runtime (host)

The OpenClaw runtime is the core process that executes agent turns,
evaluates hooks and manages session lifecycles.  It is provided by the
underlying platform and **must not be modified** by the longClaw project.
Runtime updates are controlled by the upstream project; longClaw should
interact with the runtime only through public hook interfaces and
supported configuration files.

Responsibilities:

* Exposes hook entry points via `.claude/settings.json`.
* Manages session state, agent scheduling and tool execution.
* Owns the definition of AGENTS.md, MULTI_AGENTS.md, CTRL_PROTOCOLS.md and
  DEV_LOG.md.

## longClaw Workspace

The workspace layer is a set of configuration and data files that sits
alongside OpenClaw.  It defines custom agents, skills, workflows and
settings for a particular deployment.  It is where most integration work
occurs, and it is subject to change by users and developers.

Responsibilities:

* Defines agent and multi‑agent specifications (`AGENTS.md`,
  `MULTI_AGENTS.md`).
* Provides protocol files (`CTRL_PROTOCOLS.md`) and developer logs
  (`DEV_LOG.md`).
* Supplies `.claude/settings.json` to wire hooks into the sidecar.
* Houses memory files such as `heartbeat-state.json`.

## Runtime Sidecar

The **runtime sidecar** is a separate Python package introduced by this
project to extend longClaw without modifying the host runtime.  It runs in
the same process as the hooks but maintains its own state and logic.  The
sidecar adheres to the **workspace‑first, sidecar‑second, runtime‑fork‑last**
principle: only when an extension cannot be achieved via workspace
configuration should it be implemented in the sidecar, and only if that is
insufficient would a runtime fork be considered (but such a fork is out of
scope for this phase).

Responsibilities:

* Implements a **hook dispatcher** (`hook_dispatcher.py`) that consolidates
  multiple shell scripts into a single Python entry point.  The `.claude`
  configuration calls into this dispatcher for each hook event.
* Provides a lightweight **event bus** and plugin system (`event_bus.py` and
  `plugins/`) to handle SessionStart, PostCompact, FileChanged and
  PreToolUse events.
* Maintains a **session ledger** using a local SQLite database to record
  minimal session and tool metadata.  This ledger is not a replacement for
  the OpenClaw session store; it supplements it with extra auditing data.
* Supplies **doctor** and **status** scripts to report on environment
  health and ledger statistics.

The sidecar deliberately avoids dependence on OpenClaw internals.  It uses
only stable interfaces (hooks and file conventions) and stores its own
state separately.  Should the sidecar become unnecessary or obsolete it can
be removed without impacting the host.
# Migration Roadmap

This document outlines the migration path for integrating the longClaw
runtime sidecar.  The goal of this phase is to introduce a minimum set of
infrastructure while keeping the changes reversible and minimally
intrusive.

## Phase 1 – Foundation (this release)

* **Hook Dispatcher**: Consolidate disparate shell scripts into a single
  Python dispatcher.  Update `.claude/settings.json` to forward
  SessionStart, PostCompact, FileChanged and PreToolUse events to
  `runtime_sidecar/hook_dispatcher.py`.  The dispatcher uses a plugin
  architecture to ensure extensibility and graceful degradation.
* **Session Ledger**: Introduce a local SQLite database (`memory/state.db`)
  that tracks session metadata, route decisions, tool events and notes.
  Provide simple writers/readers for recording events.  This ledger is
  supplementary; it does not replace OpenClaw’s internal session
  management.
* **Doctor & Status**: Add `longclaw-doctor` to perform environment
  diagnostics and `longclaw-status` to summarise the ledger.  These
  commands validate file presence, configuration and database health.
* **Documentation**: Create boundary, roadmap and compatibility
  documentation to clarify roles and future plans.  Update the README with
  instructions for using the sidecar.

## Phase 2 – Enhancements (proposed)

* **Jobs and Process Registry**: Build on the ledger to support
  background tasks (cron‑like jobs) and a process registry.  This would
  allow long‑running workflows to be monitored without embedding that
  logic in the runtime.
* **Skill Registry**: Formalise how custom skills are discovered and
  registered.  Introduce a registry that can be queried via the sidecar.
* **Doctor Extensions**: Expand the doctor to validate the presence and
  correctness of workflows, skills and memory configuration.  Add more
  nuanced checks beyond file existence.
* **Full‑Text Search**: Upgrade the session ledger to use SQLite FTS5
  indexes, enabling more powerful searching via `tools/session_search.py`.
* **External Memory Providers**: Investigate adding pluggable memory
  providers (e.g. S3, databases) while maintaining the default local
  behaviour.  This must respect the workspace‑first principle and only
  extend if local storage is insufficient.

## Not in Scope (explicitly deferred)

* Complete cron platform or complex scheduling subsystem.
* Broad external memory provider integrations.
* Modifications to the OpenClaw runtime itself.
* Major directory refactoring of the existing repository.

The roadmap emphasises incremental progress.  Each phase builds on the
previous one while preserving the ability to roll back.  Feedback from
users and maintainers will inform prioritisation of future work.
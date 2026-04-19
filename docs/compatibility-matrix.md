# Compatibility Matrix

The following table summarises the current dependencies and assumptions of
the runtime sidecar implementation.  It helps users understand what
environment is required and which components remain coupled to
OpenClaw.

| Component/Requirement        | Notes |
|-----------------------------|-------|
| **Operating System**        | Tested on macOS (Apple Silicon and Intel) and Linux.  Windows is untested. |
| **Python Version**          | Python 3.8 or newer.  Uses standard library only; no external dependencies. |
| **OpenClaw**                | The sidecar requires a functioning OpenClaw runtime to execute hooks.  It does not modify or replace the runtime. |
| **.claude/settings.json**   | Must be present and configured to invoke `runtime_sidecar/hook_dispatcher.py`. |
| **memory/state.db**         | Created automatically on first use.  Can be overridden via the `LONGCLAW_STATE_DB` environment variable. |
| **memory/heartbeat-state.json** | Optional.  If present, must contain valid JSON for heartbeat checks. |
| **Agent/Protocol Files**    | `AGENTS.md`, `MULTI_AGENTS.md`, `CTRL_PROTOCOLS.md`, `DEV_LOG.md` should exist in the repository root. |
| **Tools**                   | The presence of `tools/memory_search.py` is optional.  The new `tools/session_search.py` is provided by this release. |
| **macOS vs Linux**          | Both platforms are supported; path handling uses `os.path` functions.  Use caution when overriding `LONGCLAW_STATE_DB` on different filesystems. |
| **Manual Installation Steps** | None required beyond updating `.claude/settings.json` and ensuring Python 3 is available.  The sidecar is self‑contained. |
| **Permissions**             | The process must have permission to create the `memory` directory and write to the state database file. |

If any of these assumptions do not hold, the sidecar may not function
correctly.  The `longclaw-doctor` script can help identify missing
files or incompatible configurations.
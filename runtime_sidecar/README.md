# runtime_sidecar

The `runtime_sidecar` package contains the non‑intrusive infrastructure layer for
longClaw.  It runs alongside the existing OpenClaw runtime and provides a
discrete place to extend behaviour without modifying the host.  The sidecar
design obeys the **workspace‑first, sidecar‑second, runtime‑fork‑last**
principles described in the project guidelines.

This package is not a replacement for OpenClaw – it is a set of modules that
enable hook dispatching, session ledger persistence and health reporting.  All
functionality here can be removed without breaking the core longClaw
workflows.

Key components:

* **`hook_dispatcher.py`** – an entry point that receives hook events from the
  `.claude/settings.json` hooks and dispatches them to plugin handlers.  It
  encapsulates all hook logic so the JSON configuration stays simple.
* **`event_bus.py`** – a lightweight event bus that loads plugin handlers and
  dispatches events.  It ensures that one failing plugin does not break the
  entire hook chain.
* **`hook_events.py`** – simple definitions for known hook event names and
  their payload structure.
* **`plugins/`** – small modules implementing specific hook behaviours
  (SessionStart, PostCompact, FileChanged, PreToolUse).  Each plugin exposes a
  `handle_event()` function that receives context and returns a result.
* **`state/`** – a minimal SQLite ledger used to capture session and tool
  metadata.  It should not be confused with OpenClaw’s own session store.
* **`doctor/`** – checks and diagnostics used by the `longclaw‑doctor` script.
* **`logging/`** – a thin wrapper over the Python logging module to provide
  uniform logging for the sidecar.

This directory is intentionally narrow in scope.  New features should
concentrate on expanding this sidecar rather than modifying the host runtime.
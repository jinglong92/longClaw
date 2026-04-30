import { t as definePluginEntry } from "../../plugin-entry-DyZc6JGI.js";
import { execFile } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// Resolve longClaw root: extensions/longclaw-sidecar/ -> ../../
const __dirname = dirname(fileURLToPath(import.meta.url));
const LONGCLAW_ROOT = resolve(__dirname, "../..");
const DISPATCHER = resolve(LONGCLAW_ROOT, "scripts/hooks/hook_dispatcher_post_tool_use.sh");

function dispatchToSidecar(event, ctx) {
  const payload = JSON.stringify({
    tool_name: event.toolName ?? ctx.toolName ?? "unknown",
    output: typeof event.result === "string" ? event.result : JSON.stringify(event.result ?? ""),
    session_id: ctx.sessionId ?? ctx.sessionKey ?? "openclaw-unknown",
    run_id: ctx.runId ?? event.runId,
    tool_call_id: ctx.toolCallId ?? event.toolCallId,
    duration_ms: event.durationMs ?? null,
    error: event.error ?? null,
  });

  // fire-and-forget: pipe payload to shell script which forwards to python sidecar
  const child = execFile(
    "bash",
    [DISPATCHER],
    { env: { ...process.env, LONGCLAW_ROOT } },
    (err) => {
      if (err) {
        process.stderr.write(`[longclaw-sidecar] dispatcher error: ${err.message}\n`);
      }
    }
  );
  child.stdin?.end(payload);
}

var plugin = definePluginEntry({
  id: "longclaw-sidecar",
  name: "longClaw Sidecar",
  description: "Bridges OpenClaw tool lifecycle events to the longClaw sidecar ledger.",
  register(api) {
    api.on("after_tool_call", (event, ctx) => {
      dispatchToSidecar(event, ctx);
    });
  },
});

export { plugin as default };

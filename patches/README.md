# patches

Reapply after `openclaw` upgrade (which overwrites `/opt/homebrew/lib/node_modules/openclaw/dist/**`).

## openclaw-deepseek-thinking.patch

Purpose: force DeepSeek V4 (openai-completions path) into non-thinking mode so it stops returning `reasoning_content`, and prevent pi-ai from replaying `reasoning_content` on subsequent turns (which would break DeepSeek's thinking-state contract).

Applies to:
`/opt/homebrew/lib/node_modules/openclaw/dist/extensions/google/node_modules/@mariozechner/pi-ai/dist/providers/openai-completions.js`

Reapply:

```bash
patch -p0 < ~/.openclaw/workspace/patches/openclaw-deepseek-thinking.patch
```

Companion config (already in `~/.openclaw/openclaw.json`):

```json
"models": [
  { "id": "deepseek-v4-pro",   "name": "DeepSeek V4 Pro",
    "compat": { "thinkingFormat": "deepseek", "supportsReasoningEffort": true } },
  { "id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash",
    "compat": { "thinkingFormat": "deepseek", "supportsReasoningEffort": true } }
]
```

Behavior:
- Default outbound body includes `"thinking": {"type": "disabled"}`.
- If caller passes `reasoningEffort`, it flips to `"enabled"` and pi-ai additionally sends `reasoning_effort` (because `supportsReasoningEffort: true`).
- Assistant-message replay skips re-injecting `reasoning_content`.

Backup of pre-patch file: `~/.openclaw/openclaw.json.pre-deepseek-thinking-patch`

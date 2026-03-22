# HEARTBEAT.md

## Daily AI Intel Push (high priority)

When heartbeat runs between 08:30-10:30 (Asia/Shanghai), prepare and send one daily digest to the user if not sent today.

### Scope (must cover)
1. Industry leaders' latest views on AI progress/future trends
2. Key updates from:
   - Andrej Karpathy
   - OpenAI
   - Google AI
   - Anthropic
3. Technical focus:
   - AgenticRL
   - LLM for OR
   - LLM-as-Algorithm-Designer (EoH, ReEvo and follow-ups)

### Output requirements
- Include source links and timestamps
- For papers: include paper link + code repo link (if available)
- Keep concise, structured, and actionable

### De-duplication rule
- Track last sent date in `memory/heartbeat-state.json`
- If already sent today, do not resend unless there is major breaking update

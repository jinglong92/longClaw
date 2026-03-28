# HEARTBEAT.md

## Daily AI Intel Push (high priority)

When heartbeat runs, enforce fixed deadline: send the digest before 09:30 (Asia/Shanghai) each day. If missed, send at first available heartbeat after 09:30.

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
- Normal case is exactly one push per day

---

## Daily LeetCode Push (10:00 Asia/Shanghai)

### Goal
Send **one** interview problem + concise solution every day at/after 10:00 (Asia/Shanghai).

### Output format
1. Problem title + LeetCode number
2. Difficulty + pattern tag
3. Python reference answer (typed, concise)
4. Complexity (time/space)
5. One common pitfall

### Scheduling & de-duplication
- Use `memory/heartbeat-state.json` key `lastChecks.leetcodeDaily` to track last sent date.
- If today has already been sent, do not resend.
- If 10:00 is missed, send at first available heartbeat after 10:00.
- Prefer medium/high-frequency interview questions; avoid repeating within 14 days.

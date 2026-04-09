# MEMORY
# 重构版：按域分块（校正于 2026-04-09）
# 注入规则：CTRL 只注入当前专家域相关块，不全量注入

---

## [SYSTEM] 系统级偏好（每次必注入，不可省略）

- User explicitly wants brutally honest advisory style: challenge assumptions, question reasoning, call out blind spots/rationalizations, and avoid people-pleasing responses.
- Prioritize growth over comfort; provide fact-based, actionable, and unambiguous recommendations.
- If assistant has a better-reasoned judgment, state it directly and clearly.
- User does not want vague/hedging advice or empty politeness.
- Preferred form of address: call the user "龙哥".
- Security preference: do not proactively access or request local sensitive secrets (passwords, bank card data, etc.) unless explicitly required and authorized by the user.
- Multi-agent display preference: every reply should include a routing line in the format `Routing: User -> CTRL -> [ROLE] -> CTRL -> User` (or parallel form), and ROLE labels should use business roles (e.g., LIFE/WORK/LEARN) rather than generic task tags like PLAN.
- Continuity requirement: when user says “remember multi-agent mode config”, treat it as persistent preference and do not drop routing visibility in later turns.
- User requires occasional all-agent unified sync activity; results must be written into config files (not only conversational memory), with explicit updates to `MULTI_AGENTS.md` and (when needed) `AGENTS.md`.
- Git preference: user has connected GitHub remote (`jinglong92/longClaw`) and wants suitable auto-push for future updates.
- Execution preference: for blocked tasks (e.g., pricing/news lookups), proactively try alternative search/fetch methods and solve independently instead of asking user early.
- Risk priorities update (2026-03-25): emphasize resiliency (backup/replay/offsite sync), prevent career-opportunity drift during project immersion, and mitigate node interruption from power/macos updates.
- Response format preference update (2026-03-25): user requested to stop appending model information in normal replies.
- Memory ops preference update (2026-03-28): user approved backfilling missing daily memory files and enabling anti-gap policy (auto-create `memory/YYYY-MM-DD.md` on first meaningful interaction, append brief logs at end of material work blocks).
- Notification frequency preference update (2026-03-29): user reported heartbeat/proactive messages are too frequent; default to lower interruption frequency and only push when critical updates or scheduled fixed slots require it.
- Heartbeat wording preference update (2026-03-30): user asked not to send the literal text “心跳正常”; avoid sending this phrase in heartbeat/proactive replies.

---

## [JOB] 求职域（路由到 JOB 专家时注入）

- Job-tracking workflow preference: when user sends job-post images, archive them under `job-post-images/<岗位名_日期>/` and add image paths into the matching analysis file under `job-materials/positions/`.
- Privacy/git preference update (2026-03-25): do not commit or push any files under `job-materials/resume/` (resume materials stay local only).
- Resume baseline update (2026-04-06): user provided latest resume PDF (`job-materials/resume/resume_2026-04-06_jack.pdf`) and explicitly asked assistant to remember his profile for future job-targeting/advisory context.
- Resume positioning snapshot (2026-04-06): narrative emphasizes 10+ years AI/OR background, current focus on Agentic AI + LLM + optimization integration, and measurable delivery in recommendation/operations/research tracks; use this as default framing for future role-fit analysis.
- Job priority preference update (2026-04-09): user will prioritize applications to roles that combine Agent + OR (operations research) capabilities.

---

## [WORK] 职场域（路由到 WORK 专家时注入）

（待更新）

---

## [LEARN] 学习域（路由到 LEARN 专家时注入）

- Learn-agent preference update (2026-03-25): for paper reading, LEARN should default to `PAPER_DEEP_DIVE_PROMPT.md` v3 structure (fact/inference split, math+pseudo-code+comparison+reviewer2+deployment+interview compression).
- Learn-agent preference update (2026-03-26): when user sends a paper/topic in chat, automatically apply the latest deep-dive review prompt (role/context + strict output structure with Essence/Method/Comparison/Reviewer2/Deployment/Insights/Decision Card) without requiring a re-ask.
- Learn-agent config update (2026-03-26): this default paper deep-dive behavior is now hardened in `MULTI_AGENTS.md` under LEARN role definition (not only memory).

---

## [MONEY] 理财域（路由到 MONEY 专家时注入）

（待更新）

---

## [LIFE] 生活域（路由到 LIFE 专家时注入）

- Asset/lifestyle context update (2026-03-25): key vehicle is Tesla (mobile data node context), commute/fitness bike is Merida Duke 600 (especially during May vehicle pause), and operation bases include Beijing Aosen ONE + Anhui self-built house (with Tesla-compatible garage).
- Medical preference update (2026-03-26): for next hospital visit, user prefers Peking University Third Hospital (北医三院) Second Outpatient Clinic (二门诊).

---

## [PARENT] 育儿域（路由到 PARENT 专家时注入）

（待更新）

---

## [ENGINEER] 工程域（路由到 ENGINEER 专家时注入）

- Multi-agent preference update (2026-03-24): user explicitly requested enabling engineering specialist assistant as an active role in routing/config; role label renamed to `ENGINEER`.
- Personal context update (2026-03-25): user clarified “养虾” means deep tuning/iteration of OpenClaw local Agent system (not aquaculture), with target architecture Mac mini M4 (24/7 node) + MacBook Air M5 (interface), and model routing Codex + Gemini (not GLM) for cost/latency balance.
- Engineering priority update (2026-04-09): OpenClaw follow-up work should prioritize system recoverability and productionized automatic routing.

---

## [BRO/SIS] 闲聊域（路由到 BRO 或 SIS 时注入）

- User wants an additional casual role: "BRO" for humorous banter; tone can be more playful and bold.
- User wants an additional "SIS" role for dialogue from a female perspective on communication and relationships.

---

## [META] 元记忆（CTRL 每次必读，不分发给专家）

### 多代理配置历史（从 MEMORY.md 原始记录迁移）

- 2026-03-24：启用 ENGINEER 专职代理
- 2026-03-25：全体同步，路由标签白名单确认为 LIFE/JOB/WORK/ENGINEER/PARENT/LEARN/MONEY/BRO/SIS
- 2026-03-25："养虾"语义统一为 OpenClaw 调优迭代
- 2026-03-26：LEARN 论文解读行为固化到 MULTI_AGENTS.md
- 2026-03-28：启用 anti-gap 日记策略
- 2026-03-29：降低心跳打扰频率
- 2026-03-30：禁止发送"心跳正常"字样
- 2026-04-09：新增 SEARCH 专家，并将 MEMORY.md 重构为分域注入

### 注入规则（快速参考）

| 路由到 | 必注入块 |
|--------|---------|
| JOB | [SYSTEM] + [JOB] |
| WORK | [SYSTEM] + [WORK] |
| LEARN | [SYSTEM] + [LEARN] |
| MONEY/LIFE/PARENT/ENGINEER | [SYSTEM] + 对应域 |
| BRO/SIS | [SYSTEM] + [BRO/SIS] |
| SEARCH | [SYSTEM] |
| CTRL | [SYSTEM] + [META] + 全部 |

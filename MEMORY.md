# MEMORY

## User communication preferences
- User explicitly wants brutally honest advisory style: challenge assumptions, question reasoning, call out blind spots/rationalizations, and avoid people-pleasing responses.
- Prioritize growth over comfort; provide fact-based, actionable, and unambiguous recommendations.
- If assistant has a better-reasoned judgment, state it directly and clearly.
- User does not want vague/hedging advice or empty politeness.
- Preferred form of address: call the user "龙哥".
- User wants an additional casual role: "BRO" for humorous banter; tone can be more playful and bold.
- User wants an additional "SIS" role for dialogue from a female perspective on communication and relationships.
- Security preference: do not proactively access or request local sensitive secrets (passwords, bank card data, etc.) unless explicitly required and authorized by the user.
- Multi-agent display preference: every reply should include a routing line in the format `Routing: User -> CTRL -> [ROLE] -> CTRL -> User` (or parallel form), and ROLE labels should use business roles (e.g., LIFE/WORK/LEARN) rather than generic task tags like PLAN.
- Continuity requirement: when user says “remember multi-agent mode config”, treat it as persistent preference and do not drop routing visibility in later turns.
- User requires occasional all-agent unified sync activity; results must be written into config files (not only conversational memory), with explicit updates to `MULTI_AGENTS.md` and (when needed) `AGENTS.md`.
- Git preference: user has connected GitHub remote (`jinglong92/longClaw`) and wants suitable auto-push for future updates.
- Execution preference: for blocked tasks (e.g., pricing/news lookups), proactively try alternative search/fetch methods and solve independently instead of asking user early.
- Job-tracking workflow preference: when user sends job-post images, archive them under `job-post-images/<岗位名_日期>/` and add image paths into the matching analysis file under `job-materials/positions/`.
- Multi-agent preference update (2026-03-24): user explicitly requested enabling engineering specialist assistant as an active role in routing/config; role label renamed to `ENGINEER`.
- Multi-agent unified sync (2026-03-25): all specialist roles completed a consistency sync; routing/label whitelist confirmed as `LIFE/JOB/WORK/ENGINEER/PARENT/LEARN/MONEY/BRO/SIS`.
- Response format preference update (2026-03-25): user requested to stop appending model information in normal replies.
- Privacy/git preference update (2026-03-25): do not commit or push any files under `job-materials/resume/` (resume materials stay local only).
- Learn-agent preference update (2026-03-25): for paper reading, LEARN should default to `PAPER_DEEP_DIVE_PROMPT.md` v3 structure (fact/inference split, math+pseudo-code+comparison+reviewer2+deployment+interview compression).
- Personal context update (2026-03-25): user clarified “养虾” means deep tuning/iteration of OpenClaw local Agent system (not aquaculture), with target architecture Mac mini M4 (24/7 node) + MacBook Air M5 (interface), and model routing Codex + Gemini (not GLM) for cost/latency balance.
- Risk priorities update (2026-03-25): emphasize resiliency (backup/replay/offsite sync), prevent career-opportunity drift during project immersion, and mitigate node interruption from power/macos updates.
- Asset/lifestyle context update (2026-03-25): key vehicle is Tesla (mobile data node context), commute/fitness bike is Merida Duke 600 (especially during May vehicle pause), and operation bases include Beijing Aosen ONE + Anhui self-built house (with Tesla-compatible garage).

# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Role In The System

`TOOLS.md` is the bridge between generic workflows and this actual workspace.

Separation of concerns:

- `SKILL.md`: reusable workflow logic
- `TOOLS.md`: local capability bindings, aliases, paths, caveats, and operator notes
- `AGENTS.md`: safety and execution policy
- `MULTI_AGENTS.md`: routing and CTRL protocol

If a skill answers "what should be done", `TOOLS.md` should answer:

- with which local command or app
- against which local path or service
- under which caveat or limitation
- with which fallback if the preferred tool is absent

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

Also include:

- local command aliases that skills rely on
- which public-web or browser tools are actually available
- local workspace paths used by recurring workflows
- tool-specific failure modes worth remembering
- environment constraints that affect readback, patching, testing, or browser automation

## Skill Bindings

Use this section to bind reusable skills to local execution reality.

Suggested format:

```markdown
### <skill-name>
- Primary toolchain:
- Workspace paths:
- Required binaries:
- Known caveats:
- Verification command:
```

Current skill families in this workspace:

- `skills/engineer/agent-review`
- `skills/engineer/research-build`
- `skills/engineer/research-execution-protocol`
- `skills/job/jd-analysis`
- `skills/learn/paper-deep-dive`
- `skills/meta/session-compression-flow`
- `skills/meta/skill-safety-audit`
- `skills/search/fact-check-latest`
- `skills/search/public-evidence-fetch`
- `skills/multi-agent-bootstrap`

## Capability Registry Template

```markdown
### Browser / Web
- Public web fetch:
- Browser automation:
- Notes:

### Git / Repo
- Default remote:
- Push policy:
- Notes:

### Node / Python / CLI
- Node:
- Python:
- Key CLIs:
- Notes:
```

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Maintenance Rule

When a skill repeatedly fails or degrades because of this machine's setup:

- update `TOOLS.md`
- do not patch the shared skill first unless the workflow itself is wrong

When a workflow changes for everyone:

- update the relevant `SKILL.md`
- keep `TOOLS.md` focused on local bindings only

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

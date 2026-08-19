---
slug: unconditional-5e-gates
title: Make agent/skill kit-gates unconditional 5e
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: 5e-native-fork
blockedBy: [hardcode-5e-ruleset]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T14:10:45Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Rewrite every "only when the active kit is dnd5e" / "for non-D&D kits..."
conditional as unconditional 5e instruction. Files: `.claude/agents/
monster-manual.md`, `rules-master.md`, `gear-master.md` (if gated),
`spell-caster.md` (if gated), `create-character.md`,
`.claude/commands/create-character.md`, `.claude/skills/gm-skills/SKILL.md`,
any other gm-* skills carrying kit conditionals, and the project `CLAUDE.md`
(kit language in the header, Action Router, Death Protocol SWAP, and
specialist-agents sections). Book-grounded ordering stays (imported D&D module
text still wins over generic SRD), but the fallback is always the 5e API, never
"the generic core's terms." Update claiming docs same-commit.

## Acceptance criteria

- [ ] `grep -ri "kit is dnd5e\|non-D&D kit\|active kit" .claude CLAUDE.md` returns no conditional gates (informational mentions of "5e" fine)
- [ ] Each API-backed agent states its dnd5eapi path as mandatory, not conditional
- [ ] CLAUDE.md no longer describes World Kit as per-book variable rules
- [ ] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

hardcode-5e-ruleset

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]

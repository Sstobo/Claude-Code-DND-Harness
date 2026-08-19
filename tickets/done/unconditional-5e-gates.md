---
slug: unconditional-5e-gates
title: Make agent/skill kit-gates unconditional 5e
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: 5e-native-fork
blockedBy: [hardcode-5e-ruleset]
claimedBy: ss-5efork
claimedAt: 2026-08-19T15:20:53Z
changedFiles: [.claude/agents/monster-manual.md, .claude/agents/rules-master.md, .claude/agents/gear-master.md, .claude/agents/spell-caster.md, .claude/agents/create-character.md, .claude/commands/create-character.md, .claude/skills/gm-combat/SKILL.md, .claude/skills/gm-conditions/SKILL.md, .claude/skills/gm-craft/SKILL.md, .claude/skills/gm-dungeon/SKILL.md, .claude/skills/gm-levelup/SKILL.md, .claude/skills/gm-skills/SKILL.md, .claude/skills/gm-social/SKILL.md, .claude/skills/gm-spellcasting/SKILL.md, tests/test_lean_core.py, tests/test_kit_aware_character_creation.py, CLAUDE.md, docs/conventions/lean-core-and-skill-routing.md]
resolution: kit gates removed everywhere — agents, all 8 skills, CLAUDE.md unconditionally 5e; enforcement tests inverted with positive anchors
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T15:45:23Z
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

- [x] `grep -ri "kit is dnd5e\|non-D&D kit\|active kit" .claude CLAUDE.md` returns no conditional gates (informational mentions of "5e" fine)
- [x] Each API-backed agent states its dnd5eapi path as mandatory, not conditional
- [x] CLAUDE.md no longer describes World Kit as per-book variable rules
- [x] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

hardcode-5e-ruleset

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
- 2026-08-19T15:20:53Z  claimed  [ss-5efork]
- 2026-08-19T15:27:45Z  doc-grounding confirmed  [ss-5efork]

### 2026-08-19T15:37:19Z — verified [ss-5efork]
grep gate clean (no kit conditionals in .claude or CLAUDE.md). test_lean_core inverted to enforce the new invariant (12 passed); test_kit_aware_character_creation: 2 kit tests inverted into real guards, 3 removed, others untouched (21 passed combined). Full suite: only the known pre-existing failure. Scope extension (kit-aware test file) granted mid-ticket.
- 2026-08-19T15:37:19Z  verified → in-review  [ss-5efork]

### 2026-08-19T15:41:18Z — fail [review-5e-gates]
reviewed: needs-changes (prose clean; tests weak)
- test_judgment_skills_state_five_e_tables_outright vacuous (negative-only, subsumed by the all-skills guard); needs positive anchors (DC ladder, social DCs, Paralyzed).
- test_mechanics_skills_are_unconditionally_active negative-only; nothing asserts death saves/CR-XP/XP table/slot table still present.
- test_world_kit_exposes_kit_identity tautological and still accepts "custom"; must assert kit() == "dnd5e" exactly.
- lean-core-and-skill-routing.md missing /lib/world_kit.py in sources: (its load-bearing claim now depends on it).
Cross-ticket notes: session_manager KIT block is dead output; docs/log.md:47 still describes per-book kit — filed for sweep.
- [x] (review) every negative no-kit-gate assertion paired with a positive 5e-content assertion
- [x] (review) test_world_kit_exposes_kit_identity asserts kit() == "dnd5e" exactly
- [x] (review) lean-core-and-skill-routing.md lists /lib/world_kit.py in sources:

### 2026-08-19T15:44:24Z — verified (fix round) [ss-5efork]
FIVE_E_ANCHORS positive assertions added per skill (literal current strings); kit identity asserted == dnd5e exactly; world_kit.py added to convention doc sources. test_lean_core 13 passed; suite 1 known pre-existing failure. Followup review dispatched.
- 2026-08-19T15:44:24Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T15:45:23Z — pass [review-5e-gates]
reviewed: perfect (followup round 2)
Notes: optional future hardening — guard tests match fixed phrases; a freshly-worded re-gate could slip past (assert on conditional constructions near tables if it ever matters). Pre-existing okf error in tool-wrapper-contract.md (cites a test file that never existed in this fork) noted for a docs pass.
- 2026-08-19T15:45:23Z  done → committed  [ss-5efork]

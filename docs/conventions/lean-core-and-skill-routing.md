---
type: Convention
title: Lean core, skills on demand
description: Why CLAUDE.md stays thin, what the router is allowed to keep inline, and why no skill carries a kit guard in this 5e-only fork.
sources:
  - { resource: /tests/test_lean_core.py }
  - { resource: /.claude/skills/gm-combat/SKILL.md }
  - { resource: /.claude/skills/gm-skills/SKILL.md }
  - { resource: /.claude/skills/gm-craft/SKILL.md }
  - { resource: /lib/session_manager.py }
  - { resource: /lib/world_kit.py }
generated: { by: claude-opus-5, at: 2026-08-19T17:48:27Z }
verified: { by: claude-opus-5, at: 2026-08-19T17:55:42Z }
---

# Lean core, skills on demand

`CLAUDE.md` is always in context; the eight `gm-*` Skills are not. The core routes; the
Skills hold the mechanics. The alternative — one large always-on ruleset — spends the
model's attention on rules that have nothing to do with the current beat, and it is what
this repo migrated *away* from (the pre-lean `CLAUDE.md` is 1227 lines, in git history).

## The line between router and skill

**Router keeps:** the core loop, persist-before-narrate, the action router table, movement,
output format, the search guide, the memory policy, the golden rules, and stakes/death.
These are needed *every* turn or needed to decide *which* skill to load.

**Skills hold:** anything you need only in a specific moment — combat resolution, spell
slots, condition tables, XP thresholds, dungeon procedure, narration craft.

The practical test is the one the router itself fails first: **an XP-by-CR table inline in
`CLAUDE.md` is the smell.** `test_lean_core.py:35` asserts `"25,000" not in text` for
exactly that reason.

## Enforcement point

`tests/test_lean_core.py` is a real guard, and unusually specific for a documentation rule:

- `CLAUDE.md` must be **under 320 lines** and contain `LEAN CORE`
- it must still contain the load-bearing sections by name (Core Loop, Action Router,
  Movement, Output Format, Search Guide, Auto Memory Policy, Golden Rules, `uv run python`)
- it must name **all eight** skills, so a skill can't be orphaned by a router edit
- every skill must exist with matching `name:` frontmatter
- `gm-craft` must still contain `"Yes, and"` and `"Persist before narrating"` — the one
  content assertion, guarding what the test calls the soul

Adding a skill without adding it to `ALL_SKILLS` and the router leaves it unroutable and
untested.

## Every skill is unconditionally 5e — the kit guard is gone by design

This fork plays D&D 5e and nothing else. `lib/world_kit.py` is hardcoded: `WorldKit.kit()`
always returns `"dnd5e"`, there is no `ruleset.json`, no custom kits, and no generic-core
fallback for mechanics. Skills therefore carry no gate: `gm-combat`, `gm-levelup`, and
`gm-spellcasting` open straight into hit dice, spell slots, the XP table, and death saves,
and `gm-skills`, `gm-social`, and `gm-conditions` state their DC ladders and condition
lists outright.

Enforcement inverted with the fork. `test_mechanics_skills_are_unconditionally_active` and
`test_no_skill_carries_kit_guard_language` fail if any skill reintroduces "KIT GUARD",
"active kit", "World Kit", `ruleset.json`, "non-D&D", "generic core", or "kit-aware", and
`test_judgment_skills_state_five_e_tables_outright` fails on the old conditional phrasings.
The same rule reaches the API-backed agents: their book-grounded ordering survives, so an
imported module's own text still beats generic SRD data, but the dnd5eapi fallback is
stated as mandatory rather than kit-conditional.

(History, for anyone reading a stale branch: an earlier design let each book ship its own
rules on a generic core, and three skills opened with a STEP-0 read of the scene-context
KIT block that closed the skill unless the kit was `dnd5e`. That guard was an instruction a
model follows, not an interlock, and it is now removed rather than merely unused — a
lingering guard would tell the model to close a skill on a condition that can never be
true.)

`gm-dungeon` and `gm-craft` were never rules-bearing and are unaffected beyond dropped
kit-awareness phrasing.

## Related

- [A play turn](../flows/play-turn.md) — where routing happens in the loop

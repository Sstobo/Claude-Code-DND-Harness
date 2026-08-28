---
slug: sheet-5e-completeness
title: The sheet is missing most of what 5e needs — proficiency bonus, slots, hit dice, rest
category: enhancement
kind: hitl
priority: p1
lane: agent
parentPrd: readme-promises
blockedBy: [sheet-validate-on-write]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: 0
implementer: null
createdAt: 2026-08-27T00:00:00Z
updatedAt: 2026-08-27T00:00:00Z
---

## Parent

readme-promises — prds/readme-promises.md

## Category

enhancement

## What to build

README:5 promises "Every campaign runs on real D&D 5e." `lib/game_core.py:5-6`
states the opposite design intent in a comment: "NO D&D 5e assumptions live here:
no fixed ability names, no level-20 cap, no spell slots." The kit abstraction won
and the sheet inherited its silence. Attack rolls really do resolve against
stored AC, but almost everything upstream of the die lives only in the model's
head.

What a 5e sheet needs, against what this one carries:

| Needed | Status |
|---|---|
| Ability scores | `stats` — present 3/4 campaigns, empty on the live `dcc` PC |
| Proficiency bonus | **absent everywhere**; recomputed ad hoc inside `save_character.py:48`, never persisted |
| Saving throw proficiencies | **lost** — `saves` stores final numbers, not *which* are proficient, so it cannot be recomputed on level-up |
| Skill proficiencies | **lost** — same; `skills` is a number dict with no proficiency flag |
| Speed | **absent**; one dead reference at `lib/schemas.py:300` |
| Hit dice | **absent**; the class hit die is used once at creation (`save_character.py:27-35`) and never stored |
| Spell slots | **absent**, no code anywhere |
| Spells known | **no home** — dropped by the 21-key whitelist |
| Conditions | present on 1 of 4 sheets; PC path auto-inits at `lib/player_manager.py:972` |
| Death save state | on the combatant record only (`lib/combat_manager.py:360`), never on the sheet |
| Attunement | absent |
| Initiative, passive perception, senses, languages, resistances | absent |
| Short / long rest | **no mechanic at all** — `gm-player.sh` has no `rest` verb |

The two that hurt most in play: **saving throw and skill proficiencies are
unrecoverable** (storing the total instead of the proficiency means level-up
cannot recompute, so every level-up is the model re-deriving numbers by hand),
and **there is no rest**, so hit dice, slot recovery and exhaustion relief have
nowhere to happen.

This is `kind: hitl` because it is a scope decision, not just a fix: the harness
deliberately built a kit-agnostic core, and adding 5e fields to the sheet chooses
a direction. `tickets/prds/5e-native-fork.md` is the existing home for that
argument — read it before starting and reconcile.

## Acceptance criteria

- [ ] Decision recorded (in this ticket or the 5e-native PRD) on which fields become canonical
- [ ] `proficiency_bonus`, `speed`, and hit dice persist on the sheet rather than being recomputed
- [ ] `saves` and `skills` record *proficiency*, not only the final number, so level-up can recompute
- [ ] Spells and spell slots have a home on the sheet, and `/create-character`'s documented example stops being silently discarded
- [ ] `gm-player.sh rest short|long` exists and recovers hit dice / slots / exhaustion per 5e
- [ ] Death save state persists on the sheet, so a resume after a session boundary keeps the tally

## Out of scope

Encumbrance, crafting, downtime activities. Attunement can be a follow-up if
this ticket gets large.

## Verification

Lane: agent, then human sign-off on the scope decision.

## Blocked by

sheet-validate-on-write

---

## QA Reports

## History

- 2026-08-27T00:00:00Z  created → needs-triage  [readme-audit]

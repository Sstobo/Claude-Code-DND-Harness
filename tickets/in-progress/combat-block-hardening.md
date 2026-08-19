---
slug: combat-block-hardening
title: Harden _from_stat_block null fallbacks and XP coercion
category: bug
kind: afk
priority: p2
lane: agent
parentPrd: 5e-native-fork
blockedBy: []
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: null
implementer: null
createdAt: 2026-08-19T16:40:00Z
updatedAt: 2026-08-19T16:40:00Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

bug

## What to build

Cross-session review findings on lib/combat_manager.py (committed 1d596fa):
1. MED — `_from_stat_block` fallbacks (`block.get('hit_points', block.get('hp'))`
   and siblings for ac/cr/attacks) only fall back when the primary key is ABSENT,
   not null. A homebrew-adapted block with `{"armor_class": null, "ac": 17}`
   silently yields AC 10; `{"hit_points": None, "hp": 30}` drops HP (repro
   verified by the reporting reviewer). Fall back on None as well as absence.
2. LOW — `xp` persists unvalidated from the block; `int(c['xp'])` at `end()`
   crashes on `"1,100"` AFTER the fight, losing the summary. Coerce/validate at
   add_combatant time where the CLI has an error envelope.

## Acceptance criteria

- [ ] Null primary keys fall back to the alternate shape (hp/ac/cr/attacks); test with the reviewer's repro block
- [ ] Non-numeric xp rejected (or coerced) at add time with the clean envelope; end() cannot crash on stored xp
- [ ] test_combat_manager extended for both; suite passes (bar the environmental sibling-repo failure)

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T16:40:00Z  created → needs-triage (source: cross-session review, claude-code-dnd-harness-b7)  [ss-5efork]

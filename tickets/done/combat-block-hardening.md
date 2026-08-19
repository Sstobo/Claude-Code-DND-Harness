---
slug: combat-block-hardening
title: Harden _from_stat_block null fallbacks and XP coercion
category: bug
kind: afk
priority: p2
lane: agent
parentPrd: 5e-native-fork
blockedBy: []
claimedBy: ss-5efork
claimedAt: 2026-08-19T18:41:05Z
changedFiles: [lib/combat_manager.py, tests/test_combat_manager.py, .claude/skills/gm-combat/SKILL.md]
resolution: stat-block fallbacks null- and empty-tolerant, xp validated at add and reported when unreadable
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T16:40:00Z
updatedAt: 2026-08-19T19:09:15Z
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

- [x] Null primary keys fall back to the alternate shape (hp/ac/cr/attacks); test with the reviewer's repro block
- [x] Non-numeric xp rejected (or coerced) at add time with the clean envelope; end() cannot crash on stored xp
- [x] test_combat_manager extended for both; suite passes (bar the environmental sibling-repo failure)

## Verification

Lane: agent

## Blocked by

None.

---

## QA Reports

## History

- 2026-08-19T16:40:00Z  created → needs-triage (source: cross-session review, claude-code-dnd-harness-b7)  [ss-5efork]
- 2026-08-19T18:41:05Z  triaged → claimed  [ss-5efork]
- 2026-08-19T18:51:33Z  doc-grounding confirmed  [ss-5efork]

### 2026-08-19T18:59:43Z — verified [ss-5efork]
Repro verified live: null primaries fall back (AC 17, HP 30), "1,100" coerces to 1100. end() re-coerces stored xp and skips uncoercibles (legacy-save test). 24 combat tests green; suite only the environmental failure.
- 2026-08-19T18:59:43Z  verified → in-review  [ss-5efork]

### 2026-08-19T19:03:30Z — fail [review-combat-hardening]
reviewed: needs-changes (all reproduced by execution)
- MED :79 — AC fallback half-fixed: _pick commits to armor_class when non-null, then _ac_value can reduce it to None and the ac sibling is never consulted ([] or "17 (natural)" -> AC 10). Extraction must run per-candidate.
- LOW :78,82 — present-but-empty/zero primary shadows a populated sibling ({"hit_points":0,"hp":30} -> hp 0 dead-on-arrival; actions [] shadows attacks).
- LOW :64 — int(float('inf')) raises OverflowError which neither guard catches; json accepts bare Infinity -> raw traceback through the CLI.
- end() silently skips uncoercible legacy xp (enemy in defeated, absent from xp map, evidence destroyed by _save) — surface as xp_unreadable list.
- [x] (review) unparseable primary AC ([], "17 (natural armor)") resolves to the sibling — tested
- [x] (review) hp 0 / empty-actions primaries fall to populated siblings — tested
- [x] (review) xp Infinity returns the CLI envelope, not a traceback — tested at CLI layer
- [x] (review) end() reports xp_unreadable names instead of silent skips — legacy test updated

### 2026-08-19T19:07:31Z — verified (fix round) [ss-5efork]
Per-candidate AC extraction (unreadable primaries fall to sibling); _pick_populated for hp/actions only (0 xp/cr deliberately kept, pinned by test); non-finite xp rejected + both guards widened; xp_unreadable field on end(). 32 combat tests green; suite only the environmental failure. Followup review dispatched.
- 2026-08-19T19:07:31Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T19:09:15Z — pass [review-combat-hardening]
reviewed: perfect (followup round 2) — all four fixes verified by execution; xp_unreadable consumer added to gm-combat skill post-verdict (orchestrator-verified one-sentence doc edit).
Notes: future nit — both-keys-stringified AC ({"armor_class":"17 (natural)","ac":"17"}) still defaults to 10; no evidence such blocks occur.
- 2026-08-19T19:09:15Z  done → committed  [ss-5efork]

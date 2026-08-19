---
slug: spells-levelup-api
title: Spells, slots, and level-up from /classes API
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: 5e-native-fork
blockedBy: [unconditional-5e-gates, api-file-cache]
claimedBy: ss-5efork
claimedAt: 2026-08-19T15:45:42Z
changedFiles: [features/character-creation/api/get_class_levels.py, .claude/skills/gm-spellcasting/SKILL.md, .claude/skills/gm-levelup/SKILL.md, tests/test_lean_core.py]
resolution: casting resources and level-up content now fetched from the classes API — slots, features, ASIs; kit tables replaced by get_class_levels lookup
reviewRounds: 3
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T16:12:57Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Make the /classes API the source of truth for casting resources and
progression. `.claude/skills/gm-spellcasting/` resolves cast spells against
fetched spell data (`features/spells/get_spell.py`: level, damage, save,
components, concentration) and takes spell-slot tables from
`/classes/{class}/levels` instead of any inlined table in the skill.
`.claude/skills/gm-levelup/` pulls features, ASI levels, and slot changes for
the new level from `/classes/{class}/levels/{level}` instead of narrating from
memory; hit-dice-by-class may stay inlined (static, tiny). Add a small helper
script under `features/character-creation/api/` (or reuse an existing one) for
the class-levels lookup so skills call one command. Update claiming docs
same-commit.

## Acceptance criteria

- [x] gm-spellcasting instructs resolving spell effects from fetched data; its inlined slot table is replaced by the class-levels lookup
- [x] gm-levelup pulls level features/ASIs/slots from the API (demonstrated: wizard level 3 lookup returns correct slots and features)
- [x] One command exists to fetch `/classes/{class}/levels/{level}` and is referenced by both skills
- [x] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

unconditional-5e-gates, api-file-cache

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
- 2026-08-19T15:45:42Z  claimed  [ss-5efork]
- 2026-08-19T15:53:13Z  doc-grounding confirmed  [ss-5efork]

### 2026-08-19T16:02:23Z — verified [ss-5efork]
get_class_levels.py wizard 3 returns correct slots (4/2) + prof bonus; cleric 1 correct per implementer. gm-spellcasting slot table replaced with class-levels lookup (old heading absent); gm-levelup ceremony reads fetched features/ASIs. test_lean_core 13 passed with updated anchors; suite only pre-existing failure.
- 2026-08-19T16:02:23Z  verified → in-review  [ss-5efork]

### 2026-08-19T16:05:35Z — fail [review-spells-levelup]
reviewed: needs-changes
- HIGH gm-levelup:32,42 — ability_score_bonuses is a CUMULATIVE ASI total, not a per-level flag; instruction grants wizard ASIs at 5-7 and never after 8. Signal is the value increasing vs previous level, or "Ability Score Improvement" in features.
- MED gm-spellcasting:45 — "persist the spent slot with gm-player.sh" points at a nonexistent subcommand; either implement or state slots are narration-tracked.
- MED gm-levelup:43 — hardcoded "subclass at level 3" contradicts fetched features (wizard 2, cleric/sorc/warlock 1); let features drive it.
- LOW gm-spellcasting:42 — warlock Pact Magic short-rest recovery missing.
- LOW gm-spellcasting:35 — spells_known absent for prepared casters; name the prepared formula (mod + level).
- LOW get_class_levels.py:43 — bad level returns HTTP 400 not 404; friendly branch never fires.
- [x] (review) ASI detection uses features list or cumulative delta, never ==1
- [x] (review) slot persistence instruction points at a real mechanism or states narration-tracking
- [x] (review) subclass level driven by fetched features, not hardcoded 3
- [x] (review) warlock pact magic + prepared-caster formula named
- [x] (review) get_class_levels handles HTTP 400 for bad levels gracefully

### 2026-08-19T16:10:19Z — note [ss-5efork]
Round-2 review raced the fix round (verdict rendered against pre-fix state; ASI/subclass/pact fixes confirmed present in tree by orchestrator). reviewRounds held at 2. Residual round dispatched for two surviving gaps: empty-spellcasting guidance (subclass casters) + gm-levelup section anchor.

### 2026-08-19T16:11:46Z — verified (residual round) [ss-5efork]
Empty-spellcasting guidance added (subclass casters -> third-caster table, never "cannot cast"); gm-levelup API section anchored in FIVE_E_ANCHORS with grepped literals. test_lean_core 13 passed. Final followup review dispatched (round cap).
- 2026-08-19T16:11:46Z  residual round verified — final followup dispatched  [ss-5efork]

### 2026-08-19T16:12:19Z — fail [review-spells-levelup]
reviewed: needs-changes (round 3) — all five prior findings CONFIRMED fixed against the live API; sole defect is one transcribed digit in the new third-caster table ("3/2 at 7" should be 4 first / 2 second) plus an optional mystic-arcanum clause (warlock 11+). Orchestrator decision: one-digit fix re-delegated; final check by orchestrator arithmetic (third-caster = full-caster row at ceil(level/3)) instead of a fourth review round.
- [x] (review) third-caster table matches ceil(level/3) mapping (L7 = 4/2)
- [x] (review) mystic arcanum clause at warlock 11+ (once/long rest, outside pact slots)

### 2026-08-19T16:12:57Z — pass [ss-5efork orchestrator close]
Round-3 review confirmed all substantive findings fixed against the live API; sole residual was one transcribed digit, fixed and verified by orchestrator arithmetic (L7 -> ceil(7/3)=3 -> full-caster row 4/2, matches line 44) plus the mystic-arcanum clause (line 56). test_lean_core 13 passed, anchors hold.
- 2026-08-19T16:12:57Z  done → committed  [ss-5efork]

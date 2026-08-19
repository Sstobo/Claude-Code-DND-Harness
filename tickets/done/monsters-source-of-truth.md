---
slug: monsters-source-of-truth
title: Combat uses fetched SRD stat blocks
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: 5e-native-fork
blockedBy: [unconditional-5e-gates, api-file-cache]
claimedBy: ss-5efork
claimedAt: 2026-08-19T15:45:42Z
changedFiles: [lib/combat_manager.py, tools/gm-combat.sh, .claude/skills/gm-combat/SKILL.md, .claude/agents/monster-manual.md, tests/test_combat_manager.py]
resolution: fetched SRD stat blocks mandatory in combat — add-enemy accepts fetched JSON, kills award fetched XP, duplicates auto-suffixed
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T16:41:05Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Make fetched SRD stat blocks mandatory in combat. `.claude/skills/gm-combat/`
and `.claude/agents/monster-manual.md` get the hard rule: an SRD creature
entering combat uses its fetched AC/HP/attacks/CR/XP — never improvised.
Non-SRD/homebrew creatures are built by analogy: fetch the nearest-CR SRD
block and adapt, stating which block anchored it. Wire the enemy-creation path
in `tools/gm-combat.sh` (and its lib backing) to accept a fetched stat block
JSON so the numbers persist as fetched, not retyped. Update claiming docs
same-commit.

## Acceptance criteria

- [x] gm-combat skill and monster-manual agent state the fetched-block mandate and the homebrew-by-analogy rule
- [x] `gm-combat.sh` enemy creation accepts fetched monster JSON (demonstrated with a fetched goblin)
- [x] XP award on kill uses the fetched block's XP value
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

### 2026-08-19T16:20:08Z — verified [ss-5efork]
Independently demoed in scratch tree: dnd_monster.py goblin -> add-enemy --stat-block-file -> record carries HP 7/XP 50/CR 0.25; kill via end --json awards xp_awarded 50. test_combat_manager 12/12. Both block shapes (full + --combat) mapped; legacy add-enemy signature intact; mandate + homebrew-by-analogy in skill and agent with book-grounded ordering preserved.
- 2026-08-19T16:20:08Z  verified → in-review  [ss-5efork]

### 2026-08-19T16:27:54Z — fail [review-monsters]
reviewed: needs-changes (3 in-scope findings; reviewer also surfaced 3 findings in the other session's files, relayed to them)
- MED combat_manager:73 — stat-block name default means duplicate combatants ("Goblin" x4); _find returns first match so only #1 is ever damageable. New exposure (manual signature forced distinct names). Fix: auto-suffix duplicates on add.
- LOW :153 — xp_by_enemy keyed by name collapses duplicates (contradicts xp_awarded); fixed by suffixing.
- LOW :204 — CLI json.loads/read_text outside try; empty/invalid stat-block file tracebacks and breaks the --json envelope.
- [x] (review) duplicate stat-block enemies get distinct names (Goblin, Goblin 2, ...); each individually damageable
- [x] (review) xp_by_enemy consistent with xp_awarded for multiples
- [x] (review) bad/empty --stat-block(-file) input returns the clean --json error envelope, never a traceback

### 2026-08-19T16:30:55Z — verified (fix round) [ss-5efork]
_unique_name on the shared add path (manual + block); xp fields agree for multiples; CLI failures all return the error envelope (parametrized subprocess tests). 19/19 combat tests. Suite: only the environmental sibling-repo failure. Followup review dispatched.
- 2026-08-19T16:30:55Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T16:41:05Z — pass [review-monsters]
reviewed: perfect (followup round 2) — all four fixes confirmed against live tooling. Optional test gaps noted (missing-path CLI branch, case-insensitive dupes) — verified by hand, not held.
- 2026-08-19T16:41:05Z  done → committed  [ss-5efork]

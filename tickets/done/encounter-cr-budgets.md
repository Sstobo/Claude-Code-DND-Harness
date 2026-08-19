---
slug: encounter-cr-budgets
title: Encounters routed through CR-budget builder
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: 5e-native-fork
blockedBy: [monsters-source-of-truth]
claimedBy: ss-5efork
claimedAt: 2026-08-19T16:41:05Z
changedFiles: [features/dnd-api/monsters/dnd_encounter_v2.py, tests/test_encounter_budget.py, .claude/skills/gm-combat/SKILL.md, .claude/agents/monster-manual.md, docs/conventions/lean-core-and-skill-routing.md]
resolution: DMG XP-budget mode in the encounter builder — thresholds, multipliers, band ceilings; encounters composable with add-enemy
reviewRounds: 2
implementer: null
createdAt: 2026-08-19T14:10:45Z
updatedAt: 2026-08-19T18:02:59Z
---

## Parent

5e-Native Fork (prds/5e-native-fork.md)

## Category

enhancement

## What to build

Route encounter generation through
`features/dnd-api/monsters/dnd_encounter_v2.py` CR budgets. Verify the script
implements the 5e XP-threshold difficulty math (easy/medium/hard/deadly per
party level, encounter multipliers) and fix gaps if it doesn't. Document the
workflow where encounters get designed (gm-combat skill and/or monster-manual
agent): pick difficulty, run the builder with party level/size, get creatures
whose stat blocks then come from the fetched data per monsters-source-of-truth.
Improvised "feels about right" encounter composition for combat-intended beats
is out; narrative set-dressing creatures stay free. Update claiming docs
same-commit.

## Acceptance criteria

- [x] `dnd_encounter_v2.py` produces a correct XP budget for a known case (e.g. 4 PCs at level 3, "hard") matching DMG thresholds
- [x] gm-combat/monster-manual document the builder as the encounter-design path
- [x] Builder output creatures are fetchable SRD indexes (composable with monsters-source-of-truth)
- [x] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

monsters-source-of-truth

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]
- 2026-08-19T16:41:05Z  claimed  [ss-5efork]
- 2026-08-19T17:43:30Z  doc-grounding confirmed  [ss-5efork]

### 2026-08-19T17:49:47Z — verified [ss-5efork]
Budget mode live: 4 PCs L3 hard -> budget 900, adjusted 900, band hard. 58 pure-math tests green (thresholds, multiplier ladder + party-size shifts, band sweep all 20 levels x 4 difficulties); legacy --cr mode unchanged; anchors intact. Suite: only the environmental failure. Known judgement call: single-CR random sampling (thematic casting left to the GM via --cr hint).
- 2026-08-19T17:49:47Z  verified → in-review  [ss-5efork]

### 2026-08-19T17:52:03Z — fail [review-encounters]
reviewed: needs-changes (6 findings, math verified correct)
- HIGH :191 — empty CR pool (SRD has zero CR-18 monsters) raises IndexError before the error guard; --party-level 19 --difficulty medium tracebacks.
- MED :126 — off-table --cr hint (3.5) leaves candidate sets empty; min() ValueError.
- MED :196 — failed individual fetches silently shrink the encounter and re-rate it (hard request can report trivial success).
- LOW :177 — armor_class []/null raises inside combat_fields.
- LOW :255 — --quick/--count silently ignored in budget mode.
- LOW :167 — duplicate picks collide downstream in add-enemy naming (combat_manager suffixes on add, so impact limited; builder should still number or flag).
- [x] (review) empty CR pool returns the JSON error, never a traceback (CR 18 case)
- [x] (review) off-table --cr hint validated or falls back to full CR list
- [x] (review) truncated fetches surface a warning or error, never silent re-rating
- [x] (review) armor_class []/null tolerated; --quick/--count rejected or honored in budget mode
- [x] (review) non-deadly plans land IN the requested band (next-band ceiling enforced, note-field fallback)
- [x] (review) planner sweep covers party sizes 1-8 asserting in-band placement

### 2026-08-19T17:59:50Z — verified (fix round) [ss-5efork]
All 8 findings fixed: empty-pool fallback (nearest populated CR + warning), hint validation, truncation re-rating + warnings, AC null tolerance, flag rejection + help, duplicates field, band_window ceiling with three-tier ranking (only 1 of 640 combos cannot land in-band — solo L1 medium, honestly noted), sweep widened to party 1-8 (696 tests green, no network). Followup review dispatched.
- 2026-08-19T17:59:50Z  fix round verified — followup review dispatched  [ss-5efork]

### 2026-08-19T18:02:59Z — pass [review-encounters]
reviewed: perfect (followup round 2) — all six confirmations verified by execution; 640-combo sweep re-run independently (one licensed out-of-band case, noted).
Notes (cosmetic, non-blocking): all-empty error wording overstates the walk direction; %g note formatting on far-tail plans; run_budget_mode and combat_fields AC-tolerance verified by reading only (thin fake-fetch tests would close the last layer).
- 2026-08-19T18:02:59Z  done → committed  [ss-5efork]

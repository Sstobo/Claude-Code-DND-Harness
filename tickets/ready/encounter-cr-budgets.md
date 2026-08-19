---
slug: encounter-cr-budgets
title: Encounters routed through CR-budget builder
category: enhancement
kind: afk
priority: p2
lane: agent
parentPrd: 5e-native-fork
blockedBy: [monsters-source-of-truth]
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

- [ ] `dnd_encounter_v2.py` produces a correct XP budget for a known case (e.g. 4 PCs at level 3, "hard") matching DMG thresholds
- [ ] gm-combat/monster-manual document the builder as the encounter-design path
- [ ] Builder output creatures are fetchable SRD indexes (composable with monsters-source-of-truth)
- [ ] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

monsters-source-of-truth

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]

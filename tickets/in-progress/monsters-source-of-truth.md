---
slug: monsters-source-of-truth
title: Combat uses fetched SRD stat blocks
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: 5e-native-fork
blockedBy: [unconditional-5e-gates, api-file-cache]
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

Make fetched SRD stat blocks mandatory in combat. `.claude/skills/gm-combat/`
and `.claude/agents/monster-manual.md` get the hard rule: an SRD creature
entering combat uses its fetched AC/HP/attacks/CR/XP — never improvised.
Non-SRD/homebrew creatures are built by analogy: fetch the nearest-CR SRD
block and adapt, stating which block anchored it. Wire the enemy-creation path
in `tools/gm-combat.sh` (and its lib backing) to accept a fetched stat block
JSON so the numbers persist as fetched, not retyped. Update claiming docs
same-commit.

## Acceptance criteria

- [ ] gm-combat skill and monster-manual agent state the fetched-block mandate and the homebrew-by-analogy rule
- [ ] `gm-combat.sh` enemy creation accepts fetched monster JSON (demonstrated with a fetched goblin)
- [ ] XP award on kill uses the fetched block's XP value
- [ ] Claiming docs updated/restamped same-commit

## Verification

Lane: agent

## Blocked by

unconditional-5e-gates, api-file-cache

---

## QA Reports

## History

- 2026-08-19T14:10:45Z  created → ready  [main]

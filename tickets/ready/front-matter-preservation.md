---
slug: front-matter-preservation
title: meta.front from scene-front.txt + levels fix + party-size line
category: enhancement
kind: afk
priority: p1
lane: agent
parentPrd: module-fidelity
blockedBy: [meta-adaptation-binding]
claimedBy: null
claimedAt: null
changedFiles: []
resolution: null
reviewRounds: 0
implementer: null
createdAt: 2026-08-26T18:50:00Z
updatedAt: 2026-08-26T18:50:00Z
---

## Parent

module-fidelity — prds/module-fidelity.md

## Category

enhancement

## What to build

Stop discarding the module front matter. Import lands `scene-front.txt` in
`adventure.json meta.front` ({background, recap, progression_rule, start_date,
designed_for, raw}) via a light deterministic split + converter pass;
`meta.levels` and `meta.designed_for` (party size/level line) derive from it —
AT-05 currently reads levels "1-3" for a level-5 module, which is the fixture
bug. The requires-report seeds provisional adaptation entries from
designed_for. The dossier STORY OVERVIEW renders meta.front.background +
recap ahead of the part openers. Live mechanics named in front matter (AT-05:
Glowing Crystal Shards from AT-02, milestone progression) reach the GM: render
progression_rule + carried mechanics in the overview.

## Acceptance criteria

- [ ] AT-05 re-import: meta.front populated, meta.levels corrected to 5, designed_for captured ("party of four 5th level PCs")
- [ ] Glowing Crystal Shards + milestone rule visible in dossier STORY OVERVIEW
- [ ] requires-report uses designed_for for its provisional party_size/pc_level rows
- [ ] /import-module step list updated; front slice no longer documented as skipped

## Out of scope

Retro-applying milestone progression to the live campaign (player decision).

## Verification

Lane: agent

## Blocked by

meta-adaptation-binding

---

## QA Reports

## History

- 2026-08-26T18:50:00Z  created → ready  [ss-modfid]
